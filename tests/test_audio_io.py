from unittest.mock import MagicMock, patch

import numpy as np

from bmo.audio_io import play_audio_bytes, record_until_silence


def test_record_until_silence_uses_vad_to_stop():
    sample_rate = 16000
    chunk_n = 512  # one VAD chunk @ 16kHz

    # Synthesize chunks: 5 silent, 8 speech, 30 silent (~960ms silence triggers VAD_END_CHUNKS=25).
    chunks: list[np.ndarray] = (
        [np.zeros(chunk_n, dtype=np.float32) for _ in range(5)]
        + [np.ones(chunk_n, dtype=np.float32) * 0.5 for _ in range(8)]
        + [np.zeros(chunk_n, dtype=np.float32) for _ in range(30)]
    )
    chunks_iter = iter(chunks)
    fake_stream = MagicMock()
    fake_stream.read.side_effect = lambda n: (next(chunks_iter).reshape(-1, 1), False)

    fake_vad = MagicMock()
    fake_vad.score.side_effect = lambda chunk: 0.8 if chunk.any() else 0.05

    with (
        patch(
            "sounddevice.InputStream",
            return_value=MagicMock(
                __enter__=MagicMock(return_value=fake_stream), __exit__=MagicMock()
            ),
        ),
        patch("bmo.audio_io.SileroVAD", return_value=fake_vad),
    ):
        out = record_until_silence(sample_rate=sample_rate, max_seconds=5, initial_wait_seconds=2)
    assert out.shape[0] > 0


def test_record_until_silence_returns_empty_on_pure_silence():
    sample_rate = 16000
    chunk_n = 512
    silent_chunks = [np.zeros(chunk_n, dtype=np.float32) for _ in range(200)]
    chunks_iter = iter(silent_chunks)
    fake_stream = MagicMock()
    fake_stream.read.side_effect = lambda n: (next(chunks_iter).reshape(-1, 1), False)

    fake_vad = MagicMock()
    fake_vad.score.return_value = 0.01

    with (
        patch(
            "sounddevice.InputStream",
            return_value=MagicMock(
                __enter__=MagicMock(return_value=fake_stream), __exit__=MagicMock()
            ),
        ),
        patch("bmo.audio_io.SileroVAD", return_value=fake_vad),
    ):
        out = record_until_silence(sample_rate=sample_rate, max_seconds=3, initial_wait_seconds=1)
    assert out.shape[0] == 0


def test_play_audio_bytes_pipes_to_ffplay():
    with (
        patch(
            "bmo.audio_io.shutil.which",
            side_effect=lambda c: "/usr/bin/ffplay" if c == "ffplay" else None,
        ),
        patch("bmo.audio_io.subprocess.Popen") as p,
    ):
        proc = MagicMock()
        proc.communicate.return_value = (b"", b"")
        proc.returncode = 0
        p.return_value = proc

        play_audio_bytes(b"MP3DATA")

        cmd = p.call_args.args[0]
        assert cmd[0] == "ffplay"
        proc.communicate.assert_called_once_with(b"MP3DATA")


def test_play_audio_bytes_logs_error_when_no_player():
    with patch("bmo.audio_io.shutil.which", return_value=None):
        play_audio_bytes(b"MP3DATA")  # should not raise
