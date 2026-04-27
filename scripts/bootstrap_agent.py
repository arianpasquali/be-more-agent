"""Bootstrap BMO agent on orq.ai workspace.

Uses the orq-ai-sdk Python client directly (sdk.agents namespace).
SDK shape verified:
  - sdk.agents.retrieve(agent_key=...) -> raises on 404
  - sdk.agents.create(key, role, description, instructions, path, model, settings, ...)
  - sdk.agents.update(agent_key=..., **updates)

The model field accepts a plain string ("openai/gpt-4o") per SDK type alias:
  ModelConfiguration = ModelConfiguration2 | str

Runs idempotently: creating twice is safe (second run updates instead of
creating a duplicate).

Exit codes: 0 = success, 1 = error.
"""

import json
import os
import sys
from pathlib import Path

import orq_ai_sdk

AGENT_JSON = Path(__file__).parent.parent / "orq" / "agent.json"


def main() -> int:
    api_key = os.environ.get("ORQ_API_KEY", "")
    if not api_key:
        # Also try .env in cwd
        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if line.startswith("ORQ_API_KEY="):
                    api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break

    if not api_key:
        print("ERROR: ORQ_API_KEY not set and not found in .env", file=sys.stderr)
        return 1

    cfg = json.loads(AGENT_JSON.read_text())
    key = cfg["key"]

    from orq_ai_sdk import Orq  # type: ignore[import]

    sdk = Orq(api_key=api_key)

    # Build settings dict for the SDK
    settings = cfg.get("settings", {})

    # Try to retrieve existing agent
    existing = None
    try:
        existing = sdk.agents.retrieve(agent_key=key)
    except orq_ai_sdk.APIError as exc:
        err_str = str(exc).lower()
        # 404 / not found means we need to create
        if "404" in err_str or "not found" in err_str or "notfound" in err_str:
            existing = None
        else:
            print(f"ERROR retrieving agent '{key}': {exc}", file=sys.stderr)
            return 1

    if existing is None:
        # Create
        sdk.agents.create(
            key=key,
            display_name=cfg.get("display_name", key),
            role=cfg.get("role", "Agent"),
            description=cfg["description"],
            instructions=cfg["instructions"],
            path=cfg["path"],
            model=cfg["model"],
            settings=settings,
        )
        print(f"Created agent '{key}' on orq.")
    else:
        # Update
        sdk.agents.update(
            agent_key=key,
            display_name=cfg.get("display_name", key),
            role=cfg.get("role", "Agent"),
            description=cfg["description"],
            instructions=cfg["instructions"],
            path=cfg["path"],
            model=cfg["model"],
            settings=settings,
        )
        print(f"Updated agent '{key}' on orq.")

    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
