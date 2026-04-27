from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import Any

import httpx
import numpy as np

from bmo.audio_io import play_audio_bytes, record_until_silence
from bmo.config import Settings, get_settings
from bmo.faces import FacePlayer, FaceState
from bmo.logging import setup as setup_logging
from bmo.orq_client import OrqClient
from bmo.stt import transcribe
from bmo.tts import synthesize
from bmo.vision import capture_b64
from bmo.wakeword import WakeWordDetector

log = logging.getLogger(__name__)

ERROR_REPLY = "I can't reach my brain right now. Try again in a sec."

__all__ = ["ERROR_REPLY", "handle_one_utterance", "run"]


def handle_one_utterance(
    settings: Settings,
    record_fn: Callable[[], np.ndarray],
    stt_fn: Callable[[np.ndarray], str],
    orq_client: OrqClient,
    tts_fn: Callable[[str], None],
    camera: Any | None,
    face: Any,
) -> None:
    face.set_state(FaceState.LISTENING)
    audio = record_fn()

    face.set_state(FaceState.THINKING)
    text = stt_fn(audio).strip()
    if not text:
        log.info("empty transcript, skipping")
        face.set_state(FaceState.IDLE)
        return

    image_b64: str | None = None
    if settings.vision_trigger_re.search(text) and camera is not None:
        try:
            image_b64 = capture_b64(camera, rotation=settings.camera_rotation)
        except Exception:
            log.exception("camera capture failed")

    try:
        reply = orq_client.invoke(text, image_b64=image_b64)
    except Exception:
        face.set_state(FaceState.ERROR)
        tts_fn(ERROR_REPLY)
        face.set_state(FaceState.IDLE)
        return

    face.set_state(FaceState.SPEAKING)
    tts_fn(reply or "...")
    face.set_state(FaceState.IDLE)


def run() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)

    orq_client = OrqClient(settings=settings)

    http_client = httpx.Client(
        headers={"Authorization": f"Bearer {settings.orq_api_key}"},
        timeout=30.0,
    )

    wake = WakeWordDetector(settings.wakeword_path, settings.wakeword_threshold)

    try:
        from bmo.vision import PiCamera

        camera: Any = PiCamera(rotation=settings.camera_rotation)
    except Exception:
        log.warning("camera unavailable, vision disabled")
        camera = None

    face = FacePlayer(faces_dir="faces")

    def loop() -> None:
        # Imports deferred so module is importable without portaudio/scipy at runtime.
        # Both packages lack type stubs.
        import sounddevice as sd  # noqa: I001  # pyright: ignore[reportMissingTypeStubs]
        from scipy.signal import resample_poly  # pyright: ignore[reportMissingTypeStubs, reportUnknownVariableType]

        # Try the configured sample_rate first; fall back to the device's native
        # default if the mic refuses it (common with USB mics that only do 44.1k/48k).
        native_rate = settings.sample_rate
        try:
            sd.check_input_settings(  # pyright: ignore[reportUnknownMemberType]
                device=settings.mic_device_index, samplerate=settings.sample_rate, channels=1
            )
        except Exception:
            info = sd.query_devices(settings.mic_device_index, "input")  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
            native_rate = int(info["default_samplerate"])  # pyright: ignore[reportUnknownArgumentType]
            log.warning(
                "mic does not support %dHz; falling back to device default %dHz (will resample)",
                settings.sample_rate,
                native_rate,
            )

        wake_rate = settings.sample_rate
        chunk_n = max(1, int(1280 * native_rate / wake_rate))

        log.info("listening for wakeword (native %dHz, wake %dHz)...", native_rate, wake_rate)
        face.set_state(FaceState.IDLE)

        def wait_for_wakeword() -> None:
            with sd.InputStream(
                samplerate=native_rate,
                channels=1,
                device=settings.mic_device_index,
                dtype="int16",
            ) as stream:
                while True:
                    data, _ = stream.read(chunk_n)  # pyright: ignore[reportUnknownMemberType]
                    mono: np.ndarray = data[:, 0]
                    if native_rate != wake_rate:
                        resampled = resample_poly(mono, wake_rate, native_rate)  # pyright: ignore[reportUnknownArgumentType, reportUnknownVariableType]
                        mono = np.asarray(resampled, dtype=np.int16)
                    if wake.detect(mono):
                        return

        while True:
            wait_for_wakeword()
            log.info("wakeword detected")
            # Wakeword stream is closed here — mic is free for record_until_silence.
            handle_one_utterance(
                settings=settings,
                record_fn=lambda: record_until_silence(
                    sample_rate=native_rate,
                    device=settings.mic_device_index,
                ),
                stt_fn=lambda audio: transcribe(
                    audio, native_rate, http_client, model=settings.orq_stt_model
                ),
                orq_client=orq_client,
                tts_fn=lambda txt: play_audio_bytes(
                    synthesize(
                        txt, http_client, model=settings.orq_tts_model, voice=settings.orq_tts_voice
                    )
                ),
                camera=camera,
                face=face,
            )

    threading.Thread(target=loop, daemon=True).start()
    face.run()


if __name__ == "__main__":
    run()
