import os

import pytest

from bmo.config import Settings
from bmo.orq_client import OrqClient

pytestmark = pytest.mark.skipif(
    not os.environ.get("ORQ_API_KEY") or not os.environ.get("RUN_LIVE"),
    reason="set RUN_LIVE=1 to hit real orq",
)


def test_live_text_invoke():
    s = Settings()
    c = OrqClient(settings=s)
    out = c.invoke("Say hi in one short sentence.")
    assert out
    assert len(out) < 300
    print(out)
