#!/usr/bin/env bash
# bmo-orq install for Raspberry Pi / Linux. Runs the full booth agent
# (wakeword, Pi camera, Piper TTS, fullscreen face GUI). For Mac dev use
# ./setup-mac.sh instead.
set -euo pipefail

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "[bmo-orq] setup-pi.sh is for Linux/Raspberry Pi. On macOS run ./setup-mac.sh." >&2
  exit 1
fi

echo "[bmo-orq] installing system deps…"
sudo apt update
sudo apt install -y python3 python3-pip libportaudio2 portaudio19-dev libopenblas-dev espeak-ng ffmpeg git curl

echo "[bmo-orq] installing uv…"
if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

echo "[bmo-orq] installing Python 3.11 via uv…"
uv python install 3.11

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
