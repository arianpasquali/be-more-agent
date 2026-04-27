"""Live VAD meter — prints speech probability for every 32 ms mic chunk.

Useful to verify your mic + Silero VAD agree on what counts as speech
before running the full BMO loop. Speak — bars should hit |||| etc.

Usage:
    uv run python scripts/vad_meter.py
    MIC_DEVICE_INDEX=2 uv run python scripts/vad_meter.py
"""

from __future__ import annotations

import os
import sys

import numpy as np
import sounddevice as sd

from bmo.audio_io import _resample_to_vad
from bmo.vad import VAD_CHUNK_SAMPLES, VAD_SAMPLE_RATE, SileroVAD


def main() -> int:
    device_env = os.environ.get("MIC_DEVICE_INDEX", "")
    device = int(device_env) if device_env else None

    info = sd.query_devices(device, "input")
    native_rate = int(info["default_samplerate"])
    chunk_n = int(VAD_CHUNK_SAMPLES * native_rate / VAD_SAMPLE_RATE)

    print(f"device: {info['name']}  native rate: {native_rate} Hz")
    print("speak — Ctrl+C to stop\n")

    vad = SileroVAD()
    try:
        with sd.InputStream(
            samplerate=native_rate, channels=1, device=device, dtype="float32"
        ) as s:
            while True:
                data, _ = s.read(chunk_n)
                vad_chunk = _resample_to_vad(data[:, 0], native_rate)
                if vad_chunk.shape[0] != VAD_CHUNK_SAMPLES:
                    vad_chunk = np.resize(vad_chunk, VAD_CHUNK_SAMPLES)
                prob = vad.score(vad_chunk)
                bar = "|" * int(prob * 40)
                marker = " SPEECH" if prob >= 0.5 else ""
                sys.stdout.write(f"\r{prob:.2f} {bar:<40}{marker}    ")
                sys.stdout.flush()
    except KeyboardInterrupt:
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
