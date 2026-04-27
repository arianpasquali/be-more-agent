"""TTS via orq.ai AI Router (/v3/router/audio/speech).

Replaces local Piper. Returns MP3 bytes; playback is the caller's job.
"""

from __future__ import annotations

import logging
from typing import Any

__all__ = ["synthesize"]

log = logging.getLogger(__name__)

ORQ_SPEECH_URL = "https://api.orq.ai/v3/router/audio/speech"


def synthesize(
    text: str,
    client: Any,
    model: str = "openai/tts-1",
    voice: str = "alloy",
) -> bytes:
    """POST text to orq Router TTS and return audio bytes (MP3)."""
    resp = client.post(
        ORQ_SPEECH_URL,
        json={"model": model, "input": text, "voice": voice},
    )
    resp.raise_for_status()
    return resp.content
