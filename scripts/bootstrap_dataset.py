"""Bootstrap BMO booth dataset on orq.ai workspace.

SDK shape verified (orq-ai-sdk):
  - sdk.datasets.list(limit=50) -> ListDatasetsResponseBody  (has .data: list of dataset objects)
  - sdk.datasets.create(request={"display_name": str, "path": str}) -> CreateDatasetResponseBody
  - sdk.datasets.create_datapoint(dataset_id=str, request_body=[...]) -> list of items

CreateDatasetItemRequestBodyTypedDict fields (all optional):
  - inputs: Dict[str, Any]
  - expected_output: str
  - messages: List[...]

The script is idempotent: if a dataset named 'bmo_booth_questions' already exists,
it reuses its ID.  Datapoints are always pushed (re-run will add duplicates; use
the orq dashboard to clear if needed before a clean re-seed).

Exit codes: 0 = success, 1 = error.
"""

import json
import os
import sys
from pathlib import Path

DATASET_NAME = "bmo_booth_questions"
DATASET_PATH = "Default/BMO"
DATASET_JSONL = Path(__file__).parent.parent / "orq" / "dataset.jsonl"

# orq API supports up to 100 datapoints per batch call
BATCH_SIZE = 100


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


def load_datapoints() -> list:
    rows = []
    with DATASET_JSONL.open() as f:
        for _lineno, raw in enumerate(f, 1):
            raw = raw.strip()
            if not raw:
                continue
            obj = json.loads(raw)
            rows.append(obj)
    return rows


def find_or_create_dataset(sdk) -> str:
    """Return dataset ID, creating it if it does not exist."""
    # List existing datasets (paginate if needed)
    resp = sdk.datasets.list(limit=50)
    datasets = resp.data if hasattr(resp, "data") else []
    for ds in datasets:
        name = getattr(ds, "display_name", None) or (
            ds.get("display_name") if isinstance(ds, dict) else None
        )
        if name == DATASET_NAME:
            ds_id = getattr(ds, "id", None) or (ds.get("id") if isinstance(ds, dict) else None)
            print(f"Found existing dataset '{DATASET_NAME}' with id={ds_id}")
            return ds_id

    # Not found — create it
    result = sdk.datasets.create(request={"display_name": DATASET_NAME, "path": DATASET_PATH})
    ds_id = getattr(result, "id", None) or (result.get("id") if isinstance(result, dict) else None)
    print(f"Created dataset '{DATASET_NAME}' with id={ds_id}")
    return ds_id


def push_datapoints(sdk, dataset_id: str, rows: list) -> None:
    """Push all rows in batches."""
    total = 0
    for start in range(0, len(rows), BATCH_SIZE):
        batch = rows[start : start + BATCH_SIZE]
        # Build request body matching CreateDatasetItemRequestBodyTypedDict
        request_body = []
        for row in batch:
            item = {"inputs": row["inputs"]}
            if row.get("expected_output") is not None:
                item["expected_output"] = row["expected_output"]
            request_body.append(item)

        sdk.datasets.create_datapoint(dataset_id=dataset_id, request_body=request_body)
        total += len(batch)
        print(f"  Pushed {total}/{len(rows)} datapoints...")

    print(f"Done. {total} datapoints pushed to dataset '{DATASET_NAME}' (id={dataset_id}).")


def main() -> int:
    api_key = load_api_key()
    if not api_key:
        print("ERROR: ORQ_API_KEY not set and not found in .env", file=sys.stderr)
        return 1

    if not DATASET_JSONL.exists():
        print(f"ERROR: Dataset file not found: {DATASET_JSONL}", file=sys.stderr)
        return 1

    rows = load_datapoints()
    print(f"Loaded {len(rows)} datapoints from {DATASET_JSONL.name}")

    try:
        from orq_ai_sdk import Orq  # type: ignore[import]
    except ImportError:
        print("ERROR: orq-ai-sdk not installed. Run: pip install orq-ai-sdk", file=sys.stderr)
        return 1

    sdk = Orq(api_key=api_key)

    try:
        dataset_id = find_or_create_dataset(sdk)
        push_datapoints(sdk, dataset_id, rows)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
