"""Shared fixtures for the bmo test suite."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock

import pytest

from bmo.config import Settings


@pytest.fixture
def make_settings(monkeypatch: pytest.MonkeyPatch) -> Callable[..., Settings]:
    """Return a factory that builds a Settings populated with safe test defaults."""

    def _factory(**overrides: str) -> Settings:
        env = {
            "ORQ_API_KEY": "sk-test",
            "ORQ_AGENT_KEY": "bmo_demo",
            **overrides,
        }
        for k, v in env.items():
            monkeypatch.setenv(k, v)
        return Settings()

    return _factory


@pytest.fixture
def mock_orq_sdk() -> MagicMock:
    """A MagicMock shaped like the orq-ai-sdk Orq client."""
    sdk = MagicMock()
    fake_resp = MagicMock()
    fake_resp.task_id = "task-test"
    fake_resp.output = []
    sdk.agents.responses.create.return_value = fake_resp
    return sdk
