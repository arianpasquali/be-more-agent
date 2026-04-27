"""Bootstrap BMO LLM-as-judge evaluators on orq.ai workspace.

SDK shape verified (orq-ai-sdk):
  - sdk.evals.all(limit=50) -> GetEvalsResponseBody  (has .data: list of evaluator objects)
  - sdk.evals.create(request=<Llm1TypedDict dict>) -> CreateEvalResponseBody

For LLM-as-judge evaluators, the request body must be a dict matching Llm1TypedDict:
  {
    "type": "llm_eval",          # Literal["llm_eval"]
    "mode": "single",            # Literal["single"]
    "key": str,
    "path": str,
    "prompt": str,
    "model": str,
    "output_type": str,          # "boolean" | "number" | "categorical" | "string"
    "description": str           # optional
  }

Note: sdk.evaluators namespace only has get_v2_evaluators_id_versions — it does NOT
support create.  Use sdk.evals.create instead.

The script is idempotent: if an evaluator with the same key already exists, it logs
and skips rather than failing.

Exit codes: 0 = success, 1 = error.
"""

import os
import sys
from pathlib import Path

EVALUATORS_DIR = Path(__file__).parent.parent / "orq" / "evaluators"
EVAL_PATH = "Default/BMO"
EVAL_MODEL = "openai/gpt-4o-mini"

EVALUATOR_KEYS = ["helpfulness", "on_personality", "length"]


def load_api_key() -> str:
    key = os.environ.get("ORQ_API_KEY", "")
    if not key:
        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if line.startswith("ORQ_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    return key


def get_existing_eval_keys(sdk) -> set:
    """Return set of existing evaluator keys from the workspace."""
    existing = set()
    resp = sdk.evals.all(limit=50)
    data = resp.data if hasattr(resp, "data") else []
    for ev in data:
        k = getattr(ev, "key", None) or (ev.get("key") if isinstance(ev, dict) else None)
        if k:
            existing.add(k)
    return existing


def create_evaluator(sdk, short_key: str, prompt_text: str) -> bool:
    """Create a single LLM-as-judge evaluator. Returns True on success."""
    full_key = f"bmo_{short_key}"
    request = {
        "type": "llm_eval",
        "mode": "single",
        "key": full_key,
        "path": EVAL_PATH,
        "prompt": prompt_text,
        "model": EVAL_MODEL,
        "output_type": "number",
        "description": f"BMO booth evaluator: {short_key}",
    }
    sdk.evals.create(request=request)
    return True


def main() -> int:
    api_key = load_api_key()
    if not api_key:
        print("ERROR: ORQ_API_KEY not set and not found in .env", file=sys.stderr)
        return 1

    if not EVALUATORS_DIR.exists():
        print(f"ERROR: Evaluators directory not found: {EVALUATORS_DIR}", file=sys.stderr)
        return 1

    try:
        from orq_ai_sdk import Orq  # type: ignore[import]
    except ImportError:
        print("ERROR: orq-ai-sdk not installed. Run: pip install orq-ai-sdk", file=sys.stderr)
        return 1

    sdk = Orq(api_key=api_key)

    # Fetch existing evaluator keys to support idempotency
    try:
        existing_keys = get_existing_eval_keys(sdk)
        print(f"Existing evaluators in workspace: {existing_keys or '(none)'}")
    except Exception as exc:
        print(f"WARNING: Could not fetch existing evaluators: {exc}. Will attempt creates anyway.")
        existing_keys = set()

    success_count = 0
    skip_count = 0
    error_count = 0

    for short_key in EVALUATOR_KEYS:
        full_key = f"bmo_{short_key}"
        prompt_file = EVALUATORS_DIR / f"{short_key}.md"

        if not prompt_file.exists():
            print(f"ERROR: Prompt file missing: {prompt_file}", file=sys.stderr)
            error_count += 1
            continue

        if full_key in existing_keys:
            print(f"  SKIP '{full_key}' — already exists.")
            skip_count += 1
            continue

        prompt_text = prompt_file.read_text()

        try:
            create_evaluator(sdk, short_key, prompt_text)
            print(f"  Created evaluator '{full_key}'.")
            success_count += 1
        except Exception as exc:
            err_str = str(exc).lower()
            # Treat "already exists" / duplicate-key errors as non-fatal
            if "already" in err_str or "duplicate" in err_str or "conflict" in err_str or "exists" in err_str:
                print(f"  SKIP '{full_key}' — already exists (from API error).")
                skip_count += 1
            else:
                print(f"ERROR creating '{full_key}': {exc}", file=sys.stderr)
                error_count += 1

    print(
        f"\nDone. created={success_count}, skipped={skip_count}, errors={error_count}"
    )
    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
