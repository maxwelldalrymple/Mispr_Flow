"""Microphone capture into a locked, wipeable in-memory buffer.

Privacy rules (see README):
- In Incognito mode audio never touches disk; it lives in one preallocated NumPy buffer.
- The buffer's pages are mlock'ed so they cannot be swapped out.
- After use the written region is zeroed in place (`wipe`), and the buffer is
  never converted to immutable `bytes`, which could not be wiped.
Known limitation: CoreAudio's transient tap buffers and the resampler's small internal
state are owned by those libraries; samples are copied out immediately.

Capture uses AVAudioEngine (Apple's native audio API). It replaced PortAudio, whose macOS
backend can deadlock inside Pa_StopStream (see logs/*_mic-deadlock-fix.md). Stopping is
also non-blocking by design: capture is gated off instantly and the engine is stopped on a
background thread, so a stuck CoreAudio call can never freeze the app.
"""

import ctypes
import ctypes.util
import math
import sys
import threading

import numpy as np
import soxr

from .threads import start_daemon

SAMPLE_RATE = 16_000  # what whisper.cpp expects
MAX_SECONDS = 10 * 60
TAP_FRAMES = 1024  # requested tap size (~23 ms at 44.1 kHz)
STOP_TIMEOUT = 1.0  # a stop slower than this is treated as hung: use a fresh engine

# Map RMS loudness to the 0..1 waveform range.
FLOOR_DB, CEIL_DB = -55.0, -12.0

_libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)


class SecureAudioBuffer:
    def __init__(self, seconds=MAX_SECONDS, rate=SAMPLE_RATE):
        self.data = np.zeros(seconds * rate, dtype=np.float32)
        self.length = 0
        self._ptr = ctypes.c_void_p(self.data.ctypes.data)
        self._nbytes = ctypes.c_size_t(self.data.nbytes)
        self.locked = _libc.mlock(self._ptr, self._nbytes) == 0
        if not self.locked:
            print(f"mispr: mlock failed (errno {ctypes.get_errno()}); audio may be swappable", file=sys.stderr)

    def append(self, samples):
        n = min(len(samples), len(self.data) - self.length)
        self.data[self.length:self.length + n] = samples[:n]
        self.length += n
        return n == len(samples)  # False once the buffer is full

    def view(self):
        """Zero-copy view of the recorded samples. Do not keep it past wipe()."""
        return self.data[:self.length]

    def wipe(self):
        self.data[:self.length].fill(0.0)
        self.length = 0

    def close(self):
        self.data.fill(0.0)
        self.length = 0
        if self.locked:
            _libc.munlock(self._ptr, self._nbytes)
            self.locked = False


class MicEngine:
    """Thin adapter over AVAudioEngine: the only code that touches AVFoundation.

    `on_samples(mono_float32, sample_rate)` is called on CoreAudio's thread with each
    tapped buffer. The array views CoreAudio's memory and is only valid during the call.
    """

    def __init__(self, on_samples, engine_cls=None):
        self._on_samples = on_samples
        self._engine_cls = engine_cls
        self._engine = None
        self.rate = None

    def prepare(self):
        engine_cls = self._engine_cls
        if engine_cls is None:
            from AVFoundation import AVAudioEngine as engine_cls

        engine = engine_cls.alloc().init()
        node = engine.inputNode()
        fmt = node.outputFormatForBus_(0)
        self.rate = fmt.sampleRate()
        node.installTapOnBus_bufferSize_format_block_(0, TAP_FRAMES, fmt, self._tap)
        engine.prepare()
        self._engine = engine

    def _tap(self, buffer, when):
        n = buffer.frameLength()
        if n:
            channel0 = buffer.floatChannelData()[0].as_buffer(n)
            self._on_samples(np.frombuffer(channel0, dtype=np.float32), self.rate)

    def start(self):
        ok, _error = self._engine.startAndReturnError_(None)
        return bool(ok)

    def stop(self):
        self._engine.stop()


def _soxr_stream(in_rate):
    return soxr.ResampleStream(in_rate, SAMPLE_RATE, 1, dtype="float32")


class Recorder:
    """Runs the mic only while recording, so the macOS mic indicator is honest.

    `engine_factory(on_samples)` and `resampler_factory(in_rate)` are injectable seams
    (tests use fakes; the app uses AVAudioEngine and soxr).
    """

    def __init__(self, engine_factory=MicEngine, resampler_factory=_soxr_stream, stop_timeout=STOP_TIMEOUT):
        self.buffer = SecureAudioBuffer()
        self._engine_factory = engine_factory
        self._resampler_factory = resampler_factory
        self._stop_timeout = stop_timeout
        self._engine = None
        self._resampler = None
        self._capturing = False
        self._stopping = None  # Event set once the background engine stop finishes
        self._lock = threading.Lock()
        self._level = 0.0

    @property
    def recording(self):
        return self._capturing

    def prepare(self):
        """Build the (stopped) engine ahead of time so the first recording starts fast."""
        try:
            engine = self._engine_factory(self._on_samples)
            engine.prepare()
            self._engine = engine
        except Exception:
            self._engine = None  # start() will retry and report

    def start(self):
        """Begin a fresh recording. Returns False if the microphone could not be started."""
        self.stop()
        self._await_stop()
        self.wipe()
        self._level = 0.0
        for attempt in range(2):
            try:
                if self._engine is None:
                    engine = self._engine_factory(self._on_samples)
                    engine.prepare()
                    self._engine = engine
                with self._lock:
                    self._resampler = self._resampler_factory(self._engine.rate)
                    self._capturing = True
                if not self._engine.start():
                    raise RuntimeError("microphone did not start")
                return True
            except Exception as e:  # device gone/changed, or microphone permission denied
                with self._lock:
                    self._capturing = False
                    self._resampler = None
                self._engine = None
                if attempt == 1:
                    print(f"mispr: could not open microphone: {e}", file=sys.stderr)
        return False

    def stop(self):
        """Stop capturing now. The audio stays in the buffer until wipe().

        No sample is accepted after this returns. The engine itself is stopped on a
        background thread, so a stuck CoreAudio stop can never block the caller.
        """
        with self._lock:
            was_capturing, self._capturing = self._capturing, False
            if was_capturing and self._resampler is not None:
                self.buffer.append(self._resampler.resample_chunk(np.zeros(0, np.float32), last=True))
            self._resampler = None
        self._level = 0.0
        if was_capturing and self._engine is not None:
            engine, done = self._engine, threading.Event()
            self._stopping = done

            def stop_engine():
                engine.stop()
                done.set()

            start_daemon(stop_engine, "mic-stop")

    def _await_stop(self):
        """Before reusing the engine, wait for its previous stop; abandon it if that hung."""
        done, self._stopping = self._stopping, None
        if done is not None and not done.wait(self._stop_timeout):
            print("mispr: microphone stop hung; switching to a fresh audio engine", file=sys.stderr)
            self._engine = None

    def audio(self):
        return self.buffer.view()

    def wipe(self):
        """Zero the recording. Returns (seconds, peak, verified_zero) for debug logging."""
        with self._lock:
            n = self.buffer.length
            audio = self.buffer.data[:n]
            # max/min reduce in place; np.abs() would make an unwiped copy of the audio.
            peak = max(float(audio.max()), -float(audio.min())) if n else 0.0
            self.buffer.wipe()
            verified = not self.buffer.data[:n].any()
        return n / SAMPLE_RATE, peak, verified

    def level(self, t=None):
        return self._level

    def _on_samples(self, samples, rate):
        """Called on CoreAudio's thread for every tapped buffer."""
        with self._lock:
            if not self._capturing:
                return  # gated off: nothing after stop() is ever recorded
            chunk = self._resampler.resample_chunk(samples)
            self.buffer.append(chunk)
        if not len(chunk):
            return
        rms = float(np.sqrt(np.mean(chunk * chunk)))
        db = 20 * math.log10(rms) if rms > 1e-9 else FLOOR_DB
        target = min(1.0, max(0.0, (db - FLOOR_DB) / (CEIL_DB - FLOOR_DB)))
        # Fast attack, slower release, so the waveform feels responsive but not jittery.
        k = 0.6 if target > self._level else 0.2
        self._level += (target - self._level) * k
