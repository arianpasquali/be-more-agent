"""OpenAI Realtime speech-to-speech session for BMO.

Uses the openai SDK's WebSocket Realtime API. Server-side VAD handles
turn detection (no manual silence logic). Barge-in supported natively.

Pulls system instructions from the orq agent config (orq/agent.json) so
prompt edits flow through the same governance pipeline as the orq mode —
the only difference is who runs the inference (OpenAI direct vs orq agent).

Audio I/O contract:
- Input  : 16 kHz mono int16 PCM streamed in 100 ms chunks
- Output : 24 kHz mono int16 PCM, played as it arrives via sounddevice OutputStream
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import json
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any, cast

from openai import AsyncOpenAI

from bmo.config import Settings
from bmo.faces import FacePlayer, FaceState

__all__ = ["run_realtime_session"]

log = logging.getLogger(__name__)

INPUT_RATE = 24000  # GA API requires >= 24000 Hz pcm16
OUTPUT_RATE = 24000
INPUT_CHUNK_MS = 100
INPUT_CHUNK_SAMPLES = INPUT_RATE * INPUT_CHUNK_MS // 1000  # 2400 samples


def _load_orq_instructions() -> str:
    """Read system instructions from the committed orq agent config.

    Falls back to a generic BMO persona if the file is missing.
    """
    cfg_path = Path("orq/agent.json")
    if not cfg_path.exists():
        return "You are BMO, a friendly handheld game-console robot. Keep replies short and warm."
    cfg = json.loads(cfg_path.read_text())
    return cfg.get("instructions", "")


async def _session_loop(
    settings: Settings,
    face: FacePlayer,
    session_seconds: float,
) -> None:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY not set in .env (required for Realtime mode)")

    # sounddevice ships no type stubs
    import sounddevice as sd  # pyright: ignore[reportMissingTypeStubs]

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    instructions = _load_orq_instructions()

    log.info(
        "opening realtime session (model=%s, voice=%s)",
        settings.openai_realtime_model,
        settings.openai_realtime_voice,
    )

    # Probe mic native rate; we'll resample to INPUT_RATE before sending.
    mic_rate = INPUT_RATE
    try:
        sd.check_input_settings(  # pyright: ignore[reportUnknownMemberType]
            device=settings.mic_device_index, samplerate=INPUT_RATE, channels=1
        )
    except Exception:
        info = sd.query_devices(settings.mic_device_index, "input")  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        mic_rate = int(info["default_samplerate"])  # pyright: ignore[reportUnknownArgumentType]
        log.warning(
            "mic does not support %dHz; opening at %dHz and resampling for Realtime",
            INPUT_RATE,
            mic_rate,
        )
    mic_chunk_samples = INPUT_CHUNK_SAMPLES * mic_rate // INPUT_RATE

    async with client.realtime.connect(model=settings.openai_realtime_model) as conn:
        # The openai SDK's typed Session model trails the API surface; cast through
        # Any so we can pass session.update kwargs straight through.
        # GA Realtime schema: voice + audio formats nested under session.audio,
        # modalities renamed to output_modalities.
        session_cfg = cast(
            Any,
            {
                "type": "realtime",
                "output_modalities": ["audio"],
                "instructions": instructions,
                "audio": {
                    "input": {
                        "format": {"type": "audio/pcm", "rate": INPUT_RATE},
                        "turn_detection": {
                            "type": "server_vad",
                            "threshold": 0.5,
                            "silence_duration_ms": 600,
                        },
                    },
                    "output": {
                        "format": {"type": "audio/pcm", "rate": OUTPUT_RATE},
                        "voice": settings.openai_realtime_voice,
                    },
                },
            },
        )
        await conn.session.update(session=session_cfg)

        # Output: stream raw pcm16 24kHz mono to a player that respects the
        # PulseAudio/PipeWire default sink (= the user's selected output,
        # including Bluetooth headsets). sounddevice would talk to ALSA
        # directly and ignore the PA default. Prefer paplay (native PA raw
        # player), fall back to ffplay if paplay isn't installed.
        if shutil.which("paplay"):
            out_cmd = [
                "paplay",
                "--raw",
                "--format=s16le",
                f"--rate={OUTPUT_RATE}",
                "--channels=1",
                "--latency-msec=80",
            ]
        elif shutil.which("ffplay"):
            out_cmd = [
                "ffplay",
                "-nodisp",
                "-loglevel",
                "warning",
                "-f",
                "s16le",
                "-ar",
                str(OUTPUT_RATE),
                "-ac",
                "1",
                "-fflags",
                "nobuffer",
                "-i",
                "pipe:0",
            ]
        else:
            raise RuntimeError("no audio player found — install pulseaudio-utils or ffmpeg")
        log.info("audio output: %s", out_cmd[0])
        out_proc = subprocess.Popen(
            out_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        assert out_proc.stdin is not None  # type narrowing for pyright
        out_stdin = out_proc.stdin  # local non-Optional alias

        # Drain stderr in a thread so the player's complaints surface in logs.
        def _drain_stderr() -> None:
            stderr = out_proc.stderr
            if stderr is None:
                return
            for raw in stderr:
                line = raw.decode("utf-8", "replace").rstrip()
                if line:
                    log.warning("%s: %s", out_cmd[0], line)

        import threading

        threading.Thread(target=_drain_stderr, daemon=True).start()

        in_stream = sd.RawInputStream(
            samplerate=mic_rate, channels=1, dtype="int16", device=settings.mic_device_index
        )
        in_stream.start()

        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        timeout_handle = loop.call_later(session_seconds, stop.set)

        # Lazy import: scipy adds startup cost; only need it when resampling.
        resample_poly: Any = None
        if mic_rate != INPUT_RATE:
            from scipy.signal import resample_poly as _rp  # pyright: ignore[reportMissingTypeStubs, reportUnknownVariableType]  # noqa: I001

            resample_poly = cast(Any, _rp)

        import numpy as np

        async def pump_mic() -> None:
            try:
                while not stop.is_set():
                    read_chunk = cast(Any, in_stream.read)  # pyright: ignore[reportUnknownMemberType]
                    data, _ = await loop.run_in_executor(  # pyright: ignore[reportUnknownVariableType]
                        None, read_chunk, mic_chunk_samples
                    )
                    pcm: bytes = bytes(data)  # pyright: ignore[reportUnknownArgumentType]
                    if resample_poly is not None:
                        arr = np.frombuffer(pcm, dtype=np.int16)
                        resampled = resample_poly(arr, INPUT_RATE, mic_rate)  # pyright: ignore[reportUnknownArgumentType, reportUnknownVariableType]
                        clipped: Any = np.clip(resampled, -32768, 32767)
                        pcm = clipped.astype(np.int16).tobytes()
                    await conn.input_audio_buffer.append(audio=base64.b64encode(pcm).decode())
            except Exception:
                log.exception("mic pump failed")
                stop.set()

        # Padding past computed playback end before flipping back to IDLE,
        # to cover paplay's --latency-msec buffer + BT sink jitter.
        playback_tail_padding_s = 0.4

        async def pump_events() -> None:
            speaking_started = False
            response_bytes = 0
            response_started_at = 0.0
            idle_task: asyncio.Task[None] | None = None

            async def _delayed_idle(delay_s: float) -> None:
                try:
                    await asyncio.sleep(max(0.0, delay_s))
                    face.set_state(FaceState.IDLE)
                except asyncio.CancelledError:
                    pass

            def _start_response() -> None:
                nonlocal speaking_started, response_bytes, idle_task
                speaking_started = False
                response_bytes = 0
                if idle_task and not idle_task.done():
                    idle_task.cancel()
                    idle_task = None

            try:
                async for event in conn:
                    etype = getattr(event, "type", "")

                    if etype in ("response.audio.delta", "response.output_audio.delta"):
                        audio_b64 = getattr(event, "delta", "")
                        if audio_b64:
                            if not speaking_started:
                                speaking_started = True
                                response_started_at = loop.time()
                                face.set_state(FaceState.SPEAKING)
                            try:
                                pcm = base64.b64decode(audio_b64)
                                out_stdin.write(pcm)
                                out_stdin.flush()
                                response_bytes += len(pcm)
                            except BrokenPipeError:
                                log.warning("audio player pipe closed")
                                stop.set()
                                return
                    elif etype == "input_audio_buffer.speech_started":
                        # Barge-in: visitor speaking cancels in-progress audio.
                        if idle_task and not idle_task.done():
                            idle_task.cancel()
                            idle_task = None
                        speaking_started = False
                        face.set_state(FaceState.LISTENING)
                    elif etype == "input_audio_buffer.speech_stopped":
                        face.set_state(FaceState.THINKING)
                    elif etype == "response.created":
                        _start_response()
                    elif etype in ("response.audio.done", "response.output_audio.done"):
                        # Server is done streaming bytes; local paplay buffer
                        # still draining. Compute expected playback end and
                        # schedule the IDLE transition then.
                        if speaking_started and response_bytes:
                            play_seconds = response_bytes / 2 / OUTPUT_RATE
                            elapsed = loop.time() - response_started_at
                            remaining = play_seconds - elapsed + playback_tail_padding_s
                            log.debug(
                                "audio done: bytes=%d play=%.2fs elapsed=%.2fs idle in %.2fs",
                                response_bytes,
                                play_seconds,
                                elapsed,
                                remaining,
                            )
                            idle_task = asyncio.create_task(_delayed_idle(remaining))
                        else:
                            face.set_state(FaceState.IDLE)
                        speaking_started = False
                    elif etype in (
                        "response.audio_transcript.done",
                        "response.output_audio_transcript.done",
                    ):
                        log.info("bmo said: %r", getattr(event, "transcript", ""))
                    elif etype == "conversation.item.input_audio_transcription.completed":
                        log.info("heard: %r", getattr(event, "transcript", ""))
                    elif etype == "error":
                        log.error("realtime error: %s", getattr(event, "error", event))
                        face.set_state(FaceState.ERROR)
                        stop.set()
                        return

                    if stop.is_set():
                        if idle_task and not idle_task.done():
                            idle_task.cancel()
                        return
            except Exception:
                log.exception("event pump failed")
                face.set_state(FaceState.ERROR)
                stop.set()

        try:
            await asyncio.gather(pump_mic(), pump_events())
        finally:
            timeout_handle.cancel()
            in_stream.stop()
            in_stream.close()
            with contextlib.suppress(Exception):
                out_stdin.close()
            try:
                out_proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                out_proc.kill()
            log.info("realtime session closed")


def run_realtime_session(
    settings: Settings, face: FacePlayer, session_seconds: float = 60.0
) -> None:
    """Blocking entrypoint — runs one Realtime session for session_seconds."""
    asyncio.run(_session_loop(settings, face, session_seconds))
