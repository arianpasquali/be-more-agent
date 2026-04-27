import logging
import threading
from collections.abc import Callable
from typing import Any

import httpx
import numpy as np

from bmo.audio_io import play_tts, record_until_silence
from bmo.config import Settings, get_settings
from bmo.faces import FacePlayer, FaceState
from bmo.orq_client import OrqClient
from bmo.stt import transcribe
from bmo.vision import capture_b64
from bmo.wakeword import WakeWordDetector

log = logging.getLogger(__name__)

ERROR_REPLY = "I can't reach my brain right now. Try again in a sec."


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
    logging.basicConfig(level=settings.log_level)

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

    def loop():
        import sounddevice as sd

        log.info("listening for wakeword...")
        face.set_state(FaceState.IDLE)
        with sd.InputStream(
            samplerate=settings.sample_rate,
            channels=1,
            device=settings.mic_device_index,
            dtype="int16",
        ) as stream:
            while True:
                data, _ = stream.read(1280)
                if wake.detect(data[:, 0]):
                    log.info("wakeword detected")
                    handle_one_utterance(
                        settings=settings,
                        record_fn=lambda: record_until_silence(
                            sample_rate=settings.sample_rate,
                            device=settings.mic_device_index,
                        ),
                        stt_fn=lambda audio: transcribe(
                            audio, settings.sample_rate, http_client, model=settings.orq_stt_model
                        ),
                        orq_client=orq_client,
                        tts_fn=lambda txt: play_tts(txt, voice=settings.piper_voice),
                        camera=camera,
                        face=face,
                    )

    threading.Thread(target=loop, daemon=True).start()
    face.run()


if __name__ == "__main__":
    run()
