from unittest.mock import MagicMock, patch

import numpy as np

from bmo.main import handle_one_utterance


def test_handle_text_only(make_settings):
    settings = make_settings()
    audio = np.zeros(16000, dtype=np.float32)

    fake_record = MagicMock(return_value=audio)
    fake_stt = MagicMock(return_value="tell me a joke")
    fake_orq = MagicMock()
    fake_orq.invoke.return_value = "knock knock"
    fake_tts = MagicMock()
    fake_camera = MagicMock()
    fake_face = MagicMock()

    handle_one_utterance(
        settings=settings,
        record_fn=fake_record,
        stt_fn=fake_stt,
        orq_client=fake_orq,
        tts_fn=fake_tts,
        camera=fake_camera,
        face=fake_face,
    )

    fake_orq.invoke.assert_called_once_with("tell me a joke", image_b64=None)
    fake_tts.assert_called_once_with("knock knock")
    fake_camera.capture.assert_not_called()


def test_handle_vision_trigger_captures(make_settings):
    settings = make_settings()
    audio = np.zeros(16000, dtype=np.float32)

    fake_record = MagicMock(return_value=audio)
    fake_stt = MagicMock(return_value="bmo what do you see")
    fake_orq = MagicMock()
    fake_orq.invoke.return_value = "a desk"
    fake_tts = MagicMock()
    fake_camera = MagicMock()
    fake_face = MagicMock()

    with patch("bmo.main.capture_b64", return_value="BASE64IMG") as cap:
        handle_one_utterance(
            settings=settings,
            record_fn=fake_record,
            stt_fn=fake_stt,
            orq_client=fake_orq,
            tts_fn=fake_tts,
            camera=fake_camera,
            face=fake_face,
        )

    cap.assert_called_once()
    fake_orq.invoke.assert_called_once_with("bmo what do you see", image_b64="BASE64IMG")
