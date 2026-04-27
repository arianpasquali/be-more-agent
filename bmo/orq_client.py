import logging
from typing import Any
from bmo.config import Settings

log = logging.getLogger(__name__)


class OrqClient:
    def __init__(self, settings: Settings, sdk: Any | None = None):
        self.settings = settings
        if sdk is None:
            from orq_ai_sdk import Orq
            sdk = Orq(api_key=settings.orq_api_key)
        self.sdk = sdk
        self._previous_response_id: str | None = None

    def invoke(self, text: str, image_b64: str | None = None) -> str:
        if image_b64:
            content = [
                {"type": "input_text", "text": text},
                {"type": "input_image", "image_url": f"data:image/jpeg;base64,{image_b64}"},
            ]
            payload: Any = [{"type": "message", "role": "user", "content": content}]
        else:
            payload = text

        kwargs: dict[str, Any] = {
            "model": f"agent/{self.settings.orq_agent_key}",
            "input": payload,
        }
        if self._previous_response_id:
            kwargs["previous_response_id"] = self._previous_response_id

        try:
            resp = self.sdk.responses.create(**kwargs)
        except Exception:
            log.exception("orq invoke failed")
            raise

        self._previous_response_id = getattr(resp, "id", None)
        return self._extract_text(resp)

    @staticmethod
    def _extract_text(resp: Any) -> str:
        for item in getattr(resp, "output", []) or []:
            for part in getattr(item, "content", []) or []:
                text = getattr(part, "text", None)
                if text:
                    return text
        return ""

    def reset_thread(self) -> None:
        self._previous_response_id = None
