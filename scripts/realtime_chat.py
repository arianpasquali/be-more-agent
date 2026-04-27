"""Standalone Realtime API tester — no wakeword, no faces, no Pi GUI.

Opens an OpenAI Realtime session immediately and routes mic in / audio out
through the host's audio stack (PulseAudio/PipeWire). Press Ctrl+C to stop.

Usage:
    uv run python scripts/realtime_chat.py
    uv run python scripts/realtime_chat.py --seconds 120
    uv run python scripts/realtime_chat.py --voice marin
    OPENAI_REALTIME_VOICE=cedar uv run python scripts/realtime_chat.py
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from bmo.config import get_settings
from bmo.faces import FacePlayer
from bmo.logging import setup as setup_logging
from bmo.realtime import _session_loop


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=float, default=120.0, help="session length (default 120)")
    parser.add_argument("--voice", type=str, default=None, help="override OPENAI_REALTIME_VOICE")
    args = parser.parse_args()

    settings = get_settings()
    if args.voice:
        settings.openai_realtime_voice = args.voice

    setup_logging(settings.log_level)
    if not settings.openai_api_key:
        print("OPENAI_API_KEY not set in .env", file=sys.stderr)
        return 1

    log = logging.getLogger("realtime_chat")
    log.info(
        "starting realtime chat (model=%s, voice=%s, %.0fs) — speak when ready, Ctrl+C to stop",
        settings.openai_realtime_model,
        settings.openai_realtime_voice,
        args.seconds,
    )

    # FacePlayer is only used for set_state callbacks; pass an instance with
    # no Tk window. set_state() never blocks on the GUI thread.
    face = FacePlayer(faces_dir="faces")
    try:
        asyncio.run(_session_loop(settings, face, args.seconds))
    except KeyboardInterrupt:
        log.info("interrupted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
