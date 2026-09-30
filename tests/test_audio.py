import threading

import numpy as np
import pytest

from mhispr import audio
from mhispr.audio import Recorder, SecureAudioBuffer


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


class FakeLibc:
    """Spy for the C library: records mlock/munlock and can simulate mlock failure."""

    def __init__(self, mlock_result=0):
        self.mlock_result = mlock_result
        self.calls = []

    def mlock(self, ptr, n):
        self.calls.append(("mlock", n.value))
        return self.mlock_result

    def munlock(self, ptr, n):
        self.calls.append(("munlock", n.value))
        return 0


class TestMemoryLocking:
    def test_locks_exact_buffer_size(self, monkeypatch):
        libc = FakeLibc()
        monkeypatch.setattr(audio, "_libc", libc)
        b = SecureAudioBuffer(seconds=1)
        assert b.locked and libc.calls == [("mlock", 16000 * 4)]

    def test_close_unlocks_once(self, monkeypatch):
        libc = FakeLibc()
        monkeypatch.setattr(audio, "_libc", libc)
        b = SecureAudioBuffer(seconds=1)
        b.close()
        b.close()
        assert libc.calls == [("mlock", 64000), ("munlock", 64000)]

    def test_mlock_failure_is_reported_and_not_unlocked(self, monkeypatch, capsys):
        libc = FakeLibc(mlock_result=-1)
        monkeypatch.setattr(audio, "_libc", libc)
        b = SecureAudioBuffer(seconds=1)
        assert b.locked is False
        assert "mlock failed" in capsys.readouterr().err
        b.close()
        assert ("munlock", 64000) not in libc.calls

    def test_mlock_success_is_silent(self, monkeypatch, capsys):
        monkeypatch.setattr(audio, "_libc", FakeLibc())
        SecureAudioBuffer(seconds=1)
        assert capsys.readouterr().err == ""

    def test_default_capacity_is_ten_minutes(self, monkeypatch):
        monkeypatch.setattr(audio, "_libc", FakeLibc())
        assert audio.MAX_SECONDS == 600
        assert len(SecureAudioBuffer().data) == 600 * 16000


class FakeEngine:
    """Stands in for MicEngine: records calls; `feed()` plays samples in as CoreAudio would."""

    instances = []

    def __init__(self, on_samples, rate=16000.0, fail_prepare=False, fail_start=0, stop_blocks=None):
        self.on_samples, self.rate = on_samples, rate
        self.fail_prepare, self.fail_start, self.stop_blocks = fail_prepare, fail_start, stop_blocks
        self.calls = []
        FakeEngine.instances.append(self)

    def prepare(self):
        self.calls.append("prepare")
        if self.fail_prepare:
            raise RuntimeError("no input device")

    def start(self):
        self.calls.append("start")
        if self.fail_start:
            self.fail_start -= 1
            return False
        return True

    def stop(self):
        self.calls.append("stop")
        if self.stop_blocks is not None:
            self.stop_blocks.wait()  # simulate the CoreAudio deadlock

    def feed(self, values):
        self.on_samples(np.asarray(values, np.float32), self.rate)


class IdentityResampler:
    """16 kHz in, 16 kHz out, no delay: makes buffer contents exactly predictable."""

    def __init__(self, in_rate):
        self.in_rate = in_rate
        self.flushed = False

    def resample_chunk(self, x, last=False):
        x = np.asarray(x, np.float32)
        if last:
            self.flushed = True
            return np.concatenate([x, [9.0]]).astype(np.float32)  # input + sentinel "tail" sample
        return x


@pytest.fixture
def engines(monkeypatch):
    FakeEngine.instances = []
    monkeypatch.setattr(audio, "MAX_SECONDS", 2)
    return FakeEngine.instances


def recorder(**engine_kw):
    return Recorder(engine_factory=lambda cb: FakeEngine(cb, **engine_kw), resampler_factory=IdentityResampler)


class TestRecorder:
    def test_prepare_builds_engine_without_starting_mic(self, engines):
        r = recorder()
        r.prepare()
        assert engines[0].calls == ["prepare"] and not r.recording

    def test_prepare_failure_leaves_no_engine(self, engines):
        r = recorder(fail_prepare=True)
        r.prepare()
        assert r._engine is None

    def test_start_reuses_prepared_engine(self, engines):
        r = recorder()
        r.prepare()
        assert r.start() is True and r.recording
        assert len(engines) == 1 and engines[0].calls == ["prepare", "start"]

    def test_start_builds_engine_if_needed(self, engines):
        assert recorder().start() is True and len(engines) == 1

    def test_samples_recorded_only_while_capturing(self, engines):
        r = recorder()
        r.prepare()
        engines[0].feed([0.5] * 10)  # before start: dropped
        r.start()
        engines[0].feed([0.2] * 5)
        r.stop()
        engines[0].feed([0.7] * 10)  # after stop: dropped (gated)
        assert r.audio().tolist() == pytest.approx([0.2] * 5 + [9.0])  # + flushed tail

    def test_stop_flushes_resampler_tail(self, engines):
        r = recorder()
        r.start()
        resampler = r._resampler
        r.stop()
        assert resampler.flushed and r.audio().tolist() == [9.0]

    def test_resampler_built_for_engine_rate(self, monkeypatch):
        rates = []
        r = Recorder(engine_factory=lambda cb: FakeEngine(cb, rate=44100.0),
                     resampler_factory=lambda rate: rates.append(rate) or IdentityResampler(rate))
        r.start()
        assert rates == [44100.0]

    def test_stop_stops_engine_in_background_worker(self, engines, inline_threads):
        r = recorder()
        r.start()
        r.stop()
        assert engines[0].calls[-1] == "stop" and inline_threads[-1] == "mic-stop"

    def test_stop_when_idle_does_not_touch_engine(self, engines):
        r = recorder()
        r.prepare()
        r.stop()
        assert engines[0].calls == ["prepare"]

    def test_stop_never_blocks_even_if_coreaudio_hangs(self, engines, monkeypatch):
        """The regression: a deadlocked engine stop must not freeze the caller (the UI)."""
        import time
        from mhispr import threads
        monkeypatch.setattr(audio, "start_daemon", threads.start_daemon)  # real background thread
        stuck = threading.Event()
        r = Recorder(engine_factory=lambda cb: FakeEngine(cb, stop_blocks=stuck),
                     resampler_factory=IdentityResampler, stop_timeout=0.05)
        r.start()
        t = time.perf_counter()
        r.stop()
        assert time.perf_counter() - t < 0.05 and not r.recording
        stuck.set()

    def test_hung_stop_switches_to_fresh_engine(self, engines, monkeypatch, capsys):
        from mhispr import threads
        monkeypatch.setattr(audio, "start_daemon", threads.start_daemon)
        stuck = threading.Event()
        made = []

        def factory(cb):
            engine = FakeEngine(cb, stop_blocks=stuck if not made else None)
            made.append(engine)
            return engine

        r = Recorder(engine_factory=factory, resampler_factory=IdentityResampler, stop_timeout=0.05)
        r.start()
        r.stop()  # first engine deadlocks in stop
        assert r.start() is True  # waits 50 ms, gives up on it, builds a new one
        assert len(made) == 2 and r._engine is made[1]
        assert "switching to a fresh audio engine" in capsys.readouterr().err
        stuck.set()

    def test_restart_waits_for_previous_stop(self, engines, monkeypatch):
        from mhispr import threads
        monkeypatch.setattr(audio, "start_daemon", threads.start_daemon)
        r = recorder()
        r.start()
        r.stop()
        assert r.start() is True and len(engines) == 1  # same engine reused after a clean stop

    def test_start_while_recording_restarts_cleanly(self, engines):
        r = recorder()
        r.start()
        engines[0].feed([0.4] * 5)
        assert r.start() is True and len(r.audio()) == 0  # previous take stopped and wiped
        assert engines[0].calls == ["prepare", "start", "stop", "start"]  # stopped before restarting

    def test_start_resets_level(self, engines):
        r = recorder()
        r._level = 0.9
        r.start()
        assert r.level() == 0.0

    def test_start_retries_once_with_fresh_engine(self, engines):
        attempts = iter([1, 0])  # first engine fails to start, second works
        r = Recorder(engine_factory=lambda cb: FakeEngine(cb, fail_start=next(attempts)),
                     resampler_factory=IdentityResampler)
        assert r.start() is True and len(engines) == 2

    def test_start_tries_exactly_twice(self, engines):
        attempts = iter([1, 1, 0])  # a third attempt would succeed, but there must not be one
        r = Recorder(engine_factory=lambda cb: FakeEngine(cb, fail_start=next(attempts)),
                     resampler_factory=IdentityResampler)
        assert r.start() is False and len(engines) == 2 and not r.recording

    def test_start_gives_up_after_two_failures(self, engines, capsys):
        r = recorder(fail_prepare=True)
        assert r.start() is False and r._engine is None
        assert "could not open microphone" in capsys.readouterr().err

    def test_successful_retry_reports_no_error(self, engines, capsys):
        attempts = iter([1, 0])
        r = Recorder(engine_factory=lambda cb: FakeEngine(cb, fail_start=next(attempts)),
                     resampler_factory=IdentityResampler)
        r.start()
        assert capsys.readouterr().err == ""

    def test_stop_turns_mic_off_but_keeps_audio(self, engines):
        r = recorder()
        r.start()
        engines[0].feed([0.4] * 50)
        r.stop()
        assert not r.recording and len(r.audio()) == 51 and r.level() == 0.0

    def test_wipe_returns_stats_and_zeroes(self, engines):
        r = recorder()
        r.start()
        engines[0].feed([0.1, -0.8, 0.3] * 16000)
        secs, peak, verified = r.wipe()
        assert secs == pytest.approx(3.0) and peak == pytest.approx(0.8) and verified is True
        assert len(r.audio()) == 0 and not r.buffer.data.any()

    def test_wipe_empty(self, engines):
        assert recorder().wipe() == (0.0, 0.0, True)

    def test_audio_is_view_of_buffer(self, engines):
        r = recorder()
        r.start()
        engines[0].feed([0.2] * 10)
        assert np.shares_memory(r.audio(), r.buffer.data)

    def test_recording_false_initially(self, engines):
        r = recorder()
        assert r.recording is False and r.level() == 0.0

    def test_level_ignores_t_argument(self, engines):
        r = recorder()
        r._level = 0.42
        assert r.level() == r.level(123.0) == 0.42


class TestLevel:
    @pytest.fixture
    def live(self, engines):
        r = recorder()
        r.start()
        return r, engines[0]

    # Level mapping: dBFS of each block -> 0..1 target (-55 dB floor, -12 dB ceiling); the first
    # block moves the level 60% of the way (attack), so level = 0.6 * target.
    @pytest.mark.parametrize("dbfs,target", [(-60, 0.0), (-55, 0.0), (-33.5, 0.5), (-12, 1.0), (-3, 1.0)])
    def test_dbfs_to_level_mapping(self, live, dbfs, target):
        r, engine = live
        engine.feed([10 ** (dbfs / 20)] * 512)
        assert r.level() == pytest.approx(0.6 * target, abs=1e-6)

    def test_mapping_constants(self):
        assert (audio.FLOOR_DB, audio.CEIL_DB) == (-55.0, -12.0)

    def test_silence_keeps_level_zero(self, live):
        r, engine = live
        engine.feed([0.0] * 512)
        assert r.level() == 0.0

    def test_level_saturates_at_one(self, live):
        r, engine = live
        for _ in range(20):
            engine.feed([1.0] * 512)
        assert r.level() == pytest.approx(1.0) and r.level() <= 1.0

    def test_level_decays_slower_than_it_rises(self, live):
        r, engine = live
        for _ in range(20):
            engine.feed([1.0] * 512)
        engine.feed([0.0] * 512)
        assert r.level() == pytest.approx(0.8)  # 20% release

    def test_empty_chunk_leaves_level(self, live):
        r, engine = live
        r._level = 0.5
        engine.feed([])
        assert r.level() == 0.5

    def test_level_not_updated_after_stop(self, live):
        r, engine = live
        r.stop()
        engine.feed([1.0] * 512)
        assert r.level() == 0.0


class TestResampling:
    def test_real_resampler_converts_44k1_to_16k(self):
        stream = audio._soxr_stream(44100)
        t = np.arange(44100 * 2) / 44100
        tone = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        out = np.concatenate([stream.resample_chunk(tone[i:i + 1024]) for i in range(0, len(tone), 1024)]
                             + [stream.resample_chunk(np.zeros(0, np.float32), last=True)])
        assert out.dtype == np.float32 and abs(len(out) - 32000) <= 2
        spectrum = np.abs(np.fft.rfft(out[1600:-1600]))
        peak_hz = np.argmax(spectrum) * 16000 / len(out[1600:-1600])
        assert abs(peak_hz - 440) < 2  # pitch preserved

    def test_tap_size_and_stop_timeout(self):
        assert audio.TAP_FRAMES == 1024 and audio.STOP_TIMEOUT == 1.0


class FakeFormat:
    def sampleRate(self):
        return 44100.0


class FakeBuffer:
    """An AVAudioPCMBuffer stand-in: channel data as PyObjC exposes it (varlists with as_buffer)."""

    def __init__(self, channels):
        self.channels = [np.asarray(c, np.float32) for c in channels]

    def frameLength(self):
        return len(self.channels[0])

    def floatChannelData(self):
        class Channel:
            def __init__(self, data):
                self.data = data

            def as_buffer(self, n):
                return memoryview(self.data[:n].tobytes())

        return [Channel(c) for c in self.channels]


class FakeAVAudioEngine:
    """Records the AVAudioEngine calls MicEngine makes."""

    made = []

    @classmethod
    def alloc(cls):
        return cls()

    def init(self):
        self.calls, self.tap = [], None
        FakeAVAudioEngine.made.append(self)
        engine = self

        class Node:
            def outputFormatForBus_(self, bus):
                engine.calls.append(("format", bus))
                return FakeFormat()

            def installTapOnBus_bufferSize_format_block_(self, bus, size, fmt, block):
                engine.calls.append(("tap", bus, size))
                engine.tap = block

        self.node = Node()
        return self

    def inputNode(self):
        return self.node

    def prepare(self):
        self.calls.append("prepare")

    def startAndReturnError_(self, err):
        self.calls.append("start")
        return (self.start_ok, None)

    start_ok = True

    def stop(self):
        self.calls.append("stop")


class TestMicEngine:
    @pytest.fixture
    def mic(self):
        FakeAVAudioEngine.made = []
        got = []
        engine = audio.MicEngine(lambda samples, rate: got.append((samples.copy(), rate)), engine_cls=FakeAVAudioEngine)
        engine.prepare()
        return engine, FakeAVAudioEngine.made[0], got

    def test_prepare_taps_input_bus_zero_at_native_format(self, mic):
        engine, av, _ = mic
        assert av.calls == [("format", 0), ("tap", 0, audio.TAP_FRAMES), "prepare"]
        assert engine.rate == 44100.0

    def test_tap_delivers_channel_zero_at_engine_rate(self, mic):
        engine, av, got = mic
        av.tap(FakeBuffer([[0.1, 0.2, 0.3], [9.0, 9.0, 9.0]]), None)
        (samples, rate), = got
        assert samples.tolist() == pytest.approx([0.1, 0.2, 0.3]) and rate == 44100.0

    def test_tap_uses_frame_length_not_capacity(self, mic):
        engine, av, got = mic
        buf = FakeBuffer([[0.5, 0.5, 0.7, 0.7]])
        buf.frameLength = lambda: 2
        av.tap(buf, None)
        assert got[0][0].tolist() == [0.5, 0.5]

    def test_empty_tap_buffer_is_ignored(self, mic):
        engine, av, got = mic
        av.tap(FakeBuffer([[]]), None)
        assert got == []

    @pytest.mark.parametrize("ok", [True, False])
    def test_start_reports_success(self, mic, ok):
        engine, av, _ = mic
        av.start_ok = ok
        assert engine.start() is ok and av.calls[-1] == "start"

    def test_stop(self, mic):
        engine, av, _ = mic
        engine.stop()
        assert av.calls[-1] == "stop"

    def test_default_engine_is_avaudioengine(self):
        from AVFoundation import AVAudioEngine
        e = audio.MicEngine(lambda s, r: None)
        e.prepare()  # real engine, tap installed, mic NOT started
        assert isinstance(e._engine, AVAudioEngine) and e.rate > 0
