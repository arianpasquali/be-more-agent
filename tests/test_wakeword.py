from unittest.mock import MagicMock, patch

import numpy as np

from bmo.wakeword import WakeWordDetector


def test_detector_fires_above_threshold():
    fake_model = MagicMock()
    fake_model.predict.return_value = {"wakeword": 0.92}
    with patch("bmo.wakeword.Model", return_value=fake_model):
        d = WakeWordDetector(model_path="x.onnx", threshold=0.5)
        chunk = np.zeros(1280, dtype=np.int16)
        assert d.detect(chunk) is True


def test_detector_silent_below_threshold():
    fake_model = MagicMock()
    fake_model.predict.return_value = {"wakeword": 0.10}
    with patch("bmo.wakeword.Model", return_value=fake_model):
        d = WakeWordDetector(model_path="x.onnx", threshold=0.5)
        assert d.detect(np.zeros(1280, dtype=np.int16)) is False
