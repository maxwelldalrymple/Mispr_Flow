import signal

import pytest
from AppKit import NSMakeRect

from whispr import app, screens, sounds


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
    monkeypatch.setattr(screens.Quartz, "CGWindowListCopyWindowInfo", lambda opts, wid: state["windows"])
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

    def test_falls_back_to_mouse_screen(self, desktop):
        desktop["mouse"] = (2000, 500)
        assert screens.active_screen() == (SECOND, False)

    def test_falls_back_to_main_screen(self, desktop):
        desktop["mouse"] = (-5000, -5000)
        assert screens.active_screen() == (PRIMARY, False)


# --- sounds --------------------------------------------------------------------------

class FakeSound:
    played = []

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
    FakeSound.played = []
    class Sound:
        soundNamed_ = staticmethod(lambda name: FakeSound(name) if name in ("Tink", "Pop", "Bottle") else None)

    monkeypatch.setattr(sounds, "NSSound", Sound)
    return FakeSound


class TestSounds:
    def test_plays_named_sound_at_volume(self, fake_nssound):
        s = sounds.Sounds(volume=0.4)
        s.play(sounds.START)
        assert [(p.name, p.volume) for p in fake_nssound.played] == [("Tink", 0.4)]

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
        assert [p.name for p in s._playing] == ["Pop"]

    def test_cue_names_are_system_sounds(self):
        assert (sounds.START, sounds.STOP, sounds.CANCEL) == ("Tink", "Pop", "Bottle")


# --- app -----------------------------------------------------------------------------

class TestSingleInstance:
    def test_first_instance_gets_lock(self, monkeypatch, tmp_path):
        monkeypatch.setattr(app.tempfile, "gettempdir", lambda: str(tmp_path))
        lock = app._single_instance_lock()
        assert not lock.closed and (tmp_path / "whispr-clone.lock").exists()
        lock.close()

    def test_second_instance_exits(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr(app.tempfile, "gettempdir", lambda: str(tmp_path))
        first = app._single_instance_lock()
        with pytest.raises(SystemExit) as exit_info:
            app._single_instance_lock()
        assert exit_info.value.code == 1
        assert "already running" in capsys.readouterr().err
        first.close()

    def test_lock_released_when_closed(self, monkeypatch, tmp_path):
        monkeypatch.setattr(app.tempfile, "gettempdir", lambda: str(tmp_path))
        app._single_instance_lock().close()
        app._single_instance_lock().close()  # no SystemExit


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


class TestStatusItem:
    def test_menu_has_quit(self):
        item = app._status_item()
        try:
            menu = item.menu()
            quit_item = menu.itemAtIndex_(0)
            assert quit_item.title() == "Quit Whispr Clone"
            assert quit_item.action() == "terminate:" and quit_item.keyEquivalent() == "q"
            assert item.button().image().isTemplate()  # adapts to light/dark menu bar
        finally:
            app.NSStatusBar.systemStatusBar().removeStatusItem_(item)
