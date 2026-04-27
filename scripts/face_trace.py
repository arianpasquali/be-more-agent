"""Run a Realtime session with a FacePlayer that prints state transitions.

Use to verify the event→face mapping without firing up the fullscreen Tk
GUI on the Pi. Each state change is printed with a timestamp.

Usage:
    uv run python scripts/face_trace.py
"""

from __future__ import annotations

import asyncio
import logging
import sys
import time

from bmo.config import get_settings
from bmo.faces import FacePlayer, FaceState
from bmo.logging import setup as setup_logging
from bmo.realtime import _session_loop


class TracingFacePlayer(FacePlayer):
    """FacePlayer subclass that logs every set_state call to stdout."""

    def __init__(self) -> None:
        super().__init__(faces_dir="faces")
        self._t0 = time.monotonic()

    def set_state(self, state: FaceState) -> None:
        elapsed = time.monotonic() - self._t0
        print(f"  [{elapsed:6.2f}s] face → {state.value.upper()}")
        super().set_state(state)


def main() -> int:
    settings = get_settings()
    setup_logging(settings.log_level)
    if not settings.openai_api_key:
        print("OPENAI_API_KEY not set in .env", file=sys.stderr)
        return 1

    log = logging.getLogger("face_trace")
    log.info("realtime face trace — speak to BMO, Ctrl+C to stop")

    face = TracingFacePlayer()
    try:
        asyncio.run(_session_loop(settings, face, 120.0))
    except KeyboardInterrupt:
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
