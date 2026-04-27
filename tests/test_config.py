import pytest
from pydantic import ValidationError

from bmo.config import Settings


def test_loads_required_keys(monkeypatch):
    monkeypatch.setenv("ORQ_API_KEY", "sk-test")
    monkeypatch.setenv("ORQ_AGENT_KEY", "bmo_demo")
    # pydantic-settings populates required fields from env; pyright can't verify that
    s = Settings()  # pyright: ignore[reportCallIssue]
    assert s.orq_api_key == "sk-test"
    assert s.orq_agent_key == "bmo_demo"
    assert s.orq_model == "openai/gpt-4o"  # default


def test_missing_api_key_raises(monkeypatch, tmp_path):
    # Change to a temporary directory where .env doesn't exist
    # This ensures pydantic-settings won't find the real .env file
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ORQ_API_KEY", raising=False)
    monkeypatch.setenv("ORQ_AGENT_KEY", "bmo_demo")
    with pytest.raises(ValidationError):
        Settings()  # pyright: ignore[reportCallIssue]


def test_orq_stt_model_default(monkeypatch):
    monkeypatch.setenv("ORQ_API_KEY", "sk-test")
    monkeypatch.setenv("ORQ_AGENT_KEY", "bmo_demo")
    s = Settings()  # pyright: ignore[reportCallIssue]
    assert s.orq_stt_model == "openai/whisper-1"


def test_vision_trigger_compiles(monkeypatch):
    monkeypatch.setenv("ORQ_API_KEY", "sk-test")
    monkeypatch.setenv("ORQ_AGENT_KEY", "bmo_demo")
    s = Settings()  # pyright: ignore[reportCallIssue]
    assert s.vision_trigger_re.search("what do you see")
    assert not s.vision_trigger_re.search("hello there")
