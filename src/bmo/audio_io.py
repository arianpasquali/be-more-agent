from __future__ import annotations

import logging
import shutil
import subprocess

import numpy as np

from bmo.vad import VAD_CHUNK_SAMPLES, VAD_SAMPLE_RATE, SileroVAD

log = logging.getLogger(__name__)

# Silero VAD speech-probability threshold and run lengths (in 32 ms chunks).
VAD_SPEECH_THRESHOLD = 0.5
VAD_START_CHUNKS = 3  # ~96 ms above threshold to consider speech started
VAD_END_CHUNKS = 25  # ~800 ms below threshold to consider utterance ended

__all__ = [
    "VAD_END_CHUNKS",
    "VAD_SPEECH_THRESHOLD",
    "VAD_START_CHUNKS",
    "play_audio_bytes",
    "record_until_silence",
]


def _resample_to_vad(chunk: np.ndarray, src_rate: int) -> np.ndarray:
    """Downsample a recording chunk to 16 kHz mono float32 for the VAD."""
    if src_rate == VAD_SAMPLE_RATE:
        return chunk.astype(np.float32, copy=False)
    # scipy.signal lacks type stubs; cast away pyright noise locally.
    from scipy.signal import resample_poly  # pyright: ignore[reportMissingTypeStubs, reportUnknownVariableType]  # noqa: I001

    out = resample_poly(chunk, VAD_SAMPLE_RATE, src_rate)  # pyright: ignore[reportUnknownVariableType, reportUnknownArgumentType]
    return np.asarray(out, dtype=np.float32)


def record_until_silence(
    sample_rate: int = 16000,
    max_seconds: float = 12.0,
    initial_wait_seconds: float = 6.0,
    device: int | None = None,
) -> np.ndarray:
    """Record from mic until Silero VAD detects end-of-utterance.

    Two-phase:
      1. Wait up to initial_wait_seconds for the first chunk-run above
         the VAD speech threshold.
      2. Capture audio until VAD reports VAD_END_CHUNKS of trailing silence
         OR total max_seconds reached.

    Returns float32 audio at the input device's native sample rate (caller
    passes that rate forward to STT). VAD itself runs on a 16 kHz copy.
    """
    # sounddevice ships no type stubs; ignore the stub-not-found diagnostic
    import sounddevice as sd  # pyright: ignore[reportMissingTypeStubs]

    vad = SileroVAD()
    # Native input chunk size that corresponds to one 16 kHz VAD chunk.
    chunk_n = int(VAD_CHUNK_SAMPLES * sample_rate / VAD_SAMPLE_RATE)
    chunk_seconds = VAD_CHUNK_SAMPLES / VAD_SAMPLE_RATE
    max_chunks = int(max_seconds / chunk_seconds)
    initial_wait_chunks = int(initial_wait_seconds / chunk_seconds)

    captured: list[np.ndarray] = []
    speech_run = 0
    silence_run = 0
    speech_started = False
    peak_prob = 0.0

    with sd.InputStream(  # pyright: ignore[reportUnknownMemberType]
        samplerate=sample_rate, channels=1, device=device, dtype="float32"
    ) as stream:
        for i in range(max_chunks):
            data, _ = stream.read(chunk_n)  # pyright: ignore[reportUnknownMemberType]
            mono = data[:, 0]
            vad_chunk = _resample_to_vad(mono, sample_rate)
            # Defensive: if resample produces a slightly off length, pad/trim.
            if vad_chunk.shape[0] < VAD_CHUNK_SAMPLES:
                vad_chunk = np.pad(vad_chunk, (0, VAD_CHUNK_SAMPLES - vad_chunk.shape[0]))
            elif vad_chunk.shape[0] > VAD_CHUNK_SAMPLES:
                vad_chunk = vad_chunk[:VAD_CHUNK_SAMPLES]

            prob = vad.score(vad_chunk)
            peak_prob = max(peak_prob, prob)

            if not speech_started:
                if prob >= VAD_SPEECH_THRESHOLD:
                    speech_run += 1
                else:
                    speech_run = 0
                if speech_run >= VAD_START_CHUNKS:
                    speech_started = True
                    captured.append(mono.copy())
                elif i >= initial_wait_chunks:
                    log.info(
                        "no speech detected within %.1fs (peak vad=%.2f)",
                        initial_wait_seconds,
                        peak_prob,
                    )
                    return np.array([], dtype=np.float32)
                continue

            captured.append(mono.copy())
            if prob < VAD_SPEECH_THRESHOLD:
                silence_run += 1
            else:
                silence_run = 0
            if silence_run >= VAD_END_CHUNKS:
                break

    if captured:
        seconds = len(captured) * chunk_seconds
        log.info("captured %.1fs (peak vad=%.2f)", seconds, peak_prob)
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
