"""Plain-text REPL against the orq BMO agent. No mic, no TTS, no Pi.

Use this to validate conversational continuity (task_id threading),
prompt edits in AI Studio, and orq trace flow without any audio
hardware in the loop.

Usage:
    uv run python scripts/chat.py
    uv run python scripts/chat.py --reset    # start a fresh thread

Commands inside the REPL:
    /reset   — drop the current task_id (start a new thread)
    /thread  — print the current task_id
    /quit    — exit
"""

from __future__ import annotations

import argparse
import sys

from bmo.config import get_settings
from bmo.orq_client import OrqClient


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reset", action="store_true", help="start with a fresh thread")
    args = parser.parse_args()

    settings = get_settings()
    client = OrqClient(settings=settings)
    if args.reset:
        client.reset_thread()

    print(f"BMO chat — agent={settings.orq_agent_key} model={settings.orq_model}")
    print("Type a message and press Enter. /reset, /thread, /quit.\n")

    try:
        while True:
            try:
                line = input("you> ").strip()
            except EOFError:
                print()
                break

            if not line:
                continue
            if line in ("/quit", "/exit"):
                break
            if line == "/reset":
                client.reset_thread()
                print("(thread reset)")
                continue
            if line == "/thread":
                print(f"(task_id={client._task_id})")
                continue

            try:
                reply = client.invoke(line)
            except Exception as exc:
                print(f"!! orq error: {type(exc).__name__}: {exc}", file=sys.stderr)
                continue

            print(f"bmo> {reply or '(empty)'}\n")
    except KeyboardInterrupt:
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
