"""Silero VAD wrapper using the ONNX model downloaded by openwakeword.

openwakeword.utils.download_models() places `silero_vad.onnx` under the
package's resources/models/ directory. We reuse it via onnxruntime — no
extra pip dep, no torch.

Silero VAD expects:
- 16 kHz mono float32 input
- chunks of exactly 512 samples (32 ms each)

It returns a probability in [0.0, 1.0] of speech being present in the chunk.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import onnxruntime as ort  # pyright: ignore[reportMissingTypeStubs]

# openwakeword ships no type stubs
import openwakeword.utils  # pyright: ignore[reportMissingTypeStubs]

__all__ = ["VAD_CHUNK_SAMPLES", "VAD_SAMPLE_RATE", "SileroVAD"]

log = logging.getLogger(__name__)

VAD_SAMPLE_RATE = 16000
VAD_CHUNK_SAMPLES = 512  # 32 ms @ 16 kHz


def _model_path() -> Path:
    pkg_dir = Path(openwakeword.utils.__file__).parent
    return pkg_dir / "resources" / "models" / "silero_vad.onnx"


class SileroVAD:
    """Stateful per-stream Silero VAD."""

    def __init__(self) -> None:
        path = _model_path()
        if not path.exists():
            # Trigger openwakeword's bundled downloader (also fetches Silero VAD).
            log.info("downloading silero_vad.onnx via openwakeword…")
            openwakeword.utils.download_models()  # pyright: ignore[reportUnknownMemberType]
        self._session = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
        # The openwakeword-shipped Silero VAD is the older variant with separate
        # h/c LSTM states ([2, batch, 64]) rather than a combined `state` tensor.
        self._h = np.zeros((2, 1, 64), dtype=np.float32)
        self._c = np.zeros((2, 1, 64), dtype=np.float32)
        self._sr = np.array(VAD_SAMPLE_RATE, dtype=np.int64)

    def reset(self) -> None:
        self._h = np.zeros((2, 1, 64), dtype=np.float32)
        self._c = np.zeros((2, 1, 64), dtype=np.float32)

    def is_speech(self, chunk: np.ndarray, threshold: float = 0.5) -> bool:
        return self.score(chunk) >= threshold

    def score(self, chunk: np.ndarray) -> float:
        if chunk.shape[0] != VAD_CHUNK_SAMPLES:
            raise ValueError(
                f"silero VAD requires exactly {VAD_CHUNK_SAMPLES} samples, got {chunk.shape[0]}"
            )
        x = chunk.astype(np.float32).reshape(1, -1)
        outputs = self._session.run(  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
            None,
            {"input": x, "h": self._h, "c": self._c, "sr": self._sr},
        )
        prob_arr: np.ndarray = np.asarray(outputs[0])  # pyright: ignore[reportUnknownArgumentType]
        self._h = np.asarray(outputs[1])  # pyright: ignore[reportUnknownArgumentType]
        self._c = np.asarray(outputs[2])  # pyright: ignore[reportUnknownArgumentType]
        return float(prob_arr.flat[0])
