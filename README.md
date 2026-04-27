# bmo-orq

A conference-booth fork of [be-more-agent](https://github.com/brenpoly/be-more-agent) where the BMO Raspberry Pi is a thin I/O client and the brain runs on [orq.ai](https://orq.ai).

- Wakeword + STT + TTS + face: on the Pi.
- Reasoning + vision: orq.ai Agent (`gpt-4o`).
- Live meta-demo: a laptop with Claude Code + the orq MCP edits prompts, runs experiments, and shows traces while visitors interact.

## Quick start

```bash
git clone <this repo>
cd bmo-orq
cp .env.example .env
# fill in ORQ_API_KEY (and ORQ_AGENT_KEY if not bmo_demo)

./setup.sh                            # Pi only — installs system deps + Piper
source .venv/bin/activate
python scripts/bootstrap_agent.py     # creates/updates the orq agent
python -m bmo.main                    # runs the listener
```

## Architecture

```
mic → wakeword → STT → orq Agent ⇄ vision → TTS + face
                          ↑
                  laptop: Claude Code + orq MCP
```

See `docs/superpowers/specs/2026-04-27-bmo-orq-design.md` for the full design.

## Booth ops

See `docs/booth-runbook.md` and `docs/visitor-cards.md`.

## Development

```bash
pytest                                # unit suite
RUN_LIVE=1 pytest tests/test_live_agent.py  # live orq integration
```

## Out of scope (v1)

- Local LLM (Ollama).
- Self-hosted observability (OpenLLMetry → orq OTLP exporter).
- Multi-agent orchestration.

These are parked for v2.

## Credits

Forked from [brenpoly/be-more-agent](https://github.com/brenpoly/be-more-agent). BMO and Adventure Time © Cartoon Network / Warner Bros. Discovery — non-commercial fan project.
