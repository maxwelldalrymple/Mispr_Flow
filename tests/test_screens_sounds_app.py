import signal
from pathlib import Path

import numpy as np

import pytest
from AppKit import NSMakeRect

from mispr import app, screens, sounds


# --- screens -----------------------------------------------------------------------

class FakeScreen:
    def __init__(self, x, y, w, h, name):
        self._f, self.name = NSMakeRect(x, y, w, h), name

    def frame(self):
        return self._f


PRIMARY = FakeScreen(0, 0, 1512, 982, "primary")
SECOND = FakeScreen(1512, 0, 1920, 1080, "second")  # to the right, bottoms aligned


class FakeApp:
    def processIdentifier(self):
        return 7


@pytest.fixture
def desktop(monkeypatch):
    state = {"windows": [], "app": FakeApp(), "mouse": (100, 100)}

    # Python stand-ins for the AppKit classes (ObjC class methods can't be monkeypatched).
    class Workspace:
        @staticmethod
        def sharedWorkspace():
            return Workspace()

        def frontmostApplication(self):
            return state["app"]

    class Screen:
        screens = staticmethod(lambda: [PRIMARY, SECOND])
        mainScreen = staticmethod(lambda: PRIMARY)

    class Event:
        mouseLocation = staticmethod(lambda: state["mouse"])

    monkeypatch.setattr(screens, "NSWorkspace", Workspace)
    monkeypatch.setattr(screens, "NSScreen", Screen)
    monkeypatch.setattr(screens, "NSEvent", Event)
    def window_list(opts, wid):
        state["query"] = (opts, wid)
        return state["windows"]

    monkeypatch.setattr(screens.Quartz, "CGWindowListCopyWindowInfo", window_list)
    return state


def window(pid=7, layer=0, x=100, y=100, w=800, h=600):
    return {"kCGWindowOwnerPID": pid, "kCGWindowLayer": layer,
            "kCGWindowBounds": {"X": x, "Y": y, "Width": w, "Height": h}}


class TestFrontmostWindowBounds:
    def test_no_app(self, desktop):
        desktop["app"] = None
        assert screens._frontmost_window_bounds() is None

    def test_first_matching_window(self, desktop):
        desktop["windows"] = [window(pid=1), window(x=5), window(x=9)]
        assert screens._frontmost_window_bounds()["X"] == 5

    def test_skips_non_normal_layers(self, desktop):
        desktop["windows"] = [window(layer=25, x=1), window(layer=0, x=2)]
        assert screens._frontmost_window_bounds()["X"] == 2

    def test_queries_only_onscreen_app_windows(self, desktop):
        desktop["windows"] = [window()]
        screens._frontmost_window_bounds()
        import Quartz
        assert desktop["query"] == (Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
                                    Quartz.kCGNullWindowID)

    @pytest.mark.parametrize("w,h,counted", [(50, 50, True), (49, 500, False), (500, 49, False), (51, 51, True)])
    def test_min_window_size_boundary(self, desktop, w, h, counted):
        desktop["windows"] = [window(w=w, h=h)]
        assert (screens._frontmost_window_bounds() is not None) is counted

    def test_skips_tiny_windows(self, desktop):
        desktop["windows"] = [window(w=10, h=10, x=1), window(x=2)]
        assert screens._frontmost_window_bounds()["X"] == 2

    def test_none_when_app_has_no_windows(self, desktop):
        desktop["windows"] = [window(pid=99)]
        assert screens._frontmost_window_bounds() is None


class TestActiveScreen:
    def test_window_on_primary(self, desktop):
        desktop["windows"] = [window()]
        assert screens.active_screen() == (PRIMARY, False)

    def test_window_on_second_screen(self, desktop):
        desktop["windows"] = [window(x=1600, y=200)]
        s, fs = screens.active_screen()
        assert s is SECOND and fs is False

    def test_fullscreen_detected(self, desktop):
        desktop["windows"] = [window(x=0, y=0, w=1512, h=982)]
        assert screens.active_screen() == (PRIMARY, True)

    def test_fullscreen_on_second_screen(self, desktop):
        # CG y is measured down from the primary's top; the second screen is taller (1080).
        desktop["windows"] = [window(x=1512, y=982 - 1080, w=1920, h=1080)]
        assert screens.active_screen() == (SECOND, True)

    def test_maximized_but_not_fullscreen(self, desktop):
        desktop["windows"] = [window(x=0, y=33, w=1512, h=949)]  # below the menu bar
        assert screens.active_screen() == (PRIMARY, False)

    def test_straddling_window_belongs_to_screen_holding_its_center(self, desktop):
        # x 1100..2000: centre 1550 is past the primary's right edge (1512) -> second screen.
        desktop["windows"] = [window(x=1100, w=900)]
        assert screens.active_screen()[0] is SECOND
        desktop["windows"] = [window(x=700, w=900)]  # centre 1150 -> primary
        assert screens.active_screen()[0] is PRIMARY

    def test_vertical_center_uses_flipped_coordinates(self, desktop, monkeypatch):
        above = FakeScreen(0, 982, 1512, 982, "above")  # stacked on top of the primary
        monkeypatch.setattr(screens, "NSScreen", type("S", (), {
            "screens": staticmethod(lambda: [PRIMARY, above]), "mainScreen": staticmethod(lambda: PRIMARY)}))
        # CG y grows downward from the primary's top; a window at CG y -700..-100 has its
        # centre at CG -400 = AppKit 1382, which is on the upper screen.
        desktop["windows"] = [window(x=100, y=-700, h=600)]
        assert screens.active_screen()[0] is above
        desktop["windows"] = [window(x=100, y=-200, h=600)]  # centre CG 100 = AppKit 882 -> primary
        assert screens.active_screen()[0] is PRIMARY

    @pytest.mark.parametrize("dx,dy,dw,dh", [(1, 0, 0, 0), (0, 1, 0, 0), (0, 0, -1, 0), (0, 0, 0, -1)])
    def test_fullscreen_tolerance_is_under_one_point(self, desktop, dx, dy, dw, dh):
        desktop["windows"] = [window(x=dx, y=dy, w=1512 + dw, h=982 + dh)]
        assert screens.active_screen() == (PRIMARY, False)

    @pytest.mark.parametrize("dx,dy,dw,dh", [(0.5, 0, 0, 0), (0, 0.5, 0, 0), (0, 0, -0.5, 0), (0, 0, 0, -0.5)])
    def test_fullscreen_tolerates_subpixel_differences(self, desktop, dx, dy, dw, dh):
        desktop["windows"] = [window(x=dx, y=dy, w=1512 + dw, h=982 + dh)]
        assert screens.active_screen() == (PRIMARY, True)

    def test_falls_back_to_mouse_screen(self, desktop):
        desktop["mouse"] = (2000, 500)
        assert screens.active_screen() == (SECOND, False)

    def test_falls_back_to_main_screen(self, desktop):
        desktop["mouse"] = (-5000, -5000)
        assert screens.active_screen() == (PRIMARY, False)


# --- sounds --------------------------------------------------------------------------

class FakeSound:
    played = []
    loads = []

    def __init__(self, name):
        self.name, self.volume, self.playing = name, None, False

    def copy(self):
        return FakeSound(self.name)

    def setVolume_(self, v):
        self.volume = v

    def play(self):
        self.playing = True
        FakeSound.played.append(self)

    def isPlaying(self):
        return self.playing


@pytest.fixture
def fake_nssound(monkeypatch):
    FakeSound.played, FakeSound.loads = [], []

    class Sound:
        @staticmethod
        def alloc():
            return Sound()

        def initWithContentsOfFile_byReference_(self, path, by_ref):
            FakeSound.loads.append(path)
            return FakeSound(Path(path).stem)

    monkeypatch.setattr(sounds, "NSSound", Sound)
    return FakeSound


class TestSounds:
    def test_plays_named_sound_at_volume(self, fake_nssound):
        s = sounds.Sounds(volume=0.4)
        s.play(sounds.START)
        assert [(p.name, p.volume) for p in fake_nssound.played] == [("start", 0.4)]

    def test_disabled_plays_nothing(self, fake_nssound):
        sounds.Sounds(enabled=False).play(sounds.START)
        assert fake_nssound.played == []

    def test_unknown_sound_ignored(self, fake_nssound):
        s = sounds.Sounds()
        s.play("NoSuchSound")
        assert fake_nssound.played == [] and s._playing == []

    def test_overlapping_cues_are_separate_copies(self, fake_nssound):
        s = sounds.Sounds()
        s.play(sounds.START)
        s.play(sounds.START)
        assert len(fake_nssound.played) == 2 and fake_nssound.played[0] is not fake_nssound.played[1]

    def test_finished_sounds_released(self, fake_nssound):
        s = sounds.Sounds()
        s.play(sounds.START)
        fake_nssound.played[0].playing = False
        s.play(sounds.STOP)
        assert [p.name for p in s._playing] == ["stop"]

    def test_default_volume_is_full_because_levels_are_in_the_files(self, fake_nssound):
        sounds.Sounds().play(sounds.START)
        assert fake_nssound.played[0].volume == 1.0

    def test_each_file_is_loaded_once(self, fake_nssound):
        s = sounds.Sounds()
        for _ in range(3):
            s.play(sounds.START)
        assert len(fake_nssound.loads) == 1 and len(fake_nssound.played) == 3

    def test_missing_file_is_ignored(self, fake_nssound, monkeypatch, tmp_path):
        monkeypatch.setattr(sounds, "SOUNDS", tmp_path)
        sounds.Sounds().play(sounds.START)
        assert fake_nssound.played == [] and fake_nssound.loads == []


class TestSoundFiles:
    """The shipped cues: every one exists, is a short mono 48 kHz WAV, and isn't clipped."""

    @pytest.mark.parametrize("name", sounds.ALL)
    def test_file_shape(self, name):
        import wave
        with wave.open(str(sounds.SOUNDS / f"{name}.wav")) as w:
            assert (w.getnchannels(), w.getsampwidth(), w.getframerate()) == (1, 2, 48000)
            assert 0.05 < w.getnframes() / 48000 < 1.2
            pcm = np.frombuffer(w.readframes(w.getnframes()), "<i2")
        assert np.abs(pcm).max() < 32767

    def test_dictation_cues_are_quiet_and_short(self):
        import wave
        for name in (sounds.START, sounds.STOP, sounds.LOCK, sounds.CANCEL):
            with wave.open(str(sounds.SOUNDS / f"{name}.wav")) as w:
                pcm = np.frombuffer(w.readframes(w.getnframes()), "<i2") / 32768
                assert w.getnframes() / 48000 < 0.2
            assert 20 * np.log10(np.abs(pcm).max()) < -15  # sits under speech, never startles

    def test_generator_reproduces_the_shipped_files(self, tmp_path, monkeypatch):
        import importlib.util
        spec = importlib.util.spec_from_file_location("make_sounds", Path(sounds.__file__).parent.parent / "tools" / "make_sounds.py")
        mk = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mk)
        monkeypatch.setattr(mk, "OUT", tmp_path)
        mk.main()
        for name in sounds.ALL:
            assert (tmp_path / f"{name}.wav").read_bytes() == (sounds.SOUNDS / f"{name}.wav").read_bytes(), name


# --- app -----------------------------------------------------------------------------

class TestSingleInstance:
    """The lock path is injected, so tests never touch the real lock or patch tempfile."""

    @pytest.fixture
    def lock_path(self, tmp_path):
        return tmp_path / "Mispr_Flow.lock"

    @pytest.fixture
    def other_instance(self, lock_path):
        """Simulates another running copy holding the lock; released at teardown."""
        lock = app._single_instance_lock(lock_path)
        yield lock
        lock.close()

    def test_default_path_is_in_temp_dir(self):
        assert app.LOCK_PATH.name == "Mispr_Flow.lock"
        assert app.LOCK_PATH.parent == app.Path(app.tempfile.gettempdir())

    def test_first_instance_gets_lock(self, lock_path):
        lock = app._single_instance_lock(lock_path)
        try:
            assert not lock.closed and lock_path.exists()
        finally:
            lock.close()

    def test_second_instance_exits_with_code_1(self, lock_path, other_instance, capsys):
        with pytest.raises(SystemExit) as exit_info:
            app._single_instance_lock(lock_path)
        assert exit_info.value.code == 1
        assert "already running" in capsys.readouterr().err

    def test_second_instance_releases_its_file(self, lock_path, other_instance):
        import gc
        import warnings

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            with pytest.raises(SystemExit):
                app._single_instance_lock(lock_path)
            gc.collect()  # a leaked file object would emit ResourceWarning here
        assert not [w for w in caught if issubclass(w.category, ResourceWarning)]

    def test_lock_is_released_when_closed(self, lock_path):
        app._single_instance_lock(lock_path).close()
        second = app._single_instance_lock(lock_path)  # no SystemExit
        second.close()

    def test_locks_are_independent_per_path(self, tmp_path):
        a = app._single_instance_lock(tmp_path / "a.lock")
        b = app._single_instance_lock(tmp_path / "b.lock")
        a.close()
        b.close()


class TestShutdown:
    @pytest.fixture
    def wiring(self, monkeypatch):
        from conftest import FakeCleaner, FakeRecorder

        handlers, observers, removed, stopped = {}, [], [], []
        monkeypatch.setattr(app.signal, "signal", lambda sig, fn: handlers.__setitem__(sig, fn))

        class Center:
            def addObserverForName_object_queue_usingBlock_(self, name, obj, queue, block):
                observers.append((name, block))

        class Bar:
            def removeStatusItem_(self, item):
                removed.append(item)

        monkeypatch.setattr(app, "NSNotificationCenter", type("NC", (), {"defaultCenter": staticmethod(Center)}))
        monkeypatch.setattr(app, "NSStatusBar", type("SB", (), {"systemStatusBar": staticmethod(Bar)}))
        monkeypatch.setattr(app.AppHelper, "stopEventLoop", lambda: stopped.append(True))

        class Widget:
            recorder, cleaner = FakeRecorder(), FakeCleaner()

        w = Widget()
        app._install_shutdown("ITEM", w)
        return dict(handlers=handlers, observers=observers, removed=removed, stopped=stopped, widget=w)

    def test_handles_term_int_hup(self, wiring):
        assert set(wiring["handlers"]) == {signal.SIGTERM, signal.SIGINT, signal.SIGHUP}

    def test_signal_releases_everything(self, wiring):
        wiring["handlers"][signal.SIGTERM](signal.SIGTERM, None)
        w = wiring["widget"]
        assert w.recorder.stopped == 1 and w.recorder.buffer.closed and w.cleaner.closed == 1
        assert wiring["removed"] == ["ITEM"] and wiring["stopped"] == [True]

    def test_menu_quit_releases_models_and_audio(self, wiring):
        (name, block), = wiring["observers"]
        assert name == app.NSApplicationWillTerminateNotification
        block(None)
        w = wiring["widget"]
        assert w.recorder.buffer.closed and w.cleaner.closed == 1


class TestBranding:
    def test_app_name(self):
        assert app.APP_NAME == "Mispr Flow" and app.APP_ID == "Mispr_Flow"
        assert app.LOCK_PATH.name == "Mispr_Flow.lock"

    def test_menu_has_quit(self):
        item = app._status_item()
        try:
            quit_item = item.menu().itemAtIndex_(0)
            assert quit_item.title() == "Quit Mispr Flow"
            assert quit_item.action() == "terminate:" and quit_item.keyEquivalent() == "q"
        finally:
            app.NSStatusBar.systemStatusBar().removeStatusItem_(item)

    def test_menubar_icon_is_the_logo_as_template(self):
        icon = app._menubar_icon()
        assert icon.isTemplate()  # macOS tints it for light/dark menu bars
        assert (icon.size().width, icon.size().height) == (18, 18)
        widths = sorted(r.pixelsWide() for r in icon.representations())
        assert widths == [18, 36]  # 1x and Retina
        assert icon.accessibilityDescription() == "Mispr Flow"

    def test_menubar_icon_falls_back_to_symbol(self, monkeypatch, tmp_path):
        monkeypatch.setattr(app, "ASSETS", tmp_path)  # no asset files
        icon = app._menubar_icon()
        assert icon is not None and icon.isTemplate()

    def test_app_icon_has_every_macos_size(self):
        icon = app._app_icon()
        sizes = sorted({r.pixelsWide() for r in icon.representations()})
        assert sizes == [16, 32, 64, 128, 256, 512, 1024]

    def test_icon_source_is_square_1024(self):
        from AppKit import NSImage
        rep = NSImage.alloc().initWithContentsOfFile_(str(app.ASSETS / "icon.png")).representations()[0]
        assert (rep.pixelsWide(), rep.pixelsHigh()) == (1024, 1024)


class TestHotkeyMaintenance:
    class Fn:
        def __init__(self, tap=None, active=False, start_ok=True, upgrade_ok=False):
            self._tap, self.active = tap, active
            self.start_ok, self.upgrade_ok, self.calls = start_ok, upgrade_ok, []

        def start(self):
            self.calls.append("start")
            if self.start_ok:
                self._tap = "TAP"
            return self.start_ok

        def upgrade(self):
            self.calls.append("upgrade")
            return self.upgrade_ok

    def test_starts_tap_once_permission_allows(self):
        fn = self.Fn()
        assert app.maintain_hotkey(fn) == "started" and fn.calls == ["start"]

    def test_keeps_trying_without_permission(self):
        fn = self.Fn(start_ok=False)
        assert app.maintain_hotkey(fn) is None and app.maintain_hotkey(fn) is None
        assert fn.calls == ["start", "start"]

    def test_upgrades_listen_only_tap(self):
        fn = self.Fn(tap="LISTEN", active=False, upgrade_ok=True)
        assert app.maintain_hotkey(fn) == "upgraded" and fn.calls == ["upgrade"]

    def test_listen_only_waits_for_accessibility(self):
        fn = self.Fn(tap="LISTEN", active=False, upgrade_ok=False)
        assert app.maintain_hotkey(fn) is None

    def test_active_tap_is_left_alone(self):
        fn = self.Fn(tap="TAP", active=True)
        assert app.maintain_hotkey(fn) is None and fn.calls == []


class TestSetupWiring:
    def test_setup_guide_is_first_menu_item_and_opens_setup(self):
        item = app._status_item()
        opened = []
        try:
            actions = app.add_setup_menu_item(item, lambda: opened.append(True))
            guide = item.menu().itemAtIndex_(0)
            assert guide.title() == "Setup Guide…" and guide.target() is actions
            assert item.menu().itemAtIndex_(1).title() == "Quit Mispr Flow"
            actions.openSetup_(None)
            assert opened == [True]
        finally:
            app.NSStatusBar.systemStatusBar().removeStatusItem_(item)

    def test_setup_flow_reads_widget_download_state(self, monkeypatch):
        retries = []

        class Widget:
            setup_progress, setup_error = 0.25, "offline"
            settings = app.onboarding.settings_mod.Settings(onboarded=True)

            def _retry_setup(self):
                retries.append(True)

        monkeypatch.setattr(app.setup, "missing", lambda: ["model"])
        flow = app._setup_flow(Widget())
        assert flow.model_status() == ("error", 0.25, "Download failed: offline")
        assert not flow.models_ready() and flow.settings.onboarded is True
        flow.retry_models()
        assert retries == [True]
        assert [p.key for p in flow.permissions] == ["microphone", "accessibility", "screen_audio"]
