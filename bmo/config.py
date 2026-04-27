import re
from functools import cached_property
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    orq_api_key: str
    orq_agent_key: str
    orq_model: str = "openai/gpt-4o"
    orq_vision_model: str = "openai/gpt-4o"
    orq_workspace_url: str = "https://my.orq.ai"

    mic_device_index: int | None = None
    sample_rate: int = 16000
    piper_voice: str = "voices/bmo.onnx"
    piper_rate: int = 22050

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
    return Settings()
