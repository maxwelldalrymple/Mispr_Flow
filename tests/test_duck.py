"""Pause while you talk (mispr/duck.py). macOS's media commands are replaced by recorders: nothing
on this Mac is paused or played by these tests."""

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


def make(playing=True):
    sent = []
    Timer.made = []
    d = Ducker(playing=lambda: playing, send=lambda command: sent.append({0: "play", 1: "pause"}[command]), timer=Timer)
    return d, sent


def test_playing_media_is_paused_then_played():
    d, sent = make(playing=True)
    d.duck()
    assert sent == ["pause"]
    d.restore()
    assert sent == ["pause", "play"]


def test_a_paused_video_is_never_started():
    d, sent = make(playing=False)
    d.duck()
    d.restore()
    assert sent == []  # the old play/pause toggle started it


def test_only_ever_explicit_pause_and_play():
    assert duck._PAUSE == 1 and duck._PLAY == 0  # MediaRemote: never the toggle (2)


def test_a_tap_waits_and_a_second_tap_stays_paused():
    d, sent = make()
    d.duck()
    d.restore(later=1.0)  # the first tap of a double-tap
    assert sent == ["pause"] and len(Timer.made) == 1
    d.duck()  # the second tap: hands-free
    assert Timer.made[0].cancelled and sent == ["pause"]
    d.restore()
    assert sent == ["pause", "play"]


def test_a_lone_tap_plays_after_the_wait():
    d, sent = make()
    d.duck()
    d.restore(later=1.0)
    Timer.made[0].fn()
    assert sent == ["pause", "play"]
