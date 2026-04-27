from __future__ import annotations

import re
from functools import cached_property

from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ["Settings", "get_settings"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    orq_api_key: str
    orq_agent_key: str
    orq_model: str = "openai/gpt-4o"
    orq_vision_model: str = "openai/gpt-4o"
    orq_stt_model: str = "openai/whisper-1"
    orq_tts_model: str = "openai/tts-1"
    orq_tts_voice: str = "alloy"
    orq_workspace_url: str = "https://my.orq.ai"

    mic_device_index: int | None = None
    sample_rate: int = 16000

    wakeword_path: str = "wakeword.onnx"
    wakeword_threshold: float = 0.5

    session_timeout_sec: int = 30
    vision_capture_trigger: str = r"see|look|what.*you.*see"
    camera_rotation: int = 0

    log_level: str = "INFO"

    @cached_property
    def vision_trigger_re(self) -> re.Pattern[str]:
        return re.compile(self.vision_capture_trigger, re.IGNORECASE)


def get_settings() -> Settings:
    # pydantic-settings populates required fields from env / .env file at runtime;
    # pyright cannot verify that, so we silence the "missing args" false positive.
    return Settings()  # pyright: ignore[reportCallIssue]
