# bmo-orq 🤖

[![ci](https://github.com/arianpasquali/be-more-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/arianpasquali/be-more-agent/actions/workflows/ci.yml)
[![python](https://img.shields.io/badge/python-3.11%2B-blue)](pyproject.toml)
[![ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

A conference-booth fork of [be-more-agent](https://github.com/brenpoly/be-more-agent) where the BMO Raspberry Pi is a thin I/O client and the brain runs on [orq.ai](https://orq.ai).

- Wakeword + STT + TTS + face: on the Pi.
- Reasoning + vision: orq.ai Agent (`gpt-4o`).
- Live meta-demo: a laptop with Claude Code + the orq MCP edits prompts, runs experiments, and shows traces while visitors interact.

## Quick start

```bash
git clone git@github.com:arianpasquali/be-more-agent.git
cd be-more-agent

# install uv if needed
curl -LsSf https://astral.sh/uv/install.sh | sh

cp .env.example .env
# fill in ORQ_API_KEY (and ORQ_AGENT_KEY if not bmo_demo)

./setup.sh                                    # auto: setup-pi.sh on Linux/Pi, setup-mac.sh on macOS
# or call directly: ./setup-pi.sh / ./setup-mac.sh
uv run python scripts/bootstrap_agent.py      # creates/updates the orq agent
uv run bmo                                    # Pi only — runs the booth listener
```

## Architecture

```
mic → wakeword → STT → orq Agent ⇄ vision → TTS + face
                          ↑
                  laptop: Claude Code + orq MCP
```

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
- Self-hosted observability (OpenLLMetry → orq OTLP exporter).
- Multi-agent orchestration.

These are parked for v2.

## Credits

Forked from [brenpoly/be-more-agent](https://github.com/brenpoly/be-more-agent). BMO and Adventure Time © Cartoon Network / Warner Bros. Discovery — non-commercial fan project.
