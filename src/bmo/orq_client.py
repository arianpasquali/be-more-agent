import logging
from typing import Any

from bmo.config import Settings

log = logging.getLogger(__name__)


class OrqClient:
    """Thin wrapper around the orq-ai-sdk agents.responses API.

    SDK shape (verified against orq-ai-sdk installed in .venv):
      - sdk.agents.responses.create(agent_key, message, ...) -> CreateAgentResponse
      - message: {"role": "user", "parts": [{"kind": "text", "text": "..."}]}
      - image: part {"kind": "file", "file": {"bytes_": "<b64>", "mime_type": "image/jpeg"}}
      - response.output: list of AgentResponseMessage
        each message has .parts: list with .kind and .text attributes
    """

    def __init__(self, settings: Settings, sdk: Any | None = None):
        self.settings = settings
        if sdk is None:
            from orq_ai_sdk import Orq

            sdk = Orq(api_key=settings.orq_api_key)
        self.sdk = sdk
        self._task_id: str | None = None

    def invoke(self, text: str, image_b64: str | None = None) -> str:
        parts: list[dict[str, Any]] = [{"kind": "text", "text": text}]
        if image_b64:
            parts.append(
                {
                    "kind": "file",
                    "file": {
                        "bytes_": image_b64,
                        "mime_type": "image/jpeg",
                    },
                }
            )

        message: dict[str, Any] = {"role": "user", "parts": parts}

        kwargs: dict[str, Any] = {
            "agent_key": self.settings.orq_agent_key,
            "message": message,
        }
        if self._task_id:
            kwargs["task_id"] = self._task_id

        try:
            resp = self.sdk.agents.responses.create(**kwargs)
        except Exception:
            log.exception("orq invoke failed")
            raise

        self._task_id = getattr(resp, "task_id", None)
        return self._extract_text(resp)

    @staticmethod
    def _extract_text(resp: Any) -> str:
        for msg in getattr(resp, "output", []) or []:
            for part in getattr(msg, "parts", []) or []:
                # A2A TextPart has .kind == "text" and .text attribute
                if getattr(part, "kind", None) == "text":
                    text = getattr(part, "text", None)
                    if text:
                        return text
        return ""

    def reset_thread(self) -> None:
        self._task_id = None
