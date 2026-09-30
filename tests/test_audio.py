import numpy as np
import pytest

from whispr import audio
from whispr.audio import Recorder, SecureAudioBuffer


class TestSecureAudioBuffer:
    def test_starts_empty_zeroed_and_locked(self):
        b = SecureAudioBuffer(seconds=1)
        assert b.length == 0 and len(b.data) == 16000
        assert not b.data.any()
        assert b.locked  # mlock succeeded: pages can't be swapped to disk
        b.close()

    def test_dtype_is_float32(self):
        b = SecureAudioBuffer(seconds=1)
        assert b.data.dtype == np.float32
        b.close()

    def test_append_stores_samples(self):
        b = SecureAudioBuffer(seconds=1)
        assert b.append(np.array([0.1, 0.2, 0.3], np.float32)) is True
        assert b.length == 3 and b.view().tolist() == pytest.approx([0.1, 0.2, 0.3])

    def test_successive_appends_concatenate(self):
        b = SecureAudioBuffer(seconds=1)
        b.append(np.ones(10, np.float32))
        b.append(np.full(5, 0.5, np.float32))
        assert b.length == 15 and b.view()[9] == 1.0 and b.view()[10] == 0.5

    def test_append_past_capacity_clips_and_reports_full(self):
        b = SecureAudioBuffer(seconds=1)
        assert b.append(np.ones(15000, np.float32)) is True
        assert b.append(np.ones(5000, np.float32)) is False
        assert b.length == 16000
        assert b.append(np.ones(1, np.float32)) is False and b.length == 16000

    def test_append_empty(self):
        b = SecureAudioBuffer(seconds=1)
        assert b.append(np.zeros(0, np.float32)) is True and b.length == 0

    def test_view_is_zero_copy(self):
        b = SecureAudioBuffer(seconds=1)
        b.append(np.ones(100, np.float32))
        assert np.shares_memory(b.view(), b.data)

    def test_wipe_zeroes_written_region_and_resets(self):
        b = SecureAudioBuffer(seconds=1)
        b.append(np.full(500, 0.7, np.float32))
        v = b.view()
        b.wipe()
        assert b.length == 0 and not b.data.any()
        assert not v.any()  # views handed out earlier see the zeros too

    def test_wipe_on_empty_buffer(self):
        b = SecureAudioBuffer(seconds=1)
        b.wipe()
        assert b.length == 0

    def test_close_zeroes_everything_and_unlocks(self):
        b = SecureAudioBuffer(seconds=1)
        b.data[-1] = 0.9  # even data beyond `length`
        b.close()
        assert not b.data.any() and b.length == 0 and not b.locked

    def test_close_is_idempotent(self):
        b = SecureAudioBuffer(seconds=1)
        b.close()
        b.close()
        assert not b.locked

    def test_reusable_after_wipe(self):
        b = SecureAudioBuffer(seconds=1)
        b.append(np.ones(10, np.float32))
        b.wipe()
        b.append(np.full(3, 0.2, np.float32))
        assert b.length == 3 and b.view().tolist() == pytest.approx([0.2] * 3)


class FakeStream:
    instances = []

    def __init__(self, fail_start=0, **kw):
        self.kw, self.active, self.closed = kw, False, False
        self.fail_start = fail_start
        FakeStream.instances.append(self)

    def start(self):
        if self.fail_start:
            self.fail_start -= 1
            raise RuntimeError("PortAudio error")
        self.active = True

    def stop(self):
        self.active = False

    def close(self):
        self.closed = True


@pytest.fixture
def fake_sd(monkeypatch):
    FakeStream.instances = []
    monkeypatch.setattr(audio.sd, "InputStream", lambda **kw: FakeStream(**kw))
    monkeypatch.setattr(audio, "MAX_SECONDS", 2)
    return FakeStream


def frames(values):
    return np.array(values, np.float32).reshape(-1, 1)


class TestRecorder:
    def test_prepare_creates_stream_with_whisper_format(self, fake_sd):
        r = Recorder()
        r.prepare()
        kw = fake_sd.instances[0].kw
        assert (kw["samplerate"], kw["channels"], kw["dtype"]) == (16000, 1, "float32")
        assert kw["callback"] == r._callback
        assert not r.recording  # prepared, not started: mic stays off

    def test_prepare_failure_leaves_no_stream(self, monkeypatch):
        def boom(**kw):
            raise RuntimeError("no device")

        monkeypatch.setattr(audio.sd, "InputStream", boom)
        r = Recorder()
        r.prepare()
        assert r._stream is None

    def test_start_uses_prepared_stream(self, fake_sd):
        r = Recorder()
        r.prepare()
        assert r.start() is True and r.recording
        assert len(fake_sd.instances) == 1  # reused, not recreated

    def test_start_creates_stream_if_needed(self, fake_sd):
        r = Recorder()
        assert r.start() is True and len(fake_sd.instances) == 1

    def test_start_wipes_previous_recording(self, fake_sd):
        r = Recorder()
        r.start()
        r._callback(frames([0.5] * 100), 100, None, None)
        r.stop()
        r.start()
        assert len(r.audio()) == 0

    def test_start_retries_once_with_fresh_stream(self, monkeypatch):
        FakeStream.instances = []
        attempts = iter([1, 0])  # first stream fails to start, second works
        monkeypatch.setattr(audio.sd, "InputStream", lambda **kw: FakeStream(fail_start=next(attempts), **kw))
        r = Recorder()
        assert r.start() is True
        assert len(FakeStream.instances) == 2 and FakeStream.instances[0].closed

    def test_start_gives_up_after_two_failures(self, monkeypatch, capsys):
        monkeypatch.setattr(audio.sd, "InputStream", lambda **kw: FakeStream(fail_start=9, **kw))
        r = Recorder()
        assert r.start() is False and r._stream is None
        assert "could not open microphone" in capsys.readouterr().err

    def test_stop_turns_mic_off_but_keeps_audio(self, fake_sd):
        r = Recorder()
        r.start()
        r._callback(frames([0.4] * 50), 50, None, None)
        r.stop()
        assert not r.recording and len(r.audio()) == 50 and r.level() == 0.0

    def test_stop_without_stream_is_safe(self):
        Recorder().stop()

    def test_wipe_returns_stats_and_zeroes(self, fake_sd):
        r = Recorder()
        r.start()
        r._callback(frames([0.1, -0.8, 0.3] * 16000), 48000, None, None)
        secs, peak, verified = r.wipe()
        assert secs == pytest.approx(3.0) and peak == pytest.approx(0.8) and verified is True
        assert len(r.audio()) == 0 and not r.buffer.data.any()

    def test_wipe_empty(self):
        assert Recorder().wipe() == (0.0, 0.0, True)

    def test_audio_is_view_of_buffer(self, fake_sd):
        r = Recorder()
        r.start()
        r._callback(frames([0.2] * 10), 10, None, None)
        assert np.shares_memory(r.audio(), r.buffer.data)

    def test_callback_silence_keeps_level_zero(self):
        r = Recorder()
        r._callback(frames([0.0] * 512), 512, None, None)
        assert r.level() == 0.0

    def test_callback_loud_signal_raises_level_fast(self):
        r = Recorder()
        r._callback(frames([0.3] * 512), 512, None, None)  # -10.5 dBFS: above the -12 dB ceiling
        assert r.level() == pytest.approx(0.6)  # 60% attack on the first block

    def test_level_saturates_at_one(self):
        r = Recorder()
        for _ in range(20):
            r._callback(frames([1.0] * 512), 512, None, None)
        assert r.level() == pytest.approx(1.0) and r.level() <= 1.0

    def test_level_decays_slower_than_it_rises(self):
        r = Recorder()
        for _ in range(20):
            r._callback(frames([1.0] * 512), 512, None, None)
        r._callback(frames([0.0] * 512), 512, None, None)
        assert r.level() == pytest.approx(0.8)  # 20% release

    def test_callback_zero_frames(self):
        r = Recorder()
        r._callback(frames([]), 0, None, None)
        assert r.level() == 0.0

    def test_level_ignores_t_argument(self):
        r = Recorder()
        r._level = 0.42
        assert r.level() == r.level(123.0) == 0.42

    def test_recording_false_without_stream(self):
        assert Recorder().recording is False
