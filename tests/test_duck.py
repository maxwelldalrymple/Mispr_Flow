"""Pause while you talk (mispr/duck.py). AppleScript is replaced by a recorder: nothing on this
Mac is paused or played by these tests."""

from mispr import duck
from mispr.duck import Ducker


def make(playing=("Music",), tabs=1, running=("com.apple.Music", "com.google.Chrome"), missed=0, sounding=()):
    ran = []
    def run(script):
        ran.append(script)
        if "player state" in script:
            return "playing" if any(f'"{a}"' in script for a in playing) else "paused"
        if "mispr-paused','1'" in script:
            return f"{tabs} {missed}"
        return "0 0"
    keys = []
    d = Ducker(run=run, running=lambda: set(running), worker=False, sounding=lambda: set(sounding),
               media_key=lambda: keys.append("play/pause"))
    d.keys = keys
    return d, ran


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


def test_unreachable_tab_making_sound_gets_the_media_key():
    d, ran = make(playing=(), tabs=0, missed=3, sounding=("com.google.Chrome.helper",))
    d.duck()
    assert d.keys == ["play/pause"]
    d.restore()
    assert d.keys == ["play/pause", "play/pause"]  # pressed again to play


def test_no_media_key_when_the_scripts_reached_every_tab():
    d, ran = make(playing=(), tabs=1, missed=0, sounding=("com.google.Chrome.helper",))
    d.duck()
    assert d.keys == []  # Chrome may still report sound just after a pause: the key would restart it


def test_no_media_key_when_nothing_is_playing():
    d, ran = make(playing=(), tabs=0, missed=3, sounding=("com.thebandwagonapp.app",))
    d.duck()
    assert d.keys == []
