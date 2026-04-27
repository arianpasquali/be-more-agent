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
  libcamera-apps python3-libcamera

echo "[bmo-orq] installing uv…"
if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

echo "[bmo-orq] installing Python 3.11 via uv…"
uv python install 3.11

echo "[bmo-orq] syncing deps…"
uv sync --extra pi

# BMO voice (custom Piper model). Pinned to v1.0-voice — the "latest" GitHub
# release for this repo is v1.0-enclosure which doesn't carry voice assets.
VOICE_REL="v1.0-voice"
VOICE_BASE="https://github.com/brenpoly/be-more-agent/releases/download/${VOICE_REL}"
if [ ! -f voices/bmo.onnx ]; then
  echo "[bmo-orq] downloading BMO voice (release ${VOICE_REL})…"
  mkdir -p voices
  curl -fL --retry 3 -o voices/bmo.onnx      "${VOICE_BASE}/bmo.onnx"
  curl -fL --retry 3 -o voices/bmo.onnx.json "${VOICE_BASE}/bmo.onnx.json"
fi

# Piper binary.
PIPER_REL="2023.11.14-2"
if ! command -v piper >/dev/null 2>&1; then
  echo "[bmo-orq] installing piper binary (release ${PIPER_REL}, arch ${PIPER_ARCH})…"
  curl -fL --retry 3 -o piper.tar.gz \
    "https://github.com/rhasspy/piper/releases/download/${PIPER_REL}/piper_linux_${PIPER_ARCH}.tar.gz"
  tar -xzf piper.tar.gz
  sudo mv piper/piper /usr/local/bin/piper
  # Piper ships its bundled libs alongside the binary.
  sudo cp -r piper/* /usr/local/share/piper/ 2>/dev/null || true
  rm -rf piper piper.tar.gz
fi

if [ ! -f .env ]; then
  cp .env.example .env
  echo "[bmo-orq] .env created from .env.example — fill in ORQ_API_KEY before running."
fi

echo ""
echo "[bmo-orq] done. start with: uv run bmo"
echo "[bmo-orq] verify with: ./doctor.sh"
