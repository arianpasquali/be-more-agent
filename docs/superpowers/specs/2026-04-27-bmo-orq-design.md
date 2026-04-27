# BMO × orq.ai — Live Agent Booth Demo

**Date:** 2026-04-27
**Status:** Design approved, pending implementation plan
**Owner:** Arian Pasquali

## Goal

Fork the [Be More Agent](https://github.com/brenpoly/be-more-agent) Raspberry Pi BMO project into an orq.ai-backed conference booth demo (`bmo-orq`). The Pi is reduced to a thin I/O client (mic, speaker, face, camera, wakeword). All reasoning runs on an orq.ai Agent. A laptop runs Claude Code with the orq MCP server for live meta-demo (prompt edits, trace analysis, experiments).

The demo simultaneously showcases:
1. **Platform power** — edit agent/prompts in AI Studio, robot personality changes live.
2. **Observability** — every utterance produces a trace visible on a side screen.
3. **Orchestration & MCP** — Claude Code on the laptop drives orq via MCP for analyze-trace-failures, run-experiment, etc.

Local LLM support and self-hosted observability (OpenTelemetry from on-Pi Ollama) are explicitly out of scope for v1 and parked for v2.

## Architecture

```
Visitor mic → Pi (wakeword + STT) → orq Agent (cloud) → Pi (TTS + face)
                                          ↑
                              Laptop (Claude Code + orq MCP)
                                  - edit prompt in Studio
                                  - run /analyze-trace-failures
                                  - run /run-experiment
                                  - show /traces, /analytics
```

- **Pi role:** ears, mouth, face, camera. Pure I/O. No LLM, no Ollama.
- **Orq role:** brain. Single Agent (chat + vision via `gpt-4o`). System prompt, memory store, model — all editable in AI Studio.
- **Laptop role:** side-screen running orq trace dashboard, plus a Claude Code session with the orq MCP for the guided tour.

## Components

| Component | Where | Purpose |
|-----------|-------|---------|
| `agent.py` | Pi | Orchestrator: wakeword → STT → orq invoke → TTS + face. |
| `orq_client.py` | Pi | Thin wrapper around orq Agent invoke (handles vision attach). |
| `config.py` | Pi | Loads `.env`, exposes typed settings. |
| `vision.py` | Pi | Camera capture + base64 encoding. |
| `audio_io.py` | Pi | Mic input + Piper TTS playback. |
| `faces.py` | Pi | PNG-sequence face player tied to state. |
| `wakeword.py` | Pi | OpenWakeWord wrapper. |
| `.env` | Pi | All secrets and tunables. |
| BMO Agent | orq cloud | Chat + vision agent. Holds system prompt, memory, model. |
| Booth dataset | orq cloud | ~30 synthetic visitor questions, generated via `generate-synthetic-dataset`. |
| Eval suite | orq cloud | 2-3 LLM-judges (helpfulness, on-personality, response length). |
| Side-screen UI | Laptop | Browser tab on orq trace dashboard. |
| Claude Code session | Laptop | orq MCP loaded; runs experiments and edits agents on demand. |

## Configuration (`.env`)

All runtime settings live in `.env`. `.env.example` is committed; `.env` is gitignored.

```env
# orq
ORQ_API_KEY=
ORQ_AGENT_KEY=bmo_demo
ORQ_MODEL=openai/gpt-4o
ORQ_VISION_MODEL=openai/gpt-4o
ORQ_WORKSPACE_URL=https://my.orq.ai

# pi audio
MIC_DEVICE_INDEX=
SAMPLE_RATE=16000
PIPER_VOICE=voices/bmo.onnx
PIPER_RATE=22050

# wakeword
WAKEWORD_PATH=wakeword.onnx
WAKEWORD_THRESHOLD=0.5

# behavior
SESSION_TIMEOUT_SEC=30
VISION_CAPTURE_TRIGGER=see|look|what.*you.*see
CAMERA_ROTATION=0

# logging
LOG_LEVEL=INFO
```

`config.py` validates required fields at startup and fails fast if `ORQ_API_KEY` or `ORQ_AGENT_KEY` is missing.

## Visitor Flow

### Default loop (~30–60 s)

1. Visitor reads suggestion card on the table → says "Hey BMO" → wakeword fires → ack sound + listening face.
2. Pi STT transcribes utterance.
3. If transcript matches `VISION_CAPTURE_TRIGGER`, Pi grabs a single camera frame.
4. Pi calls orq Agent invoke (text + optional image as multimodal payload).
5. Pi plays response via Piper TTS while showing the speaking face.
6. Trace appears live on the side-screen dashboard.

### Guided tour (~3–5 min, on demand)

1. Open AI Studio → tweak system prompt (e.g., "now talk like a pirate") → save → next visitor utterance reflects the change.
2. Switch to Claude Code on laptop → run `/analyze-trace-failures last 10` → weak answers and failure modes surface.
3. Run `/run-experiment` against the booth dataset, comparing 2 prompts → results table on screen → pick the winner.
4. Show the `/analytics` panel: cost, p95 latency, token usage.

## Vision Flow

- Vision-capable agent model (`gpt-4o` by default) handles both text and image input — no separate vision agent needed.
- Trigger: regex on the STT transcript (`VISION_CAPTURE_TRIGGER`).
- On match, `vision.py` captures one frame, applies `CAMERA_ROTATION`, encodes as base64, attaches as an image input item to the orq Agent invoke payload.

## Error Handling

Boundary conditions only — no defensive code in internal paths:

- **Network / orq unreachable:** play `error_sounds/` + show error face → speak "I can't reach my brain right now."
- **Orq 5xx:** one retry with short backoff, then fall back to the same error message.
- **STT empty / silence:** play ack tone, re-listen for 5 s, then return to idle.
- **TTS failure:** log and skip; do not crash the loop.
- All errors are logged at the configured `LOG_LEVEL`. Cloud-side errors are visible in the orq trace.

## Testing Strategy

- **Unit:** `config.py` env loading and validation; vision-trigger regex; orq client retry logic; faces state transitions.
- **Live integration (real orq workspace, low cost):**
  - Build the BMO agent on orq via MCP (`create_agent`) and call `invoke_agent` from the laptop before any Pi work.
  - Verify the resulting trace shows up via `list_traces` / `get_span`.
  - Round-trip a multimodal payload (text + base64 image) and confirm vision response.
- **Manual:** Pi-on-desk dry run with the printed visitor cards before the booth.
- **Demo eval = the test:** `generate-synthetic-dataset` produces the booth dataset; `run-experiment` against it is both the demo content and the regression gate before each event.

Pi work and orq config work parallelize: the orq agent and dataset can be built, evaluated, and iterated from the laptop alone (mocked mic input, real orq calls) while the Pi hardware is being assembled.

## Repo Structure

Hard fork, renamed to `bmo-orq`. Local-LLM bits (Ollama, Whisper.cpp local, local Piper management beyond the bundled BMO voice) are removed.

```
bmo-orq/
├── agent.py              # orchestrator
├── orq_client.py         # orq Agent wrapper
├── config.py             # .env loader
├── vision.py             # camera capture + base64
├── audio_io.py           # mic + Piper TTS
├── faces.py              # PNG sequence player
├── wakeword.py           # OpenWakeWord wrapper
├── .env.example
├── requirements.txt
├── setup.sh              # Pi installer (no Ollama)
├── faces/, sounds/, voices/, wakeword.onnx
├── docs/
│   ├── booth-runbook.md  # tour script + troubleshooting
│   └── visitor-cards.md  # printable suggestions
└── orq/                  # exported orq configs (source of truth in git)
    ├── agent.json
    ├── dataset.jsonl
    └── evaluators/*.md
```

## Out of Scope (v1)

- Local LLM (Ollama) execution path.
- OpenTelemetry / OpenLLMetry instrumentation of any local model.
- Multi-agent orchestration (leader + specialists).
- External tools beyond what `gpt-4o` provides natively (no DuckDuckGo, no custom HTTP tools).
- On-Pi Claude Code or on-Pi MCP server.
- Self-running autonomous demo loop (visitor-less).

## v2 Candidates (parked)

- `--backend=orq|local` mode flag with on-Pi Ollama as a wifi-failure fallback.
- OpenLLMetry → orq OTLP exporter so local Ollama traces land in the same orq dashboard for parity demos.
- On-Pi Claude Code session with orq MCP for "BMO debugs itself" introspection.
