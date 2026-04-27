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
    max_seconds: float = 10.0,
    silence_seconds: float = 1.2,
    initial_wait_seconds: float = 5.0,
    device: int | None = None,
    chunk_ms: int = 100,
) -> np.ndarray:
    """Block-record from mic until trailing silence or max_seconds.

    Two-phase recording:
      1. Wait up to initial_wait_seconds for ANY chunk above SILENCE_RMS
         (i.e. user starts speaking). Discard leading silence.
      2. Once speech detected, keep recording until silence_seconds of
         continuous silence OR total max_seconds reached.

    This avoids capturing only the gap between wakeword and the first
    word, which was producing empty / "." Whisper transcripts.
    """
    chunk_n = int(sample_rate * chunk_ms / 1000)
    silence_chunks_needed = int(silence_seconds * 1000 / chunk_ms)
    max_chunks = int(max_seconds * 1000 / chunk_ms)
    initial_wait_chunks = int(initial_wait_seconds * 1000 / chunk_ms)

    # sounddevice ships no type stubs; ignore the stub-not-found diagnostic
    import sounddevice as sd  # pyright: ignore[reportMissingTypeStubs]

    captured: list[np.ndarray] = []
    silent_run = 0
    speech_started = False
    peak_rms = 0.0

    with sd.InputStream(  # pyright: ignore[reportUnknownMemberType]
        samplerate=sample_rate, channels=1, device=device, dtype="float32"
    ) as stream:
        for i in range(max_chunks):
            data, _ = stream.read(chunk_n)  # pyright: ignore[reportUnknownMemberType]
            mono = data[:, 0]
            level = _rms(mono)
            peak_rms = max(peak_rms, level)

            if not speech_started:
                if level >= SILENCE_RMS:
                    speech_started = True
                    captured.append(mono.copy())
                elif i >= initial_wait_chunks:
                    log.info(
                        "no speech heard within %.1fs (peak rms=%.4f)",
                        initial_wait_seconds,
                        peak_rms,
                    )
                    return np.array([], dtype=np.float32)
                continue

            captured.append(mono.copy())
            silent_run = silent_run + 1 if level < SILENCE_RMS else 0
            if silent_run >= silence_chunks_needed:
                break

    if captured:
        log.info("captured %.1fs (peak rms=%.4f)", len(captured) * chunk_ms / 1000, peak_rms)
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
