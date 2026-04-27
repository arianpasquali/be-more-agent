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
import json
import logging
from pathlib import Path
from typing import Any, cast

from openai import AsyncOpenAI

from bmo.config import Settings
from bmo.faces import FacePlayer, FaceState

__all__ = ["run_realtime_session"]

log = logging.getLogger(__name__)

INPUT_RATE = 16000
OUTPUT_RATE = 24000
INPUT_CHUNK_MS = 100
INPUT_CHUNK_SAMPLES = INPUT_RATE * INPUT_CHUNK_MS // 1000  # 1600 samples


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
        session_cfg = cast(
            Any,
            {
                "instructions": instructions,
                "voice": settings.openai_realtime_voice,
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "silence_duration_ms": 600,
                },
                "modalities": ["audio", "text"],
            },
        )
        await conn.session.update(session=session_cfg)

        out_stream = sd.RawOutputStream(samplerate=OUTPUT_RATE, channels=1, dtype="int16")
        in_stream = sd.RawInputStream(
            samplerate=mic_rate, channels=1, dtype="int16", device=settings.mic_device_index
        )
        out_stream.start()
        in_stream.start()

        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        timeout_handle = loop.call_later(session_seconds, stop.set)

        # Lazy import: scipy adds startup cost; only need it when resampling.
        if mic_rate != INPUT_RATE:
            from scipy.signal import (
                resample_poly,  # pyright: ignore[reportMissingTypeStubs, reportUnknownVariableType]
            )
        else:
            resample_poly = None  # pyright: ignore[reportConstantRedefinition]

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
                        clipped = cast(Any, np.clip(resampled, -32768, 32767))
                        pcm = clipped.astype(np.int16).tobytes()
                    await conn.input_audio_buffer.append(audio=base64.b64encode(pcm).decode())
            except Exception:
                log.exception("mic pump failed")
                stop.set()

        async def pump_events() -> None:
            try:
                async for event in conn:
                    etype = getattr(event, "type", "")
                    if etype == "response.audio.delta":
                        audio_b64 = getattr(event, "delta", "")
                        if audio_b64:
                            out_stream.write(base64.b64decode(audio_b64))  # pyright: ignore[reportUnknownMemberType]
                    elif etype == "input_audio_buffer.speech_started":
                        face.set_state(FaceState.LISTENING)
                    elif etype == "input_audio_buffer.speech_stopped":
                        face.set_state(FaceState.THINKING)
                    elif etype == "response.audio.done":
                        face.set_state(FaceState.IDLE)
                    elif etype == "response.created":
                        face.set_state(FaceState.SPEAKING)
                    elif etype == "response.audio_transcript.done":
                        log.info("bmo said: %r", getattr(event, "transcript", ""))
                    elif etype == "conversation.item.input_audio_transcription.completed":
                        log.info("heard: %r", getattr(event, "transcript", ""))
                    elif etype == "error":
                        log.error("realtime error: %s", getattr(event, "error", event))
                        stop.set()
                        return
                    if stop.is_set():
                        return
            except Exception:
                log.exception("event pump failed")
                stop.set()

        try:
            await asyncio.gather(pump_mic(), pump_events())
        finally:
            timeout_handle.cancel()
            in_stream.stop()
            in_stream.close()
            out_stream.stop()
            out_stream.close()
            log.info("realtime session closed")


def run_realtime_session(
    settings: Settings, face: FacePlayer, session_seconds: float = 60.0
) -> None:
    """Blocking entrypoint — runs one Realtime session for session_seconds."""
    asyncio.run(_session_loop(settings, face, session_seconds))
