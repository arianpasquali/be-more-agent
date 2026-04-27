from __future__ import annotations

import os

import pytest

from bmo.config import Settings
from bmo.orq_client import OrqClient

pytestmark = pytest.mark.live


def test_live_text_invoke():
    if not os.environ.get("ORQ_API_KEY"):
        pytest.skip("ORQ_API_KEY not set")
    # pydantic-settings populates required fields from env; pyright can't verify that
    s = Settings()  # pyright: ignore[reportCallIssue]
    c = OrqClient(settings=s)
    out = c.invoke("Say hi in one short sentence.")
    print(out)
    assert out
    assert len(out) < 300
