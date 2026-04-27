# Modernize Python Tooling — Design

**Date:** 2026-04-27
**Status:** Design pending approval
**Owner:** Arian Pasquali
**Builds on:** v0.1.1

## Goal

Step up `bmo-orq` from "works on my laptop" to a clean, conventional 2026-Python project: `uv` package management, `ruff` lint/format, static typing, pre-commit, CI, contributor docs, and a few code-organization upgrades.

The runtime behavior of the booth demo must not change. This is a tooling/structure refactor.

## Scope (all 3 bundles approved)

### Bundle 1 — must-do
- **uv** replaces `pip` and `python -m venv`. Deps move from `requirements.txt` into `pyproject.toml`. `uv.lock` committed.
- **ruff** as formatter + linter. Replaces black/flake8/isort. Config in `pyproject.toml`.
- **pre-commit** hooks: ruff format, ruff check, end-of-file-fixer, trailing-whitespace, check-yaml, check-toml, check-added-large-files.
- **GitHub Actions CI**: matrix Python 3.11 / 3.12 / 3.13, runs `uv sync`, ruff check, ruff format --check, pytest. Live tests skipped in CI.
- **Dependabot** weekly for `pip` ecosystem and `github-actions`.
- **CONTRIBUTING.md**: dev setup, pre-commit install, test commands, release / tag conventions.
- **Pytest markers**: `@pytest.mark.live` replaces `RUN_LIVE` env-var gating.

### Bundle 2 — nice
- **pyright** static type checker. `bmo/` runs `strict`; `tests/`, `scripts/` run `basic`. Config in `pyproject.toml`.
- **pytest-cov**: coverage reporting (no hard threshold yet — surface only). Coverage config in `pyproject.toml`.
- **`tests/conftest.py`**: shared fixtures (`make_settings`, `mocked_orq_client`).
- **CLI entrypoint**: `pyproject.toml` registers `bmo = "bmo.main:run"`. `python -m bmo.main` and `bmo` both work.
- **CHANGELOG.md**: Keep-a-Changelog format. Backfills v0.1.0 + v0.1.1.

### Bundle 3 — bigger refactors
- **`src/` layout**: move `bmo/` → `src/bmo/`. Update `pyproject.toml`, imports unaffected. Pyright/pytest configs adjusted.
- **`bmo/logging.py`**: centralized logger setup (no structlog — overkill; use stdlib + named loggers). `bmo.main.run()` calls `bmo.logging.setup(level)` instead of `logging.basicConfig`.

### Quality misc
- **`bmo/py.typed`** marker (PEP 561) so downstream consumers can pick up the type hints.
- **`__all__`** in each `bmo/*.py` module to declare public API.
- **`.editorconfig`** for cross-IDE consistency.
- **`docs/README.md`** as the docs hub (links to spec, plan, runbook, contributing).

### Deliberately out of scope
- MkDocs Material site (true overkill for a demo project).
- structlog (overkill, stdlib logging is fine).
- License/notice header rewrites (LICENSE is fine as-is).

## Architecture / Resulting Repo Layout

```
bmo-orq/
├── .editorconfig
├── .github/
│   ├── workflows/ci.yml
│   └── dependabot.yml
├── .pre-commit-config.yaml
├── .python-version          # uv reads this
├── pyproject.toml           # deps, ruff, pyright, pytest, coverage, entry points
├── uv.lock                  # committed
├── CONTRIBUTING.md
├── CHANGELOG.md
├── README.md
├── LICENSE
├── setup.sh                 # Pi installer (uses uv now)
├── src/bmo/                 # was bmo/
│   ├── __init__.py
│   ├── py.typed
│   ├── audio_io.py
│   ├── config.py
│   ├── faces.py
│   ├── logging.py           # NEW: centralized log setup
│   ├── main.py
│   ├── orq_client.py
│   ├── stt.py
│   ├── vision.py
│   └── wakeword.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # NEW: shared fixtures
│   ├── test_*.py
├── scripts/
│   ├── bootstrap_agent.py
│   ├── bootstrap_dataset.py
│   └── bootstrap_evaluators.py
├── orq/
│   ├── agent.json
│   ├── dataset.jsonl
│   └── evaluators/*.md
├── docs/
│   ├── README.md            # NEW: docs hub
│   ├── booth-runbook.md
│   ├── visitor-cards.md
│   └── superpowers/specs/, plans/
├── faces/, sounds/, voices/, wakeword.onnx
└── (requirements.txt removed; deps live in pyproject.toml)
```

`requirements.txt` is removed (uv manages deps). `setup.sh` uses `uv sync` instead of pip.

## Key Configuration Choices

### `pyproject.toml` highlights
- `[project]`: name `bmo-orq`, version `0.2.0`, requires-python `>=3.11`.
- `[project.dependencies]`: runtime deps only.
- `[project.optional-dependencies]`:
  - `dev`: pytest, pytest-mock, pytest-asyncio, pytest-cov, ruff, pyright, pre-commit
  - `pi`: picamera2 (Linux/Pi only).
- `[project.scripts]`: `bmo = "bmo.main:run"`
- `[tool.ruff]`: line-length 100, target-version py311. Lints E,F,W,I,UP,B,SIM,RUF.
- `[tool.ruff.format]`: default (black-compatible).
- `[tool.pyright]`: strict for `src/bmo`, basic for `tests`/`scripts`.
- `[tool.pytest.ini_options]`: testpaths `["tests"]`, `markers = ["live: hits real orq.ai workspace"]`, default `-m "not live"`.
- `[tool.coverage.run]`: source `src/bmo`. `[tool.coverage.report]`: show-missing, no fail-under (yet).
- `[build-system]`: hatchling.

### `.pre-commit-config.yaml` hooks
- `pre-commit/pre-commit-hooks`: end-of-file-fixer, trailing-whitespace, check-yaml, check-toml, check-added-large-files (max 500kb).
- `astral-sh/ruff-pre-commit`: ruff-format + ruff (check, --fix).

### CI matrix
- Python 3.11, 3.12, 3.13 on ubuntu-latest.
- Steps: checkout, install uv, `uv sync --extra dev`, `uv run ruff format --check`, `uv run ruff check`, `uv run pytest -m "not live"`.
- No coverage gate in v1; just upload as artifact.

### Dependabot
- `pip` ecosystem weekly Mondays.
- `github-actions` weekly Mondays.

## Migration Notes (per file)

- All Python source modules: add `from __future__ import annotations` at top (cleaner forward refs under pyright). Add `__all__ = [...]` listing public names. Stdlib + third-party imports get sorted by ruff.
- `bmo/__init__.py`: re-export public surface (`Settings`, `OrqClient`, `FacePlayer`, etc.) so consumers can `from bmo import Settings`.
- `bmo/main.py`: use `bmo.logging.setup(settings.log_level)` instead of `logging.basicConfig`.
- `tests/conftest.py`: `make_settings` fixture; `mock_orq_sdk` fixture used across `test_orq_client.py` + `test_main_loop.py`.
- `tests/test_live_agent.py`: switch from env-var skip to `@pytest.mark.live`.
- `setup.sh`: drop `python3.11 -m venv` + `pip install`; use `curl -LsSf https://astral.sh/uv/install.sh | sh` then `uv sync --extra pi`.

## Versioning

Bump to **v0.2.0**: tooling-only release, no behavior change. Tag after merge.

## Testing Strategy

- All existing 18 unit tests must still pass after migration.
- Live test still passes when `pytest -m live` is invoked.
- Lint suite (`ruff check && ruff format --check`) must pass clean.
- Pyright must pass with the configured strictness levels.
- Pre-commit hooks must pass on the migration commit itself.
- CI must go green on first push after merge.
