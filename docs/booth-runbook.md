# BMO Booth Runbook

## Mode selection

Set `BMO_MODE` in `.env` before starting:

| Mode | Best for | Latency |
|------|----------|---------|
| `BMO_MODE=orq` | Prompt-edit + traces demo — visitors see full orq trace on side screen | ~2–4 s |
| `BMO_MODE=realtime` | Natural-conversation demo — sub-second latency, barge-in, no visible trace lag | <1 s |

Switch modes by editing `.env` and restarting `uv run bmo`. Both modes still require a "Hey BMO" wakeword to start.

## Display required (face GUI)

The BMO face animation requires a display. If you're connected over SSH:

```bash
export DISPLAY=:0   # Pi must have a monitor attached and X11 running
uv run bmo
```

If no display is available, BMO runs headless (no face window). Run locally from the Pi keyboard/desktop to get the face GUI.

## Pre-shift (15 min before doors open)
1. Power Pi, plug mic, plug speaker, plug screen, plug camera.
2. Confirm wifi connected (`iwconfig`). Test with `ping api.orq.ai`.
3. Activate venv: `source .venv/bin/activate`.
4. Run agent bootstrap (idempotent): `python scripts/bootstrap_agent.py`.
5. Start BMO: `python -m bmo.main`. Watch for "listening for wakeword…".
6. Open laptop browser: `https://my.orq.ai` → Traces (live).
7. Open Claude Code on laptop in this repo with orq MCP plugin loaded.
8. Place visitor cards on table.

## Default loop (~30-60 s per visitor)
- Visitor reads card → "Hey BMO" → wakeword fires → response.
- Point at side-screen showing live trace.

## Guided tour (~3-5 min, on demand)
1. **Live prompt edit:** AI Studio → BMO agent → tweak instructions → save → next utterance reflects it.
2. **Self-debug:** Claude Code → `/analyze-trace-failures last 10`.
3. **Experiment:** Claude Code → `/run-experiment` against `bmo_booth_questions` with two prompt variants.
4. **Analytics:** show `/analytics` cost + p95 latency.

## Failure playbook
| Symptom | Fix |
|---------|-----|
| BMO silent after wakeword | Check `MIC_DEVICE_INDEX` in `.env`; restart agent. |
| "I can't reach my brain" | Check wifi; try `python scripts/bootstrap_agent.py` to verify orq reachable. |
| Vision wrong rotation | Edit `CAMERA_ROTATION` in `.env`; restart. |
| Repeated wakeword false positives | Raise `WAKEWORD_THRESHOLD` to 0.6+. |
| No audio output | Check `paplay`/`ffplay` installed (`./doctor.sh`); verify default sink (`pactl info`). |

## End-of-shift
- Stop with Ctrl+C.
- ALSA shutdown error is harmless.
- `git pull` for any prompt updates.
