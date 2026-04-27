#!/usr/bin/env bash
# bmo-orq doctor — checks every dependency the agent needs and reports OK / FAIL.
# Exits non-zero if any critical check fails. Pi-only and Mac-only checks are
# guarded by uname.
set -uo pipefail

GREEN=$'\033[0;32m'
RED=$'\033[0;31m'
YELLOW=$'\033[0;33m'
DIM=$'\033[2m'
NC=$'\033[0m'

PASS=0
FAIL=0
WARN=0
PLATFORM="$(uname -s)"

ok()    { echo "  ${GREEN}✓${NC} $1";              PASS=$((PASS+1)); }
fail()  { echo "  ${RED}✗${NC} $1";                FAIL=$((FAIL+1)); }
warn()  { echo "  ${YELLOW}!${NC} $1";             WARN=$((WARN+1)); }
info()  { echo "  ${DIM}·${NC} $1"; }
section() { echo ""; echo "${DIM}== $1 ==${NC}"; }

# --- platform ---
section "platform"
case "$PLATFORM" in
  Linux)  ok "Linux detected (full booth target)" ;;
  Darwin) ok "macOS detected (dev only — booth agent doesn't run here)" ;;
  *)      fail "unsupported platform: $PLATFORM" ;;
esac

# --- uv ---
section "uv + python"
if command -v uv >/dev/null 2>&1; then
  ok "uv $(uv --version 2>&1 | awk '{print $2}')"
else
  fail "uv not installed (run ./setup.sh)"
fi

if [ -f .python-version ]; then
  ok ".python-version present ($(cat .python-version))"
else
  warn ".python-version missing"
fi

if uv run python -c "import sys; assert sys.version_info >= (3, 11)" 2>/dev/null; then
  ok "Python $(uv run python -c 'import sys; print(".".join(map(str, sys.version_info[:3])))') in venv"
else
  fail "venv Python <3.11 or .venv not synced (run: uv sync --extra dev)"
fi

if [ -d .venv ]; then
  ok ".venv exists"
else
  fail ".venv missing (run: uv sync --extra dev)"
fi

# --- env ---
section "env"
if [ -f .env ]; then
  ok ".env present"
  if grep -qE '^ORQ_API_KEY=.+' .env; then
    ok "ORQ_API_KEY set"
  else
    fail "ORQ_API_KEY empty in .env"
  fi
  if grep -qE '^ORQ_AGENT_KEY=.+' .env; then
    info "ORQ_AGENT_KEY=$(grep '^ORQ_AGENT_KEY=' .env | cut -d= -f2-)"
  else
    warn "ORQ_AGENT_KEY missing — defaults to 'bmo_demo'"
  fi
else
  fail ".env missing (cp .env.example .env, then fill ORQ_API_KEY)"
fi

# --- python deps importable ---
section "python deps"
for pkg in orq_ai_sdk pydantic pydantic_settings sounddevice numpy openwakeword onnxruntime PIL httpx; do
  if uv run python -c "import $pkg" 2>/dev/null; then
    ok "$pkg"
  else
    fail "$pkg not importable"
  fi
done

# bmo package itself
if uv run python -c "import bmo; from bmo import Settings, OrqClient, FacePlayer, run" 2>/dev/null; then
  ok "bmo package importable (Settings, OrqClient, FacePlayer, run)"
else
  fail "bmo package broken — try: uv sync --extra dev"
fi

# --- network / orq reachability ---
section "orq.ai connectivity"
REACH=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 https://api.orq.ai/ 2>/dev/null || echo "000")
if [ "$REACH" = "000" ]; then
  fail "https://api.orq.ai unreachable (wifi or firewall issue)"
else
  ok "https://api.orq.ai reachable (HTTP $REACH)"
fi

if [ -f .env ]; then
  ORQ_KEY=$(grep '^ORQ_API_KEY=' .env | cut -d= -f2- | tr -d '"' | tr -d "'")
  if [ -n "$ORQ_KEY" ]; then
    HTTP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 8 \
      -H "Authorization: Bearer $ORQ_KEY" \
      https://api.orq.ai/v2/agents/bmo_demo 2>/dev/null || echo "000")
    case "$HTTP" in
      200) ok "orq agent 'bmo_demo' exists + key valid" ;;
      401|403) fail "orq auth failed (HTTP $HTTP) — check ORQ_API_KEY" ;;
      404) warn "orq agent 'bmo_demo' missing (run: uv run python scripts/bootstrap_agent.py)" ;;
      000) fail "no response from orq (network)" ;;
      *)   warn "orq returned HTTP $HTTP" ;;
    esac
  fi
fi

# --- pre-commit (dev hygiene, not relevant for Pi/production) ---
section "dev hygiene"
if uv run --quiet python -c "import pre_commit" 2>/dev/null; then
  HOOK=$(git rev-parse --git-path hooks/pre-commit 2>/dev/null || echo "")
  if [ -n "$HOOK" ] && [ -f "$HOOK" ]; then
    ok "pre-commit hook installed"
  else
    warn "pre-commit hook not installed (run: uv run pre-commit install)"
  fi
else
  info "pre-commit not installed (only needed on dev workstations — uv sync --extra dev)"
fi

# --- linux/Pi-only checks ---
if [ "$PLATFORM" = "Linux" ]; then
  section "Pi audio"
  if /sbin/ldconfig -p 2>/dev/null | grep -q libportaudio \
       || ls /usr/lib/*/libportaudio.so* >/dev/null 2>&1 \
       || ls /usr/lib/libportaudio.so* >/dev/null 2>&1; then
    ok "libportaudio2 system lib"
  else
    warn "libportaudio2 not found in standard paths (sounddevice import above is the real test)"
  fi

  if command -v ffplay >/dev/null 2>&1; then
    ok "ffplay (TTS playback) in PATH"
  elif command -v mpg123 >/dev/null 2>&1; then
    ok "mpg123 (TTS playback fallback) in PATH"
  else
    fail "neither ffplay nor mpg123 found (sudo apt install ffmpeg)"
  fi

  if [ -f wakeword.onnx ]; then
    ok "wakeword.onnx present"
  else
    fail "wakeword.onnx missing"
  fi

  # mic enumeration
  MICS=$(uv run python -c "import sounddevice as sd; print(sum(1 for d in sd.query_devices() if d['max_input_channels']>0))" 2>/dev/null || echo "?")
  if [ "$MICS" != "?" ] && [ "$MICS" != "0" ]; then
    ok "audio input devices detected: $MICS"
  else
    fail "no audio input devices (plug a USB mic; check ALSA)"
  fi

  # camera (Bookworm renamed libcamera-hello → rpicam-hello)
  CAM_CMD=""
  for c in rpicam-hello libcamera-hello; do
    if command -v "$c" >/dev/null 2>&1; then CAM_CMD="$c"; break; fi
  done
  if [ -n "$CAM_CMD" ]; then
    if "$CAM_CMD" --list-cameras 2>/dev/null | grep -qiE 'available cameras|^\s*[0-9]+\s*:'; then
      ok "Pi camera detected ($CAM_CMD)"
    else
      warn "$CAM_CMD installed but no camera reported (vision will be skipped)"
    fi
  else
    warn "rpicam-hello/libcamera-hello not present (vision will be skipped)"
  fi

  # face frames
  for s in idle listening thinking speaking error warmup; do
    cnt=$(ls faces/$s/*.png 2>/dev/null | wc -l | tr -d ' ')
    if [ "$cnt" -gt 0 ]; then
      ok "faces/$s ($cnt frames)"
    else
      warn "faces/$s empty (BMO will show black for that state)"
    fi
  done
fi

# --- macOS-only checks ---
if [ "$PLATFORM" = "Darwin" ]; then
  section "Mac dev"
  if command -v brew >/dev/null 2>&1; then
    ok "Homebrew installed"
    if brew list portaudio >/dev/null 2>&1; then
      ok "portaudio installed (brew)"
    else
      warn "portaudio not in brew (sounddevice wheel often bundles it; run brew install portaudio if mic fails)"
    fi
  else
    fail "Homebrew missing"
  fi
fi

# --- summary ---
echo ""
echo "${DIM}== summary ==${NC}"
echo "  ${GREEN}pass:${NC} $PASS    ${YELLOW}warn:${NC} $WARN    ${RED}fail:${NC} $FAIL"
if [ "$FAIL" -gt 0 ]; then
  echo "  ${RED}status: NOT READY${NC}"
  exit 1
fi
if [ "$WARN" -gt 0 ]; then
  echo "  ${YELLOW}status: ready with warnings${NC}"
  exit 0
fi
echo "  ${GREEN}status: ready${NC}"
exit 0
