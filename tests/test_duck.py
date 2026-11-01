"""Pause while you talk (mispr/duck.py). AppleScript is replaced by a recorder: nothing on this
Mac is paused or played by these tests."""

from mispr import duck
from mispr.duck import Ducker


def make(playing=("Music",), tabs=1, running=("com.apple.Music", "com.google.Chrome")):
    ran = []
    def run(script):
        ran.append(script)
        if "player state" in script:
            return "playing" if any(f'"{a}"' in script for a in playing) else "paused"
        if duck._PAUSE_PAGE.replace('"', '\\"') in script.replace("\\\\", "\\"):
            return str(tabs)
        return "0"
    return Ducker(run=run, running=lambda: set(running), worker=False), ran


def test_pauses_what_plays_and_resumes_only_that():
    d, ran = make(playing=("Music",), tabs=2)
    d.duck()
    assert 'tell application "Music" to pause' in ran and d.paused == {"players": ["Music"], "browsers": ["Google Chrome"]}
    d.restore()
    assert 'tell application "Music" to play' in ran and any("data-mispr-paused" in r and "play()" in r for r in ran)
    assert d.paused is None


def test_nothing_playing_starts_nothing():
    d, ran = make(playing=(), tabs=0)
    d.duck()
    d.restore()
    assert not any(r.endswith("to play") or r.endswith("to pause") for r in ran)


def test_apps_that_arent_running_are_never_asked():
    d, ran = make(running=())
    d.duck()
    assert ran == []  # asking AppleScript about an app would open it


def test_a_tap_waits_for_a_possible_second_tap(monkeypatch):
    timers = []
    class Timer:
        def __init__(self, delay, fn):
            self.fn, self.cancelled = fn, False
            timers.append(self)
        def start(self):
            pass
        def cancel(self):
            self.cancelled = True
    monkeypatch.setattr(duck.threading, "Timer", Timer)
    d, ran = make()
    d.duck()
    d.restore(later=1.0)  # the first tap of a double-tap
    assert d.paused is not None and len(timers) == 1
    d.duck()  # the second tap: hands-free, stays paused
    assert timers[0].cancelled and d.paused is not None
    assert ran.count('tell application "Music" to pause') == 1  # not paused twice
