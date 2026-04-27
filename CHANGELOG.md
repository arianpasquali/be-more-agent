# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2026-04-28

### Added
- `BMO_MODE=realtime` — OpenAI Realtime API speech-to-speech mode. Sub-second latency, server-side VAD, native barge-in. Wakeword still gates session start; idle 90s closes the session.
- `bmo/realtime.py` — async WebSocket session loop with paplay/ffplay output and shadow trace logging through `OrqClient.invoke` per turn so traces appear in orq dashboard.
- `bmo/vad.py` — Silero VAD wrapper using the silero_vad.onnx model bundled with openwakeword. Replaces RMS silence detection in `bmo/audio_io.record_until_silence`.
- `bmo/tts.py` — orq AI Router TTS via `/v3/router/audio/speech`, returns MP3 bytes.
- Mic native sample-rate detection + on-the-fly resampling for both orq and realtime modes.
- Whisper hallucination filter in `bmo/stt.py` (drops "♪", "subscribe", foreign-language artifacts on silence).
- `language=en` and priming prompt sent to Whisper for cleaner transcripts.
- `scripts/realtime_chat.py` — standalone Realtime tester (no wakeword, no GUI).
- `scripts/chat.py` — text-only REPL against the orq agent.
- `scripts/vad_meter.py` — live VAD bars to verify mic + threshold.
- `scripts/face_trace.py` — prints face state transitions during a Realtime session.
- `.env`: `BMO_MODE`, `ORQ_TTS_MODEL`, `ORQ_TTS_VOICE`, `OPENAI_API_KEY`, `OPENAI_REALTIME_MODEL`, `OPENAI_REALTIME_VOICE`.
- Headless fallback in `bmo/main.py`: skips Tk GUI when `DISPLAY` is absent (SSH-friendly).
- `doctor.sh` checks `ffplay`/`mpg123` instead of piper.
- `setup.sh` dispatcher routes to `setup-pi.sh` or `setup-mac.sh`.

### Changed
- TTS now runs through orq AI Router (default `openai/tts-1`, voice `alloy`); no more local Piper.
- Audio output uses `paplay` (PulseAudio) when available, falling back to `ffplay`. Routes through user's selected default sink, including Bluetooth headsets.
- Default agent instructions: respond in English regardless of input language.
- `record_until_silence` now waits for first speech before counting trailing silence; logs peak VAD probability per utterance.

### Fixed
- Mic rates: USB mics rejecting 16/24 kHz now auto-fall-back to native (44.1/48 kHz) with resampling.
- ALSA single-stream constraint: wakeword stream now closes before opening the recording stream.
- Pi-only deps: pyqt5/pyqt5-qt5/pyqt5-sip overridden in `[tool.uv]` to skip on aarch64 (no wheel available).
- bmo.onnx and Piper download URLs corrected (pin v1.0-voice and 2023.11.14-2 with `aarch64` arch name).
- libcamera install: try `rpicam-apps` first (Bookworm) then `libcamera-apps` (Bullseye).
- Wakeword preprocessor models auto-download on first init.
- ALSA sample-rate fallback for `record_until_silence` and Realtime mic stream.

### Removed
- `src/bmo/observability.py` and OTel SDK / OTLP exporter deps. orq's OTel collector accepts spans but doesn't surface them in the workspace UI for non-router products. Replaced with the shadow trace logging approach in realtime mode.
- Local Piper TTS install + BMO voice download from `setup-pi.sh`.

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
