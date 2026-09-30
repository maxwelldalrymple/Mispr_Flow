"""Shared fixtures. Unit tests never touch the real mic, clipboard, keyboard, models,
recordings folder, or settings file: those are all faked or redirected to tmp_path."""

import time as _real_time

import numpy as np
import pytest
from AppKit import NSBitmapImageRep, NSGraphicsContext
from PyObjCTools import AppHelper

import whispr.models as models
import whispr.settings as settings
import whispr.storage as storage


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: needs the real models (set WHISPR_INTEGRATION=1)")


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path, monkeypatch):
    """Redirect every on-disk location the app writes to into this test's tmp dir."""
    monkeypatch.setattr(settings, "SETTINGS_PATH", tmp_path / "support" / "settings.json")
    monkeypatch.setattr(storage, "RECORDINGS_DIR", tmp_path / "voice-recordings")
    monkeypatch.setattr(models, "MODELS_DIR", tmp_path / "models")
    return tmp_path


@pytest.fixture(autouse=True)
def immediate_callafter(monkeypatch):
    """Run AppHelper.callAfter / callLater callbacks synchronously (no event loop in tests)."""
    monkeypatch.setattr(AppHelper, "callAfter", lambda fn, *a, **kw: fn(*a, **kw))
    monkeypatch.setattr(AppHelper, "callLater", lambda delay, fn, *a, **kw: fn(*a, **kw))


class FakeClock:
    """Stand-in for the `time` module with a controllable monotonic clock."""

    def __init__(self, start=1000.0):
        self.now = start

    def monotonic(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds

    time = staticmethod(_real_time.time)
    strftime = staticmethod(_real_time.strftime)
    localtime = staticmethod(_real_time.localtime)
    perf_counter = staticmethod(_real_time.perf_counter)
    sleep = staticmethod(_real_time.sleep)


@pytest.fixture
def clock():
    return FakeClock()


class FakeRecorder:
    """Recorder double: no microphone. `audio_data` is what the "mic" captured."""

    def __init__(self, start_ok=True, audio_data=None):
        self.start_ok = start_ok
        self.audio_data = np.zeros(0, dtype=np.float32) if audio_data is None else audio_data
        self.started = self.stopped = self.wiped = self.prepared = 0
        self._level = 0.0

        class _Buf:
            closed = False

            def close(inner):
                inner.closed = True

        self.buffer = _Buf()

    def prepare(self):
        self.prepared += 1

    def start(self):
        self.started += 1
        return self.start_ok

    def stop(self):
        self.stopped += 1

    def audio(self):
        return self.audio_data

    def wipe(self):
        self.wiped += 1
        n = len(self.audio_data)
        self.audio_data = np.zeros(0, dtype=np.float32)
        return n / 16000, 0.5 if n else 0.0, True

    def level(self, t=None):
        return self._level


class FakeTranscriber:
    def __init__(self):
        self.calls = []  # (audio, on_done, post)
        self.loaded = 0

    def load_async(self):
        self.loaded += 1

    def transcribe_async(self, audio, on_done, post=None):
        self.calls.append((audio, on_done, post))


class FakeCleaner:
    def __init__(self):
        self.loaded = self.closed = 0

    def load_async(self):
        self.loaded += 1

    def clean(self, raw):
        return raw, {"model": "fake", "applied": False, "ms": 0, "rejected": None}

    def close(self):
        self.closed += 1


@pytest.fixture
def speech():
    """One second of a loud-enough sine wave (passes the length and silence gates)."""
    t = np.arange(16000, dtype=np.float32) / 16000
    return (0.3 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)


@pytest.fixture
def controller(monkeypatch, clock):
    """A WidgetController wired to fakes: no mic, models, sounds, clipboard, or real apps."""
    import whispr.widget as W

    monkeypatch.setattr(W, "time", clock)
    monkeypatch.setattr(W, "Recorder", FakeRecorder)
    monkeypatch.setattr(W, "Transcriber", FakeTranscriber)
    monkeypatch.setattr(W, "Cleaner", FakeCleaner)
    pasted = []
    monkeypatch.setattr(W, "paste_text", pasted.append)
    monkeypatch.setattr(W.context, "frontmost", lambda include_page=True: {
        "app": "TestApp", "bundle_id": "com.test.app",
        "url": "https://example.com/page" if include_page else None,
        "page_title": "Example" if include_page else None,
    })
    c = W.WidgetController()
    c.sounds.enabled = False
    c.pasted = pasted
    return c


@pytest.fixture
def bitmap_context():
    """A real 200x100 offscreen drawing context; yields a pixel reader (x, y) -> (r, g, b, a)."""
    rep = NSBitmapImageRep.alloc().initWithBitmapDataPlanes_pixelsWide_pixelsHigh_bitsPerSample_samplesPerPixel_hasAlpha_isPlanar_colorSpaceName_bytesPerRow_bitsPerPixel_(
        None, 200, 100, 8, 4, True, False, "NSCalibratedRGBColorSpace", 0, 0
    )
    ctx = NSGraphicsContext.graphicsContextWithBitmapImageRep_(rep)
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.setCurrentContext_(ctx)

    def pixel(x, y):
        ctx.flushGraphics()
        c = rep.colorAtX_y_(int(x), 99 - int(y))  # bitmap rows are top-down; drawing is bottom-up
        return (c.redComponent(), c.greenComponent(), c.blueComponent(), c.alphaComponent())

    yield pixel
    NSGraphicsContext.restoreGraphicsState()
