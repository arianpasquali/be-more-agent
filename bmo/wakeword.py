import logging
import numpy as np
from openwakeword.model import Model

log = logging.getLogger(__name__)


class WakeWordDetector:
    def __init__(self, model_path: str, threshold: float = 0.5):
        self.threshold = threshold
        self.model = Model(wakeword_models=[model_path])

    def detect(self, chunk_int16: np.ndarray) -> bool:
        scores = self.model.predict(chunk_int16)
        if not scores:
            return False
        top = max(scores.values())
        return top >= self.threshold
