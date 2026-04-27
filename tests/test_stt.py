from unittest.mock import MagicMock
import numpy as np
from bmo.stt import transcribe


def test_transcribe_returns_text():
    fake_client = MagicMock()
    fake_response = MagicMock()
    fake_response.raise_for_status.return_value = None
    fake_response.json.return_value = {"text": "hello bmo"}
    fake_client.post.return_value = fake_response

    audio = np.zeros(16000, dtype=np.float32)
    out = transcribe(audio, sample_rate=16000, client=fake_client, model="openai/whisper-1")
    assert out == "hello bmo"

    # Verify the call was made with correct endpoint and model
    call_kwargs = fake_client.post.call_args
    assert "audio/transcriptions" in call_kwargs[0][0]
    assert call_kwargs[1]["data"]["model"] == "openai/whisper-1"
