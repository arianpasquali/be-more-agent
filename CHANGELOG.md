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
