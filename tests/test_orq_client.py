from unittest.mock import MagicMock

from bmo.orq_client import OrqClient


def make_settings():
    import os

    from bmo.config import Settings

    os.environ["ORQ_API_KEY"] = "sk-test"
    os.environ["ORQ_AGENT_KEY"] = "bmo_demo"
    return Settings()


def make_text_part(text: str) -> MagicMock:
    """Create a fake A2A TextPart with kind='text'."""
    part = MagicMock()
    part.kind = "text"
    part.text = text
    return part


def make_response(text: str) -> MagicMock:
    """Create a fake CreateAgentResponse with a single assistant message."""
    part = make_text_part(text)
    msg = MagicMock()
    msg.parts = [part]
    resp = MagicMock()
    resp.output = [msg]
    resp.task_id = "task-abc"
    return resp


def test_invoke_text_only(monkeypatch):
    fake_resp = make_response("Hello visitor!")
    fake_sdk = MagicMock()
    fake_sdk.agents.responses.create.return_value = fake_resp

    client = OrqClient(settings=make_settings(), sdk=fake_sdk)
    out = client.invoke("hello")

    assert out == "Hello visitor!"
    call = fake_sdk.agents.responses.create.call_args
    assert call.kwargs["agent_key"] == "bmo_demo"
    assert call.kwargs["message"]["role"] == "user"
    parts = call.kwargs["message"]["parts"]
    assert len(parts) == 1
    assert parts[0]["kind"] == "text"
    assert parts[0]["text"] == "hello"


def test_invoke_with_image(monkeypatch):
    fake_resp = make_response("I see a desk.")
    fake_sdk = MagicMock()
    fake_sdk.agents.responses.create.return_value = fake_resp

    client = OrqClient(settings=make_settings(), sdk=fake_sdk)
    out = client.invoke("what do you see", image_b64="aGVsbG8=")

    assert out == "I see a desk."
    call = fake_sdk.agents.responses.create.call_args
    parts = call.kwargs["message"]["parts"]
    kinds = [p["kind"] for p in parts]
    assert "text" in kinds
    assert "file" in kinds
    file_part = next(p for p in parts if p["kind"] == "file")
    assert file_part["file"]["bytes_"] == "aGVsbG8="
    assert file_part["file"]["mime_type"] == "image/jpeg"
