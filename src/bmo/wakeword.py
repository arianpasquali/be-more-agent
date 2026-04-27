from __future__ import annotations

import logging
from pathlib import Path
from typing import cast

import numpy as np

# openwakeword ships no type stubs; ignore the stub-not-found diagnostic
import openwakeword.utils  # pyright: ignore[reportMissingTypeStubs]
from openwakeword.model import Model  # pyright: ignore[reportMissingTypeStubs]

log = logging.getLogger(__name__)

__all__ = ["WakeWordDetector"]

# Preprocessor models (melspectrogram + embedding) ship separately from the
# openwakeword wheel and must be downloaded once into the package's resources/
# directory before any Model() can run.
_PREPROCESSOR_FILES = ("melspectrogram.onnx", "embedding_model.onnx")


def _ensure_preprocessor_models() -> None:
    pkg_dir = Path(openwakeword.utils.__file__).parent
    resources = pkg_dir / "resources" / "models"
    missing = [f for f in _PREPROCESSOR_FILES if not (resources / f).exists()]
    if not missing:
        return
    log.info("downloading openwakeword preprocessor models: %s", missing)
    openwakeword.utils.download_models()  # pyright: ignore[reportUnknownMemberType]


class WakeWordDetector:
    def __init__(self, model_path: str, threshold: float = 0.5):
        self.threshold = threshold
        _ensure_preprocessor_models()
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
