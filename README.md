# bmo-orq 🤖

[![ci](https://github.com/arianpasquali/be-more-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/arianpasquali/be-more-agent/actions/workflows/ci.yml)
[![python](https://img.shields.io/badge/python-3.11%2B-blue)](pyproject.toml)
[![ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

A conference-booth fork of [be-more-agent](https://github.com/brenpoly/be-more-agent) where the BMO Raspberry Pi is a thin I/O client and the brain runs on [orq.ai](https://orq.ai).

- Wakeword + STT + TTS + face: on the Pi.
- Reasoning + vision: orq.ai Agent (`gpt-4o`).
- Live meta-demo: a laptop with Claude Code + the orq MCP edits prompts, runs experiments, and shows traces while visitors interact.

## Two demo modes

BMO supports two operating modes selected via `BMO_MODE` in `.env`:

| Mode | How it works | Latency | Traces |
|------|-------------|---------|--------|
| `orq` (default) | Wakeword → Whisper STT → orq Agent → orq TTS → paplay | ~2–4 s | Full router trace in orq dashboard |
| `realtime` | Wakeword opens OpenAI Realtime API WebSocket; server-side VAD + barge-in | <1 s | Shadow trace per turn via `OrqClient.invoke` |

**`BMO_MODE=orq`** is best for the demo laptop: you can edit the system prompt live, run experiments, and show visitors the full trace in the orq UI.

**`BMO_MODE=realtime`** is best for natural conversation demos: sub-second latency, barge-in, server-side VAD. An idle session (90 s of no detected speech) closes automatically and wakeword resumes.

## Quick start

```bash
git clone git@github.com:arianpasquali/be-more-agent.git
cd be-more-agent

# install uv if needed
curl -LsSf https://astral.sh/uv/install.sh | sh

cp .env.example .env
# fill in ORQ_API_KEY (and ORQ_AGENT_KEY if not bmo_demo)
# for realtime mode also set OPENAI_API_KEY

./setup.sh                                    # auto: setup-pi.sh on Linux/Pi, setup-mac.sh on macOS
# or call directly: ./setup-pi.sh / ./setup-mac.sh
./doctor.sh                                   # check everything is wired up
uv run python scripts/bootstrap_agent.py      # creates/updates the orq agent
uv run bmo                                    # Pi only — runs the booth listener
```

To run in realtime mode:

```bash
BMO_MODE=realtime uv run bmo
# or set BMO_MODE=realtime in .env
```

## Environment variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ORQ_API_KEY` | yes | — | orq.ai workspace API key |
| `ORQ_AGENT_KEY` | no | `bmo_demo` | orq agent key |
| `BMO_MODE` | no | `orq` | `orq` or `realtime` |
| `ORQ_TTS_MODEL` | no | `openai/tts-1` | TTS model via orq AI Router |
| `ORQ_TTS_VOICE` | no | `alloy` | TTS voice |
| `OPENAI_API_KEY` | realtime only | — | OpenAI key for Realtime API |
| `OPENAI_REALTIME_MODEL` | no | `gpt-4o-realtime-preview` | Realtime model |
| `OPENAI_REALTIME_VOICE` | no | `alloy` | Realtime voice |
| `MIC_DEVICE_INDEX` | no | auto | sounddevice input index |
| `WAKEWORD_THRESHOLD` | no | `0.5` | Detection sensitivity (0–1) |

## Architecture

```
mic → wakeword → STT → orq Agent ⇄ vision → TTS + face
                          ↑
                  laptop: Claude Code + orq MCP

-- or (BMO_MODE=realtime) --

mic → wakeword → OpenAI Realtime WebSocket → paplay → face
                          ↓
               shadow OrqClient.invoke → orq trace
```

Audio output uses `paplay` (PulseAudio) when available, falling back to `ffplay`. On Pi, `paplay` is installed by `setup-pi.sh` via `apt install pulseaudio-utils`. It routes through the system default sink, so Bluetooth headsets work automatically.

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
- Multi-agent orchestration.
- Vision in realtime mode (v4 candidate).
- Tool calls in realtime mode (v4 candidate).

## Credits

Forked from [brenpoly/be-more-agent](https://github.com/brenpoly/be-more-agent). BMO and Adventure Time © Cartoon Network / Warner Bros. Discovery — non-commercial fan project.
