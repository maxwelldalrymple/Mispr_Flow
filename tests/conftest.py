"""Shared fixtures. Unit tests never touch the real mic, clipboard, keyboard, models,
recordings folder, or settings file: those are all faked or redirected to tmp_path."""

import json
import os
import time as _real_time
from pathlib import Path

import numpy as np
import pytest
from AppKit import NSBitmapImageRep, NSGraphicsContext, NSMakeRect, NSPNGFileType
from PyObjCTools import AppHelper

import mispr.models as models
import mispr.settings as settings
import mispr.storage as storage


def pytest_sessionfinish(session, exitstatus):
    """llama-cpp-python opens /dev/null twice at import and never closes it (third-party
    leak, reported as ResourceWarning at interpreter exit); close it so runs stay clean."""
    import sys
    utils = sys.modules.get("llama_cpp._utils")
    for name in ("outnull_file", "errnull_file"):
        f = getattr(utils, name, None)
        if f is not None and not f.closed:
            f.close()


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: needs the real models (set MISPR_INTEGRATION=1)")


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path, monkeypatch):
    """Redirect every on-disk location the app writes to into this test's tmp dir."""
    monkeypatch.setattr(settings, "SETTINGS_PATH", tmp_path / "support" / "settings.json")
    from mispr import storage as _storage
    monkeypatch.setattr(_storage, "LOG_DIR", tmp_path / "logs")  # lock_down() never touches the real log folder
    monkeypatch.setattr(storage, "RECORDINGS_DIR", tmp_path / "voice-recordings")
    monkeypatch.setattr(models, "MODELS_DIR", tmp_path / "models")
    return tmp_path


@pytest.fixture(autouse=True)
def inline_threads(monkeypatch):
    """Run background work synchronously (deterministic tests, no sleeps or polling).
    Records (name, target) for every daemon start; `threads.start_daemon` itself is
    tested separately with real threads."""
    import mispr.audio
    import mispr.cleanup
    import mispr.setup
    import mispr.transcribe

    started = []

    def start_daemon(target, name):
        started.append(name)
        target()

    for module in (mispr.audio, mispr.cleanup, mispr.transcribe, mispr.setup):
        monkeypatch.setattr(module, "start_daemon", start_daemon)
    return started


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
        self.configured = []

    def configure(self, system, examples, guard):
        self.configured.append((system, examples, guard))

    def load_async(self):
        self.loaded += 1

    def clean(self, raw):
        return raw, {"model": "fake", "applied": False, "ms": 0, "rejected": None}

    def close(self):
        self.closed += 1


class SpySounds:
    """Records every sound cue instead of playing it."""

    def __init__(self):
        self.played = []
        self.enabled = True

    def play(self, name):
        self.played.append(name)


@pytest.fixture
def speech():
    """One second of a loud-enough sine wave (passes the length and silence gates)."""
    t = np.arange(16000, dtype=np.float32) / 16000
    return (0.3 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)


@pytest.fixture
def controller(monkeypatch, clock):
    """A WidgetController wired to fakes: no mic, models, sounds, clipboard, or real apps."""
    import mispr.widget as W

    monkeypatch.setattr(W, "time", clock)
    monkeypatch.setattr(W, "Recorder", FakeRecorder)
    monkeypatch.setattr(W, "Transcriber", FakeTranscriber)
    monkeypatch.setattr(W, "Cleaner", FakeCleaner)
    pasted, copied = [], []
    monkeypatch.setattr(W, "paste_text", pasted.append)
    monkeypatch.setattr(W, "copy_text", copied.append)
    typed = []
    monkeypatch.setattr(W, "type_text", typed.append)
    monkeypatch.setattr(W.context, "focused_text_target", lambda: (W.context.YES, "TestApp"))
    monkeypatch.setattr(W.context, "frontmost", lambda include_page=True: {
        "app": "TestApp", "bundle_id": "com.test.app",
        "url": "https://example.com/page" if include_page else None,
        "page_title": "Example" if include_page else None,
    })
    monkeypatch.setattr(W.sounds, "Sounds", SpySounds)
    monkeypatch.setattr(W.audio, "input_device", lambda: ("MacBook Pro Microphone", True))
    c = W.WidgetController()
    c.pasted, c.copied, c.typed = pasted, copied, typed
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


# --- Golden files (approval testing) ---------------------------------------------------
# Snapshots of outputs that are easier to review than to assert field-by-field (layout
# geometry, rendered pixels). A mismatch fails; after an intentional change, regenerate with
#     UPDATE_GOLDEN=1 .venv/bin/python -m pytest
# and review the diff of tests/golden/ like any other code change.

GOLDEN_DIR = Path(__file__).parent / "golden"
UPDATE_GOLDEN = os.environ.get("UPDATE_GOLDEN") == "1"


@pytest.fixture
def golden_json():
    def check(name, data):
        path = GOLDEN_DIR / f"{name}.json"
        text = json.dumps(data, indent=2, sort_keys=True) + "\n"
        if UPDATE_GOLDEN or not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
            if not UPDATE_GOLDEN:
                pytest.fail(f"created missing golden file {path.name}; review it and re-run")
        assert json.loads(text) == json.loads(path.read_text()), f"{name} differs from golden file"

    return check


def render(draw_fn, width, height):
    """Render `draw_fn()` into an offscreen RGBA bitmap; returns (rgba uint8 array, rep)."""
    rep = NSBitmapImageRep.alloc().initWithBitmapDataPlanes_pixelsWide_pixelsHigh_bitsPerSample_samplesPerPixel_hasAlpha_isPlanar_colorSpaceName_bytesPerRow_bitsPerPixel_(
        None, width, height, 8, 4, True, False, "NSDeviceRGBColorSpace", width * 4, 32
    )
    ctx = NSGraphicsContext.graphicsContextWithBitmapImageRep_(rep)
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.setCurrentContext_(ctx)
    try:
        draw_fn()
        ctx.flushGraphics()
    finally:
        NSGraphicsContext.restoreGraphicsState()
    data = np.frombuffer(rep.bitmapData(), dtype=np.uint8, count=width * height * 4).reshape(height, width, 4).copy()
    return data, rep


def _decode(rep):
    """Pixels of a bitmap as they'd be read back from its PNG. Both sides of a golden
    comparison go through this same path, so colour-space and alpha conversions can't
    make identical renderings look different."""
    w, h = rep.pixelsWide(), rep.pixelsHigh()
    out, _ = render(lambda: rep.drawInRect_(NSMakeRect(0, 0, w, h)), w, h)
    return out


def _read_png(path):
    return _decode(NSBitmapImageRep.imageRepWithContentsOfFile_(str(path)))


def _png_roundtrip(rep):
    data = rep.representationUsingType_properties_(NSPNGFileType, {})
    return _decode(NSBitmapImageRep.imageRepWithData_(data))


@pytest.fixture
def golden_image():
    """Compare a rendering to tests/golden/<name>.png. Tolerates anti-aliasing noise:
    at most 0.5% of pixels may differ, each by at most 48/255 in any channel."""

    def check(name, pixels, rep):
        path = GOLDEN_DIR / f"{name}.png"
        if UPDATE_GOLDEN or not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            rep.representationUsingType_properties_(NSPNGFileType, {}).writeToFile_atomically_(str(path), True)
            if not UPDATE_GOLDEN:
                pytest.fail(f"created missing golden image {path.name}; review it and re-run")
        expected = _read_png(path)
        actual = _png_roundtrip(rep)  # compare like with like (see _decode)
        assert expected.shape == actual.shape, f"{name}: size changed"
        diff = np.abs(expected.astype(int) - actual.astype(int)).max(axis=2)
        bad = (diff > 48).mean()
        assert bad <= 0.005, f"{name}: {bad:.2%} of pixels differ from the golden image"

    return check


# --- Fakes for the macOS UI objects the widget talks to -------------------------------------

class FakePanel:
    def __init__(self, origin=(0.0, 0.0)):
        self.origin = origin
        self.ignores_mouse = []  # history of setIgnoresMouseEvents_ values
        self.frames = []

    def frame(self):
        return NSMakeRect(self.origin[0], self.origin[1], 480, 220)

    def setIgnoresMouseEvents_(self, value):
        self.ignores_mouse.append(value)

    def setFrame_display_(self, rect, display):
        assert display is True, "panel must redisplay when moved"
        self.frames.append((rect.origin.x, rect.origin.y, rect.size.width, rect.size.height))
        self.origin = (rect.origin.x, rect.origin.y)


class FakeView:
    def __init__(self):
        self.redraws = []

    def setNeedsDisplay_(self, flag):
        self.redraws.append(flag)


class FakeScreen:
    def __init__(self, x=0.0, y=90.0, w=1512.0, h=860.0):
        self._vf = NSMakeRect(x, y, w, h)

    def visibleFrame(self):
        return self._vf


def make_pointer():
    """A fresh stand-in for NSEvent per test: `mouseLocation()` returns wherever the test put
    the pointer. (A shared class attribute leaked the position between tests.)"""
    from AppKit import NSMakePoint

    class Pointer:
        location = (-1000.0, -1000.0)  # off the widget until a test places it

        @classmethod
        def mouseLocation(cls):
            return NSMakePoint(*cls.location)

    return Pointer


@pytest.fixture
def ui(controller, monkeypatch):
    """Attach fake panel/view/screen/pointer to the controller (the UI 'humble objects')."""
    import mispr.widget as W

    screen = {"screen": FakeScreen(), "fullscreen": False}
    monkeypatch.setattr(W, "active_screen", lambda: (screen["screen"], screen["fullscreen"]))
    Pointer = make_pointer()
    monkeypatch.setattr(W, "NSEvent", Pointer)
    controller.panel, controller.view = FakePanel(), FakeView()
    # Arrange: settle the panel where the screen puts it, so the first tick doesn't move it
    # out from under a pointer the test has already placed.
    controller._poll_screen(force=True)
    controller.next_screen_poll = 0.0
    controller.panel.frames.clear()

    class UI:
        panel, view = controller.panel, controller.view

        @staticmethod
        def point_at(x, y):
            """Place the pointer at widget-local coordinates."""
            ox, oy = controller.panel.origin
            Pointer.location = (ox + x, oy + y)

        @staticmethod
        def set_screen(scr, fullscreen=False):
            screen["screen"], screen["fullscreen"] = scr, fullscreen

    return UI
