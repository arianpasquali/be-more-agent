"""bmo — orq.ai-backed booth demo."""

from __future__ import annotations

from bmo.config import Settings, get_settings
from bmo.faces import FacePlayer, FaceState
from bmo.main import run
from bmo.orq_client import OrqClient

__version__ = "0.2.0"
__all__ = [
    "FacePlayer",
    "FaceState",
    "OrqClient",
    "Settings",
    "__version__",
    "get_settings",
    "run",
]
