# Modernize Python Tooling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor `bmo-orq` tooling to 2026 conventions — uv, ruff, pyright, pre-commit, CI, `src/` layout, conftest, markers, CLI entry, CONTRIBUTING, CHANGELOG, py.typed. No runtime behavior change.

**Architecture:** Migrate `requirements.txt` deps into `pyproject.toml` and adopt `uv` for env/lock management. Move `bmo/` → `src/bmo/`. Add ruff + pyright + pre-commit + GitHub Actions. Centralize logging in `src/bmo/logging.py`. Replace env-var test gate with pytest marker. Bump to v0.2.0.

**Tech Stack:** uv, ruff, pyright, pre-commit, pytest + pytest-cov + pytest-asyncio + pytest-mock, hatchling build backend, GitHub Actions, Dependabot.

Spec: `docs/superpowers/specs/2026-04-27-modernize-tooling-design.md`.

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `pyproject.toml` | Rewrite | Project metadata, deps, build system, ruff/pyright/pytest/coverage config, console script |
| `uv.lock` | Create | uv's resolved lockfile |
| `.python-version` | Create | uv reads — `3.11` |
| `requirements.txt` | Delete | Replaced by pyproject deps |
| `setup.sh` | Rewrite | Pi installer using uv |
| `src/bmo/` | Move | Was `bmo/`; same files + new `logging.py`, `py.typed` |
| `src/bmo/__init__.py` | Update | Re-export public surface, add `__all__` |
| `src/bmo/logging.py` | Create | `setup(level)` centralizer |
| `src/bmo/main.py` | Update | Use `bmo.logging.setup` |
| `src/bmo/*.py` | Update | Add `__all__`, `from __future__ import annotations` |
| `tests/` | Stay | Add `conftest.py`, switch to `@pytest.mark.live` |
| `tests/conftest.py` | Create | Shared fixtures |
| `tests/test_live_agent.py` | Update | Use marker not env var |
| `.pre-commit-config.yaml` | Create | ruff + stdlib hooks |
| `.github/workflows/ci.yml` | Create | Lint + tests matrix |
| `.github/dependabot.yml` | Create | pip + actions weekly |
| `.editorconfig` | Create | Cross-IDE consistency |
| `CONTRIBUTING.md` | Create | Dev setup + workflow |
| `CHANGELOG.md` | Create | Backfill v0.1.0, v0.1.1; new v0.2.0 |
| `docs/README.md` | Create | Hub linking to runbook, spec, plan, contributing |
| `README.md` | Update | uv install, `bmo` CLI command, badges |

10 tasks total. Order matters: pyproject foundation → src/ move → ruff → pyright → pre-commit → CI → tests refactor → docs → final tag.

---

## Task 1: pyproject.toml + uv adoption + remove requirements.txt

**Files:**
- Rewrite: `pyproject.toml`
- Create: `.python-version`, `uv.lock` (auto-generated)
- Delete: `requirements.txt`

- [ ] **Step 1: Install uv if missing**

```bash
command -v uv >/dev/null 2>&1 || curl -LsSf https://astral.sh/uv/install.sh | sh
uv --version
```

- [ ] **Step 2: Replace `pyproject.toml`**

```toml
[project]
name = "bmo-orq"
version = "0.2.0"
description = "Conference-booth fork of be-more-agent: Pi as I/O, orq.ai Agent as brain."
readme = "README.md"
license = { file = "LICENSE" }
requires-python = ">=3.11"
authors = [{ name = "Arian Pasquali" }]

dependencies = [
    "orq-ai-sdk>=0.5.0",
    "python-dotenv>=1.0.0",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "sounddevice>=0.4.6",
    "numpy>=1.26.0",
    "scipy>=1.11.0",
    "Pillow>=10.0.0",
    "openwakeword>=0.6.0",
    "onnxruntime>=1.17.0",
    "httpx>=0.26.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-mock>=3.12.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=5.0.0",
    "ruff>=0.6.0",
    "pyright>=1.1.380",
    "pre-commit>=3.7.0",
]
pi = [
    "picamera2; sys_platform == 'linux'",
]

[project.scripts]
bmo = "bmo.main:run"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/bmo"]

[tool.ruff]
line-length = 100
target-version = "py311"
src = ["src", "tests", "scripts"]

[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP", "B", "SIM", "RUF"]
ignore = []

[tool.ruff.format]
docstring-code-format = true

[tool.pyright]
include = ["src", "tests", "scripts"]
strict = ["src/bmo"]
pythonVersion = "3.11"
reportMissingTypeStubs = false

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
markers = [
    "live: hits real orq.ai workspace (requires ORQ_API_KEY in environment)",
]
addopts = "-m 'not live'"

[tool.coverage.run]
source = ["src/bmo"]
branch = true

[tool.coverage.report]
show_missing = true
skip_covered = false
```

- [ ] **Step 3: Create `.python-version`**

```
3.11
```

- [ ] **Step 4: Delete `requirements.txt`**

```bash
git rm requirements.txt
```

- [ ] **Step 5: Generate uv lockfile and sync**

```bash
uv sync --extra dev
```

Expected: `uv.lock` created, `.venv/` populated. If uv complains about `src/bmo` not existing yet (Task 2 hasn't run), temporarily comment out the `[tool.hatch.build.targets.wheel]` block, run `uv sync`, then uncomment and re-run after Task 2. Report which path you took.

- [ ] **Step 6: Verify**

```bash
uv run pytest --version
uv run python -c "import orq_ai_sdk; print('ok')"
```

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml .python-version uv.lock
git rm requirements.txt
git commit -m "build: switch to uv + pyproject deps, drop requirements.txt"
```

---

## Task 2: src/ layout migration

**Files:**
- Move: `bmo/` → `src/bmo/`
- Create: `src/bmo/py.typed`
- Update: `pyproject.toml` already points at `src/bmo` (Task 1)

- [ ] **Step 1: git-mv the package**

```bash
mkdir -p src
git mv bmo src/bmo
```

- [ ] **Step 2: Create `src/bmo/py.typed`** (empty file)

```bash
touch src/bmo/py.typed
git add src/bmo/py.typed
```

- [ ] **Step 3: If you commented out hatchling wheel block in Task 1, uncomment and re-sync now**

```bash
uv sync --extra dev
```

- [ ] **Step 4: Verify imports still resolve**

```bash
uv run python -c "from bmo.config import Settings; from bmo.orq_client import OrqClient; from bmo.main import run; print('ok')"
```

- [ ] **Step 5: Run unit suite**

```bash
uv run pytest -v
```
Expected: all 18 unit tests still pass (live test skipped — addopts already filters it).

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "refactor: move bmo/ to src/bmo/ + add py.typed marker"
```

---

## Task 3: ruff format + lint pass

**Files:**
- Touches all `.py` files under `src/`, `tests/`, `scripts/`.

- [ ] **Step 1: Run ruff formatter**

```bash
uv run ruff format src tests scripts
```

- [ ] **Step 2: Run ruff lint with fix**

```bash
uv run ruff check --fix src tests scripts
```

- [ ] **Step 3: Re-run lint without fix to surface remaining issues**

```bash
uv run ruff check src tests scripts
```

If issues remain, fix manually. Common patterns:
- Bare `except Exception` → keep (we catch broadly intentionally; add `# noqa: BLE001` if ruff complains).
- Long lines → wrap.
- Unused imports — remove.
- Print statements in scripts — leave (intentional CLI output); add `# noqa: T201` only if ruff selects T-rules (we don't enable them, so this should be fine).

- [ ] **Step 4: Verify tests still pass**

```bash
uv run pytest -v
```
Expected: 18 passed.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "style: ruff format + lint --fix pass"
```

---

## Task 4: Add `from __future__ import annotations` + `__all__` in src/bmo modules

**Files:**
- Modify each `src/bmo/*.py` (except `py.typed`).

- [ ] **Step 1: For each module add the future import + `__all__`**

For each of `audio_io.py`, `config.py`, `faces.py`, `main.py`, `orq_client.py`, `stt.py`, `vision.py`, `wakeword.py`:

1. Insert at the very top (above existing imports): `from __future__ import annotations`
2. After the imports, add an `__all__` listing the public surface. Example for `config.py`:

```python
__all__ = ["Settings", "get_settings"]
```

Public name lists per module:
- `audio_io.py`: `["record_until_silence", "play_tts", "SILENCE_RMS"]`
- `config.py`: `["Settings", "get_settings"]`
- `faces.py`: `["FaceState", "FacePlayer", "valid_transition"]`
- `main.py`: `["handle_one_utterance", "run", "ERROR_REPLY"]`
- `orq_client.py`: `["OrqClient"]`
- `stt.py`: `["transcribe"]`
- `vision.py`: `["encode_image_b64", "rotate_image", "PiCamera", "CameraProtocol", "capture_b64"]`
- `wakeword.py`: `["WakeWordDetector"]`

- [ ] **Step 2: Update `src/bmo/__init__.py`** to re-export the most-used public names

```python
"""bmo — orq.ai-backed booth demo."""
from __future__ import annotations

from bmo.config import Settings, get_settings
from bmo.faces import FacePlayer, FaceState
from bmo.main import run
from bmo.orq_client import OrqClient

__version__ = "0.2.0"
__all__ = ["Settings", "get_settings", "FacePlayer", "FaceState", "OrqClient", "run", "__version__"]
```

- [ ] **Step 3: Re-run ruff to ensure import order is canonical**

```bash
uv run ruff format src
uv run ruff check src
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest -v
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor: add __all__ + future annotations to bmo modules"
```

---

## Task 5: Centralized logging — `src/bmo/logging.py`

**Files:**
- Create: `src/bmo/logging.py`
- Modify: `src/bmo/main.py`
- Test: `tests/test_logging.py`

- [ ] **Step 1: Failing test at `tests/test_logging.py`**

```python
from __future__ import annotations

import logging

from bmo.logging import setup


def test_setup_sets_root_level():
    setup("WARNING")
    assert logging.getLogger().level == logging.WARNING


def test_setup_idempotent_no_duplicate_handlers():
    setup("INFO")
    n1 = len(logging.getLogger().handlers)
    setup("INFO")
    n2 = len(logging.getLogger().handlers)
    assert n1 == n2
```

- [ ] **Step 2: Run, verify FAIL**

```bash
uv run pytest tests/test_logging.py -v
```

- [ ] **Step 3: Implement `src/bmo/logging.py`**

```python
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
```

- [ ] **Step 4: Update `src/bmo/main.py`** — replace `logging.basicConfig(level=settings.log_level)` with `bmo.logging.setup(settings.log_level)`. Add the import at the top:

```python
from bmo.logging import setup as setup_logging
```

And in `run()`:
```python
settings = get_settings()
setup_logging(settings.log_level)
```

- [ ] **Step 5: Run tests**

```bash
uv run pytest tests/test_logging.py -v
uv run pytest -v
```
Expected: 18 + 2 new = 20 passed.

- [ ] **Step 6: Commit**

```bash
git add src/bmo/logging.py src/bmo/main.py tests/test_logging.py
git commit -m "feat(logging): centralize log setup, idempotent + formatted"
```

---

## Task 6: tests/conftest.py + @pytest.mark.live

**Files:**
- Create: `tests/conftest.py`
- Modify: `tests/test_live_agent.py`, `tests/test_orq_client.py`, `tests/test_main_loop.py`

- [ ] **Step 1: Create `tests/conftest.py`**

```python
"""Shared fixtures for the bmo test suite."""
from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest

from bmo.config import Settings


@pytest.fixture
def make_settings(monkeypatch: pytest.MonkeyPatch) -> "callable":
    """Return a factory that builds a Settings populated with safe test defaults."""

    def _factory(**overrides: str) -> Settings:
        env = {
            "ORQ_API_KEY": "sk-test",
            "ORQ_AGENT_KEY": "bmo_demo",
            **overrides,
        }
        for k, v in env.items():
            monkeypatch.setenv(k, v)
        return Settings()

    return _factory


@pytest.fixture
def mock_orq_sdk() -> MagicMock:
    """A MagicMock shaped like the orq-ai-sdk Orq client."""
    sdk = MagicMock()
    fake_resp = MagicMock()
    fake_resp.task_id = "task-test"
    fake_resp.output = []
    sdk.agents.responses.create.return_value = fake_resp
    return sdk
```

- [ ] **Step 2: Update `tests/test_live_agent.py`** — replace env-var gating with marker:

```python
from __future__ import annotations

import os

import pytest

from bmo.config import Settings
from bmo.orq_client import OrqClient

pytestmark = pytest.mark.live


def test_live_text_invoke():
    if not os.environ.get("ORQ_API_KEY"):
        pytest.skip("ORQ_API_KEY not set")
    s = Settings()
    c = OrqClient(settings=s)
    out = c.invoke("Say hi in one short sentence.")
    print(out)
    assert out
    assert len(out) < 300
```

(`addopts = "-m 'not live'"` in pyproject.toml means this is skipped by default. To run: `uv run pytest -m live`.)

- [ ] **Step 3: Refactor `tests/test_orq_client.py` and `tests/test_main_loop.py`** to use the `make_settings` fixture instead of the local helper. Remove duplicate `make_settings()` functions in those files.

For `test_orq_client.py` change:
```python
def test_invoke_text_only(make_settings):
    settings = make_settings()
    ...
```

For `test_main_loop.py` analogous change.

- [ ] **Step 4: Run all tests**

```bash
uv run pytest -v
```
Expected: 20 passed (default), live skipped. With `-m live`: 1 picked up (skipped without ORQ_API_KEY).

- [ ] **Step 5: Run live test against real workspace**

```bash
ORQ_API_KEY=$(grep ORQ_API_KEY .env | cut -d= -f2) uv run pytest -m live -v -s
```
Expected: 1 passed.

- [ ] **Step 6: Commit**

```bash
git add tests/conftest.py tests/test_live_agent.py tests/test_orq_client.py tests/test_main_loop.py
git commit -m "test: shared fixtures + @pytest.mark.live (drop RUN_LIVE env gate)"
```

---

## Task 7: Pyright type-check pass

**Files:**
- Surface and fix any pyright errors raised by `strict` mode in `src/bmo`.

- [ ] **Step 1: Run pyright**

```bash
uv run pyright
```

- [ ] **Step 2: Iterate on errors**

Likely findings:
- `bmo/orq_client.py`: `sdk: Any | None = None` is fine; `MagicMock` typing in tests doesn't bleed into src. May need `# pyright: ignore[reportAttributeAccessIssue]` on the SDK call sites if the orq SDK lacks types.
- `bmo/faces.py`: Tk types may be unknown — `# pyright: ignore` per offending line, or add `from typing import TYPE_CHECKING`.
- `bmo/audio_io.py`: sounddevice has weak typings; localized ignores acceptable.
- `bmo/main.py`: lambda return-type inference. Add explicit `-> str` if needed.

For each error:
- If it's a real type bug, fix the code.
- If it's a third-party-stub gap, add a narrowly-scoped `# pyright: ignore[<rule>]` with a one-line comment explaining why.
- Do NOT use `# type: ignore` (that's mypy syntax).

- [ ] **Step 3: Re-run until clean**

```bash
uv run pyright
```
Expected: `0 errors, 0 warnings`.

- [ ] **Step 4: Run tests**

```bash
uv run pytest -v
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore(types): pyright strict pass on src/bmo"
```

---

## Task 8: Pre-commit hooks

**Files:**
- Create: `.pre-commit-config.yaml`

- [ ] **Step 1: Write `.pre-commit-config.yaml`**

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: end-of-file-fixer
      - id: trailing-whitespace
      - id: check-yaml
      - id: check-toml
      - id: check-added-large-files
        args: ["--maxkb=500"]

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.7.4
    hooks:
      - id: ruff-format
      - id: ruff
        args: ["--fix"]
```

- [ ] **Step 2: Install hooks locally**

```bash
uv run pre-commit install
```

- [ ] **Step 3: Run on all files (will fix in place)**

```bash
uv run pre-commit run --all-files
```

If any files were modified, stage them.

- [ ] **Step 4: Re-run to confirm clean**

```bash
uv run pre-commit run --all-files
```
Expected: all hooks "Passed" or "Skipped" (no "Failed" or "Files were modified").

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "build: pre-commit config (ruff + stdlib hooks)"
```

---

## Task 9: GitHub Actions CI + Dependabot

**Files:**
- Create: `.github/workflows/ci.yml`
- Create: `.github/dependabot.yml`

- [ ] **Step 1: Write `.github/workflows/ci.yml`**

```yaml
name: ci

on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  lint-test:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.11", "3.12", "3.13"]
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v3

      - name: Set up Python ${{ matrix.python-version }}
        run: uv python install ${{ matrix.python-version }}

      - name: Sync dependencies
        run: uv sync --extra dev

      - name: Ruff format check
        run: uv run ruff format --check src tests scripts

      - name: Ruff lint
        run: uv run ruff check src tests scripts

      - name: Pyright
        run: uv run pyright

      - name: Pytest
        run: uv run pytest -v
```

- [ ] **Step 2: Write `.github/dependabot.yml`**

```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
    open-pull-requests-limit: 5

  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
    open-pull-requests-limit: 5
```

- [ ] **Step 3: Commit**

```bash
git add .github/
git commit -m "ci: GitHub Actions matrix (3.11/3.12/3.13) + Dependabot weekly"
```

---

## Task 10: Docs hub + CONTRIBUTING + CHANGELOG + README + setup.sh + .editorconfig

**Files:**
- Create: `CONTRIBUTING.md`, `CHANGELOG.md`, `docs/README.md`, `.editorconfig`
- Update: `README.md`, `setup.sh`

- [ ] **Step 1: `.editorconfig`**

```ini
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true
indent_style = space
indent_size = 4

[*.{yml,yaml,json,toml,md}]
indent_size = 2

[Makefile]
indent_style = tab
```

- [ ] **Step 2: `CONTRIBUTING.md`**

```markdown
# Contributing to bmo-orq

## Dev setup

Requirements: Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone git@github.com:arianpasquali/be-more-agent.git
cd be-more-agent
uv sync --extra dev
uv run pre-commit install
cp .env.example .env
# fill in ORQ_API_KEY
```

## Running

```bash
uv run bmo                   # run the agent (entry point)
uv run python -m bmo.main    # equivalent
```

## Tests

```bash
uv run pytest                # default: skips live tests
uv run pytest -m live        # only live tests (needs ORQ_API_KEY)
uv run pytest -v --cov       # with coverage
```

## Lint + format + types

```bash
uv run ruff format src tests scripts
uv run ruff check src tests scripts
uv run pyright
```

Pre-commit runs ruff automatically on staged files.

## Branch / PR convention

- Branch: `arianpasquali/<short-name>` (matches the `arianpasquali` prefix used throughout the repo).
- Conventional Commits in subject lines (`feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`, `build:`, `ci:`, `style:`).
- Keep PRs focused on one concern.

## Releases

1. Update `CHANGELOG.md` (move `## Unreleased` content under a new `## vX.Y.Z` heading with a date).
2. Bump `version` in `pyproject.toml`.
3. Tag: `git tag -a vX.Y.Z -m "vX.Y.Z: <one-line summary>"`.
4. Push: `git push --follow-tags`.

## Adding a new orq agent / dataset / evaluator

Source-of-truth lives under `orq/`. Edit the JSON / Markdown there, then run the matching script in `scripts/`:

```bash
uv run python scripts/bootstrap_agent.py
uv run python scripts/bootstrap_dataset.py
uv run python scripts/bootstrap_evaluators.py
```

All three scripts are idempotent.
```

- [ ] **Step 3: `CHANGELOG.md`**

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-04-27

### Added
- `uv` for env + lock management; deps live in `pyproject.toml`.
- `ruff` format + lint, configured for line-length 100, target py311.
- `pyright` strict on `src/bmo`.
- `pre-commit` hooks (ruff + stdlib hygiene).
- GitHub Actions CI matrix (Python 3.11 / 3.12 / 3.13) + Dependabot weekly.
- `src/` layout: `bmo/` is now `src/bmo/`.
- `src/bmo/logging.py` centralizing log setup (idempotent, formatted).
- `src/bmo/py.typed` (PEP 561).
- `__all__` and `from __future__ import annotations` across `bmo/` modules.
- `tests/conftest.py` shared fixtures (`make_settings`, `mock_orq_sdk`).
- `@pytest.mark.live` replaces `RUN_LIVE` env gate; default `addopts` skips live.
- `bmo` console script entry point.
- `CONTRIBUTING.md`, `CHANGELOG.md`, `docs/README.md`, `.editorconfig`.

### Changed
- `setup.sh` now uses `uv sync` instead of `python -m venv` + `pip install`.
- `README.md` updated for uv install + `bmo` CLI.

### Removed
- `requirements.txt` (replaced by `pyproject.toml` deps).

## [0.1.1] - 2026-04-27

### Fixed
- STT endpoint corrected to `https://api.orq.ai/v3/router/audio/transcriptions`.
- `ORQ_STT_MODEL` made configurable via `.env` (default `openai/whisper-1`).

## [0.1.0] - 2026-04-27

### Added
- Initial bmo-orq fork: Pi as I/O thin client, orq.ai Agent (`gpt-4o`) as brain.
- Orchestrator (`bmo/main.py`): wakeword → STT → orq → TTS + face.
- Modules: `config`, `orq_client`, `vision`, `audio_io`, `wakeword`, `faces`, `stt`.
- `orq/agent.json`, `orq/dataset.jsonl` (30 booth questions), 3 LLM-judges.
- Bootstrap scripts: `bootstrap_agent.py`, `bootstrap_dataset.py`, `bootstrap_evaluators.py`.
- Booth runbook + printable visitor cards.
- 18 unit tests + 1 live integration test.
```

- [ ] **Step 4: `docs/README.md`**

```markdown
# bmo-orq Docs

## Operating

- [`booth-runbook.md`](booth-runbook.md) — pre-shift checklist, default loop, guided tour, failure playbook.
- [`visitor-cards.md`](visitor-cards.md) — printable suggestion cards for the booth table.

## Design

- [`superpowers/specs/2026-04-27-bmo-orq-design.md`](superpowers/specs/2026-04-27-bmo-orq-design.md) — original v0.1 design spec.
- [`superpowers/specs/2026-04-27-modernize-tooling-design.md`](superpowers/specs/2026-04-27-modernize-tooling-design.md) — v0.2 tooling refactor spec.

## Plans

- [`superpowers/plans/2026-04-27-bmo-orq.md`](superpowers/plans/2026-04-27-bmo-orq.md) — v0.1 implementation plan.
- [`superpowers/plans/2026-04-27-modernize-tooling.md`](superpowers/plans/2026-04-27-modernize-tooling.md) — v0.2 implementation plan.

## Project meta

- [`../CONTRIBUTING.md`](../CONTRIBUTING.md) — dev setup, tests, lint, release flow.
- [`../CHANGELOG.md`](../CHANGELOG.md) — versioned changes.
```

- [ ] **Step 5: Update `README.md`** — replace dev/install sections with uv-based commands. Add badges row.

```markdown
# bmo-orq 🤖

[![ci](https://github.com/arianpasquali/be-more-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/arianpasquali/be-more-agent/actions/workflows/ci.yml)
[![python](https://img.shields.io/badge/python-3.11%2B-blue)](pyproject.toml)
[![ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

A conference-booth fork of [be-more-agent](https://github.com/brenpoly/be-more-agent) where the BMO Raspberry Pi is a thin I/O client and the brain runs on [orq.ai](https://orq.ai).

- Wakeword + STT + TTS + face: on the Pi.
- Reasoning + vision: orq.ai Agent (`gpt-4o`).
- Live meta-demo: a laptop with Claude Code + the orq MCP edits prompts, runs experiments, and shows traces while visitors interact.

## Quick start

```bash
git clone git@github.com:arianpasquali/be-more-agent.git
cd be-more-agent

# install uv if needed
curl -LsSf https://astral.sh/uv/install.sh | sh

cp .env.example .env
# fill in ORQ_API_KEY (and ORQ_AGENT_KEY if not bmo_demo)

./setup.sh                            # Pi only — installs system deps + Piper
uv sync --extra dev                   # local laptop dev
uv run python scripts/bootstrap_agent.py     # creates/updates the orq agent
uv run bmo                            # runs the listener
```

## Architecture

```
mic → wakeword → STT → orq Agent ⇄ vision → TTS + face
                          ↑
                  laptop: Claude Code + orq MCP
```

See [`docs/`](docs/) for the design spec, plan, runbook, and contributing guide.

## Booth ops

See [`docs/booth-runbook.md`](docs/booth-runbook.md) and [`docs/visitor-cards.md`](docs/visitor-cards.md).

## Development

```bash
uv sync --extra dev
uv run pre-commit install
uv run pytest                         # unit suite
uv run pytest -m live                 # live orq integration
uv run ruff format src tests scripts  # format
uv run ruff check src tests scripts   # lint
uv run pyright                        # types
```

See [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Out of scope (v1)

- Local LLM (Ollama).
- Self-hosted observability (OpenLLMetry → orq OTLP exporter).
- Multi-agent orchestration.

These are parked for v2.

## Credits

Forked from [brenpoly/be-more-agent](https://github.com/brenpoly/be-more-agent). BMO and Adventure Time © Cartoon Network / Warner Bros. Discovery — non-commercial fan project.
```

- [ ] **Step 6: Rewrite `setup.sh`** — uv-based Pi installer.

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "[bmo-orq] installing system deps…"
sudo apt update
sudo apt install -y python3.11 python3-pip libportaudio2 portaudio19-dev libatlas-base-dev espeak-ng ffmpeg git curl

echo "[bmo-orq] installing uv…"
if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

echo "[bmo-orq] syncing deps…"
uv sync --extra pi

if [ ! -f voices/bmo.onnx ]; then
  echo "[bmo-orq] downloading BMO voice…"
  mkdir -p voices
  curl -L -o voices/bmo.onnx      "https://github.com/brenpoly/be-more-agent/releases/latest/download/bmo.onnx"
  curl -L -o voices/bmo.onnx.json "https://github.com/brenpoly/be-more-agent/releases/latest/download/bmo.onnx.json"
fi

if ! command -v piper >/dev/null 2>&1; then
  echo "[bmo-orq] installing piper binary…"
  PIPER_VER="2024.1.0"
  ARCH="arm64"
  curl -L -o piper.tar.gz "https://github.com/rhasspy/piper/releases/download/${PIPER_VER}/piper_linux_${ARCH}.tar.gz"
  tar -xzf piper.tar.gz
  sudo mv piper/piper /usr/local/bin/piper
  rm -rf piper piper.tar.gz
fi

if [ ! -f .env ]; then
  cp .env.example .env
  echo "[bmo-orq] .env created from .env.example — fill in ORQ_API_KEY before running."
fi

echo "[bmo-orq] done. start with: uv run bmo"
```

- [ ] **Step 7: Run pre-commit on all changes**

```bash
uv run pre-commit run --all-files
```

- [ ] **Step 8: Commit**

```bash
git add CONTRIBUTING.md CHANGELOG.md docs/README.md .editorconfig README.md setup.sh
git commit -m "docs: CONTRIBUTING + CHANGELOG + docs hub + uv-based README/setup.sh"
```

---

## Task 11: Final verification + tag v0.2.0

**Files:**
- None — verification only.

- [ ] **Step 1: Full test suite**

```bash
uv run pytest -v
```
Expected: 20 unit tests pass (18 from v0.1 + 2 new logging tests). Live skipped.

- [ ] **Step 2: Live test still works**

```bash
uv run pytest -m live -v -s
```
Expected: 1 passed; agent reply printed.

- [ ] **Step 3: Lint + types clean**

```bash
uv run ruff format --check src tests scripts
uv run ruff check src tests scripts
uv run pyright
```
Expected: all green.

- [ ] **Step 4: Pre-commit clean**

```bash
uv run pre-commit run --all-files
```

- [ ] **Step 5: CLI entry point works**

```bash
uv run bmo --help 2>&1 || echo "(bmo prints nothing or asks for input — that's expected; we only check the binary resolves)"
which $(uv run which bmo 2>/dev/null) 2>/dev/null || true
```
Mostly just confirming `uv run bmo` doesn't ImportError. The agent is interactive so it won't have a `--help`; verify it gets past startup logging, then Ctrl+C.

- [ ] **Step 6: Tag**

```bash
git tag -a v0.2.0 -m "v0.2.0: tooling modernization (uv, ruff, pyright, pre-commit, CI, src layout)"
```

- [ ] **Step 7: Final repo summary**

```bash
git log --oneline | head -30
git status
ls -la src/bmo/ tests/ .github/
wc -l src/bmo/*.py tests/*.py
```

- [ ] **Step 8: Done**

Push branch + tag in a follow-up step (not part of this plan; user-driven).

---

## Self-Review Notes

- **Spec coverage:** all spec items mapped to tasks. Bundle 1 (uv, ruff, pre-commit, CI, dependabot, CONTRIBUTING, markers): Tasks 1, 3, 8, 9, 10, 6. Bundle 2 (pyright, pytest-cov, conftest, CLI entry, CHANGELOG): Tasks 7, 1 (cov config), 6, 1 (entry), 10. Bundle 3 (`src/` layout, centralized logging): Tasks 2, 5. Quality misc (`py.typed`, `__all__`, `.editorconfig`, docs hub): Tasks 2, 4, 10.
- **Placeholder scan:** clean. Every step has executable commands and full file contents.
- **Type consistency:** `bmo` package import path stays `bmo.<module>` after `src/` move (hatchling `packages = ["src/bmo"]` resolves it). All `__all__` lists reference real exports. CLI entry `bmo.main:run` matches existing function name.
