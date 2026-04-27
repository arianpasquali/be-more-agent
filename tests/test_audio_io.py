from unittest.mock import MagicMock, patch

import numpy as np

from bmo.audio_io import play_tts, record_until_silence


def test_record_until_silence_stops_on_quiet():
    samples = np.concatenate(
        [
            np.ones(16000) * 0.5,  # 1s loud
            np.zeros(16000),  # 1s silence (above threshold of 0.8s)
        ]
    ).astype(np.float32)

    fake_stream = MagicMock()
    chunks = iter([samples[i : i + 1600] for i in range(0, len(samples), 1600)])
    fake_stream.read.side_effect = lambda n: (next(chunks).reshape(-1, 1), False)

    with patch(
        "bmo.audio_io.sd.InputStream",
        return_value=MagicMock(__enter__=MagicMock(return_value=fake_stream), __exit__=MagicMock()),
    ):
        out = record_until_silence(sample_rate=16000, max_seconds=3, silence_seconds=0.8)
    assert out.shape[0] > 0


def test_play_tts_invokes_piper_subprocess():
    with patch("bmo.audio_io.subprocess.Popen") as p:
        proc = MagicMock()
        proc.communicate.return_value = (b"WAVDATA", b"")
        proc.returncode = 0
        p.return_value = proc
        with patch("bmo.audio_io._play_wav_bytes") as play:
            play_tts("hello", piper_bin="piper", voice="voices/bmo.onnx")
            play.assert_called_once()
