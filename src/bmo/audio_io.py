import io
import logging
import subprocess
import wave

import numpy as np
import sounddevice as sd

log = logging.getLogger(__name__)

SILENCE_RMS = 0.02


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

    captured: list[np.ndarray] = []
    silent_run = 0

    with sd.InputStream(
        samplerate=sample_rate, channels=1, device=device, dtype="float32"
    ) as stream:
        for _ in range(max_chunks):
            data, _ = stream.read(chunk_n)
            mono = data[:, 0]
            captured.append(mono.copy())
            silent_run = silent_run + 1 if _rms(mono) < SILENCE_RMS else 0
            if silent_run >= silence_chunks_needed and len(captured) > silence_chunks_needed:
                break

    return np.concatenate(captured) if captured else np.array([], dtype=np.float32)


def _play_wav_bytes(wav_bytes: bytes) -> None:
    with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
        rate = wf.getframerate()
        frames = wf.readframes(wf.getnframes())
        audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    sd.play(audio, samplerate=rate)
    sd.wait()


def play_tts(text: str, piper_bin: str = "piper", voice: str = "voices/bmo.onnx") -> None:
    proc = subprocess.Popen(
        [piper_bin, "--model", voice, "--output_raw"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    out, err = proc.communicate(text.encode("utf-8"))
    if proc.returncode != 0:
        log.error("piper failed: %s", err.decode("utf-8", "replace"))
        return
    # Wrap raw int16 PCM into a wave container at piper default 22050.
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(22050)
        wf.writeframes(out)
    _play_wav_bytes(buf.getvalue())
