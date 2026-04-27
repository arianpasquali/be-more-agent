from __future__ import annotations

import logging
from typing import cast

import numpy as np

# openwakeword ships no type stubs; ignore the stub-not-found diagnostic
from openwakeword.model import Model  # pyright: ignore[reportMissingTypeStubs]

log = logging.getLogger(__name__)

__all__ = ["WakeWordDetector"]


class WakeWordDetector:
    def __init__(self, model_path: str, threshold: float = 0.5):
        self.threshold = threshold
        self.model = Model(wakeword_models=[model_path], inference_framework="onnx")

    def detect(self, chunk_int16: np.ndarray) -> bool:
        # openwakeword lacks stubs; predict() returns an untyped dict-like object.
        # Cast to a plain dict so we can call .values() safely.
        raw = self.model.predict(chunk_int16)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        scores = cast(dict[str, float], raw)
        if not scores:
            return False
        top = max(scores.values())
        return top >= self.threshold
