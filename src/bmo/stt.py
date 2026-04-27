"""
Speech-to-text via the orq AI Router (Whisper).

SDK adaptation note:
    The orq_ai_sdk (Orq) does NOT expose a .audio attribute as of 2026-04.
    `Orq(api_key='test').audio` → AttributeError.

    Therefore, production STT is implemented via a plain httpx.Client that
    POSTs multipart/form-data to the orq AI Router transcription endpoint:

        POST https://api.orq.ai/v3/router/audio/transcriptions
        Authorization: Bearer <api_key>
        Content-Type: multipart/form-data
        Body fields: file (WAV bytes), model (str)

    The `client` parameter accepts any object with a `.post(url, files, data)`
    method that returns a response with `.raise_for_status()` and `.json()`.
    In production pass an `httpx.Client` (or requests.Session); in tests pass
    a MagicMock.
"""

from __future__ import annotations

import io
import logging
import wave
from typing import Any, Protocol

import numpy as np

log = logging.getLogger(__name__)

ORQ_TRANSCRIPTION_URL = "https://api.orq.ai/v3/router/audio/transcriptions"

__all__ = ["transcribe"]


class _HttpClient(Protocol):
    """Minimal interface satisfied by httpx.Client, requests.Session, or a MagicMock."""

    def post(
        self,
        url: str,
        *,
        files: dict[str, Any],
        data: dict[str, str],
    ) -> Any: ...


def _audio_to_wav_bytes(audio: np.ndarray, sample_rate: int) -> bytes:
    int16 = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(int16.tobytes())
    return buf.getvalue()


def transcribe(
    audio: np.ndarray,
    sample_rate: int,
    client: _HttpClient,
    model: str = "openai/whisper-1",
    url: str = ORQ_TRANSCRIPTION_URL,
) -> str:
    """Transcribe float32 audio via the orq AI Router Whisper endpoint.

    Args:
        audio:       Float32 array, values in [-1.0, 1.0].
        sample_rate: Audio sample rate (e.g. 16000).
        client:      httpx.Client (or compatible) pre-configured with auth headers.
        model:       Model ID routed through orq (default: openai/whisper-1).
        url:         Transcription endpoint URL.

    Returns:
        Transcribed text string, or "" on empty response.
    """
    wav_bytes = _audio_to_wav_bytes(audio, sample_rate)
    resp = client.post(
        url,
        files={"file": ("speech.wav", wav_bytes, "audio/wav")},
        data={"model": model},
    )
    resp.raise_for_status()
    return resp.json().get("text", "") or ""
