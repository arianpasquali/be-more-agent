from __future__ import annotations

import logging
import shutil
import subprocess

import numpy as np

log = logging.getLogger(__name__)

SILENCE_RMS = 0.02

__all__ = ["SILENCE_RMS", "play_audio_bytes", "record_until_silence"]


def _rms(chunk: np.ndarray) -> float:
    return float(np.sqrt(np.mean(chunk.astype(np.float32) ** 2)))


def record_until_silence(
    sample_rate: int = 16000,
    max_seconds: float = 8.0,
    silence_seconds: float = 0.8,
    device: int | None = None,
    chunk_ms: int = 100,
) -> np.ndarray:
    """Block-record from mic until trailing silence or max_seconds."""
    chunk_n = int(sample_rate * chunk_ms / 1000)
    silence_chunks_needed = int(silence_seconds * 1000 / chunk_ms)
    max_chunks = int(max_seconds * 1000 / chunk_ms)

    # sounddevice ships no type stubs; ignore the stub-not-found diagnostic
    import sounddevice as sd  # pyright: ignore[reportMissingTypeStubs]

    captured: list[np.ndarray] = []
    silent_run = 0

    with sd.InputStream(  # pyright: ignore[reportUnknownMemberType]
        samplerate=sample_rate, channels=1, device=device, dtype="float32"
    ) as stream:
        for _ in range(max_chunks):
            # sounddevice lacks type stubs; stream.read() returns ndarray
            data, _ = stream.read(chunk_n)  # pyright: ignore[reportUnknownMemberType]
            mono = data[:, 0]
            captured.append(mono.copy())
            silent_run = silent_run + 1 if _rms(mono) < SILENCE_RMS else 0
            if silent_run >= silence_chunks_needed and len(captured) > silence_chunks_needed:
                break

    return np.concatenate(captured) if captured else np.array([], dtype=np.float32)


def play_audio_bytes(audio_bytes: bytes) -> None:
    """Play audio bytes (mp3/wav/etc) via ffplay or mpg123 — whichever is on PATH.

    Avoids sounddevice for output because it requires a configured default
    output device and pulls the whole PortAudio output stack just to play
    a one-shot reply.
    """
    if shutil.which("ffplay"):
        cmd = ["ffplay", "-nodisp", "-autoexit", "-loglevel", "error", "-i", "pipe:0"]
    elif shutil.which("mpg123"):
        cmd = ["mpg123", "-q", "-"]
    else:
        log.error("no audio player found (install ffmpeg or mpg123)")
        return

    proc = subprocess.Popen(
        cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
    )
    _, err = proc.communicate(audio_bytes)
    if proc.returncode != 0:
        log.error("audio playback failed (%s): %s", cmd[0], err.decode("utf-8", "replace"))
