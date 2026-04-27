#!/usr/bin/env bash
# bmo-orq install for Raspberry Pi / Linux. Runs the full booth agent
# (wakeword, Pi camera, Piper TTS, fullscreen face GUI). For Mac dev use
# ./setup-mac.sh instead.
set -euo pipefail

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "[bmo-orq] setup-pi.sh is for Linux/Raspberry Pi. On macOS run ./setup-mac.sh." >&2
  exit 1
fi

# Detect arch for Piper download.
ARCH=$(uname -m)
case "$ARCH" in
  aarch64|arm64) PIPER_ARCH="aarch64" ;;
  armv7l)        PIPER_ARCH="armv7l" ;;
  x86_64)        PIPER_ARCH="x86_64" ;;
  *) echo "[bmo-orq] unsupported arch: $ARCH" >&2; exit 1 ;;
esac

echo "[bmo-orq] installing system deps…"
sudo apt update
sudo apt install -y \
  python3 python3-pip \
  libportaudio2 portaudio19-dev libopenblas-dev \
  espeak-ng ffmpeg git curl \
  python3-libcamera

# Camera CLI tools — package name differs across Pi OS releases.
# Bookworm: rpicam-apps. Bullseye: libcamera-apps. Try both, ignore failures.
sudo apt install -y rpicam-apps 2>/dev/null \
  || sudo apt install -y libcamera-apps 2>/dev/null \
  || echo "[bmo-orq] warning: neither rpicam-apps nor libcamera-apps available — vision may not work"

echo "[bmo-orq] installing uv…"
if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

echo "[bmo-orq] installing Python 3.11 via uv…"
uv python install 3.11

echo "[bmo-orq] syncing deps…"
uv sync --extra pi

# TTS now runs through orq AI Router (/v3/router/audio/speech) and audio
# is played via ffplay (installed above with ffmpeg). Local Piper is no
# longer required — for v2 we may bring back a self-hosted BMO voice.

if [ ! -f .env ]; then
  cp .env.example .env
  echo "[bmo-orq] .env created from .env.example — fill in ORQ_API_KEY before running."
fi

echo ""
echo "[bmo-orq] done. start with: uv run bmo"
echo "[bmo-orq] verify with: ./doctor.sh"
