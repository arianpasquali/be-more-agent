#!/usr/bin/env bash
# bmo-orq dev setup for macOS (laptop dev only — does NOT run the booth agent).
# Use this on your Mac to develop, run the test suite, hit the live orq agent,
# and drive the side-screen Claude Code + orq MCP demo. Pi-only deps (picamera2,
# Piper TTS, BMO voice) are skipped. For Pi installs, use ./setup-pi.sh.
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "[bmo-orq] setup-mac.sh is for macOS. On Linux/Pi run ./setup-pi.sh." >&2
  exit 1
fi

echo "[bmo-orq] checking Homebrew…"
if ! command -v brew >/dev/null 2>&1; then
  echo "[bmo-orq] Homebrew missing. Install it: https://brew.sh" >&2
  exit 1
fi

echo "[bmo-orq] installing system deps via brew…"
brew install portaudio uv

echo "[bmo-orq] installing Python 3.11 via uv…"
uv python install 3.11

echo "[bmo-orq] syncing dev deps (no --extra pi on Mac)…"
uv sync --extra dev

echo "[bmo-orq] installing pre-commit hook…"
uv run pre-commit install

if [ ! -f .env ]; then
  cp .env.example .env
  echo "[bmo-orq] .env created from .env.example — fill in ORQ_API_KEY before running tests."
fi

echo ""
echo "[bmo-orq] mac dev setup done."
echo "  unit tests:        uv run pytest"
echo "  live orq tests:    uv run pytest -m live"
echo "  lint + format:     uv run ruff check src tests scripts && uv run ruff format src tests scripts"
echo "  types:             uv run pyright"
echo ""
echo "  NOTE: 'uv run bmo' is Pi-only (needs camera + fullscreen face GUI)."
echo "        On Mac use Claude Code + orq MCP for the side-screen meta-demo."
