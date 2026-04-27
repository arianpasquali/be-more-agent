# Realtime Mode — Architecture Decision Record

**Date:** 2026-04-28
**Status:** Implemented (v0.3.0)
**Author:** Arian Pasquali

---

## Problem

The `orq` mode pipeline (Whisper STT → orq Agent → orq TTS) introduces 2–4 s of latency per turn. At a conference booth this feels slow for natural conversation. Visitors disengage.

## Decision: BMO_MODE=realtime

Use the OpenAI Realtime API (WebSocket, `gpt-4o-realtime-preview`) for speech-to-speech with server-side VAD. The wakeword still gates session start; once open, the session handles all turn-taking.

## Why direct OpenAI (not through orq)

orq does not yet proxy WebSocket connections. The Realtime API is a full-duplex WebSocket — it cannot be routed through orq's HTTP router. We connect directly to `wss://api.openai.com/v1/realtime`.

System instructions are still pulled from `orq/agent.json` at session start and sent as the `session.update` system message, keeping the agent config as the single source of truth.

## Audio I/O contract

- **Mic input:** native rate probed via `sd.check_input_settings`. If 16 kHz or 24 kHz is rejected (common on USB mics), open at native rate (44.1/48 kHz) and resample down via `scipy.signal.resample_poly` before sending to OpenAI.
- **Wire format to OpenAI:** 24 kHz, 16-bit PCM, mono (pcm16).
- **Output from OpenAI:** 24 kHz pcm16 delta events reassembled into a complete buffer.
- **Playback:** raw pcm16 piped to `paplay --format=s16le --rate=24000 --channels=1`. Falls back to `ffplay -f s16le -ar 24000 -ac 1` if paplay is absent. Routes through the system default PulseAudio sink (Bluetooth headsets work automatically).
- **Speaking hold:** face stays in "speaking" state until the computed drain time (`len(buffer) / (24000 * 2)` seconds) elapses after paplay is spawned.

## Trace shadowing

orq's OTel collector accepts spans but they do not surface in the Traces UI for non-router products (only router-product calls generate browsable traces). To give the demo a visible trace per turn, each Realtime turn fires a fire-and-forget call:

```python
OrqClient.invoke("bmo_demo", "[realtime turn] User said X, BMO replied Y, acknowledge briefly")
```

This produces a real router-product trace (~$0.0001/turn) that appears immediately in the orq dashboard. It is logged but its response is discarded.

## Idle timeout

90 seconds of no detected speech closes the Realtime WebSocket and resumes the wakeword listener. This prevents runaway OpenAI costs if a visitor walks away mid-session.

## Out of scope (v4 candidates)

- Vision: sending camera frames as base64 image parts over the Realtime API.
- Tool calls: hooking orq tools (search, dataset lookup) into the Realtime function-call protocol.
- orq-proxied WebSocket: blocked on orq adding WebSocket proxy support.
