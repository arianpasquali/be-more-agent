#!/usr/bin/env bash
set -euo pipefail

echo "[bmo-orq] installing system deps…"
sudo apt update
sudo apt install -y python3.11-venv python3-pip libportaudio2 portaudio19-dev libatlas-base-dev espeak-ng ffmpeg git

echo "[bmo-orq] creating venv…"
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

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

echo "[bmo-orq] done. activate with: source .venv/bin/activate; then: python -m bmo.main"
