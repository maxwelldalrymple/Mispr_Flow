"""Pause while you talk (mispr/duck.py). The media key and the "what's playing" check are replaced:
nothing on this Mac is paused or played by these tests."""

from mispr import duck
from mispr.duck import Ducker


class Timer:
    made = []

    def __init__(self, delay, fn):
        self.fn, self.cancelled, self.daemon = fn, False, False
        Timer.made.append(self)

    def start(self):
        pass

    def cancel(self):
        self.cancelled = True


def make(sounding=("com.google.Chrome.helper",)):
    keys = []
    Timer.made = []
    d = Ducker(sounding=lambda: set(sounding), media_key=lambda: keys.append("play/pause"), timer=Timer)
    return d, keys


def test_playing_media_is_paused_then_played():
    d, keys = make()
    d.duck()
    assert keys == ["play/pause"]
    d.restore()
    assert keys == ["play/pause", "play/pause"]


def test_nothing_playing_presses_nothing():
    d, keys = make(sounding=("com.thebandwagonapp.app", "systemsoundserverd"))
    d.duck()
    d.restore()
    assert keys == []  # the key would start music


def test_a_tap_waits_and_a_second_tap_stays_paused():
    d, keys = make()
    d.duck()
    d.restore(later=1.0)  # the first tap of a double-tap
    assert keys == ["play/pause"] and len(Timer.made) == 1
    d.duck()  # the second tap: hands-free
    assert Timer.made[0].cancelled and keys == ["play/pause"]
    d.restore()
    assert keys == ["play/pause", "play/pause"]


def test_a_lone_tap_plays_after_the_wait():
    d, keys = make()
    d.duck()
    d.restore(later=1.0)
    Timer.made[0].fn()  # the wait ran out: no second tap
    assert keys == ["play/pause", "play/pause"]


def test_media_sources():
    assert duck.is_media("com.google.Chrome.helper") and duck.is_media("com.spotify.client")
    assert not duck.is_media("com.thebandwagonapp.app")
