"""Centralized logging setup for bmo."""
from __future__ import annotations

import logging

__all__ = ["setup"]

_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"


def setup(level: str = "INFO") -> None:
    """Configure root logger. Idempotent: clears existing handlers first."""
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(_FORMAT))
    root.addHandler(handler)
    root.setLevel(level.upper())
