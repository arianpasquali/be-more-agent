from unittest.mock import MagicMock, patch
from bmo.orq_client import OrqClient


def make_settings():
    from bmo.config import Settings
    import os
    os.environ["ORQ_API_KEY"] = "sk-test"
    os.environ["ORQ_AGENT_KEY"] = "bmo_demo"
    return Settings()


def test_invoke_text_only(monkeypatch):
    fake_resp = MagicMock()
    fake_resp.output = [MagicMock(content=[MagicMock(text="Hello visitor!")])]
    fake_sdk = MagicMock()
    fake_sdk.responses.create.return_value = fake_resp

    client = OrqClient(settings=make_settings(), sdk=fake_sdk)
    out = client.invoke("hello")

    assert out == "Hello visitor!"
    call = fake_sdk.responses.create.call_args
    assert call.kwargs["model"] == "agent/bmo_demo"


def test_invoke_with_image(monkeypatch):
    fake_resp = MagicMock()
    fake_resp.output = [MagicMock(content=[MagicMock(text="I see a desk.")])]
    fake_sdk = MagicMock()
    fake_sdk.responses.create.return_value = fake_resp

    client = OrqClient(settings=make_settings(), sdk=fake_sdk)
    out = client.invoke("what do you see", image_b64="aGVsbG8=")

    assert out == "I see a desk."
    payload = fake_sdk.responses.create.call_args.kwargs["input"]
    assert isinstance(payload, list)
    parts = payload[0]["content"]
    assert any(p["type"] == "input_image" for p in parts)
    assert any(p["type"] == "input_text" for p in parts)
