from __future__ import annotations

from unittest.mock import MagicMock

from bmo.tts import synthesize


def test_synthesize_posts_and_returns_bytes() -> None:
    fake = MagicMock()
    fake.post.return_value.content = b"MP3DATA"
    fake.post.return_value.raise_for_status = MagicMock()

    out = synthesize("hello", fake, model="openai/tts-1", voice="alloy")

    assert out == b"MP3DATA"
    args, kwargs = fake.post.call_args
    assert args[0] == "https://api.orq.ai/v3/router/audio/speech"
    assert kwargs["json"] == {"model": "openai/tts-1", "input": "hello", "voice": "alloy"}
