"""Subtle start/stop cues using built-in macOS system sounds."""

from AppKit import NSSound

START = "Tink"
STOP = "Pop"
CANCEL = "Bottle"


class Sounds:
    def __init__(self, enabled=True, volume=0.3):
        self.enabled = enabled
        self.volume = volume
        self._playing = []

    def play(self, name):
        if not self.enabled:
            return
        base = NSSound.soundNamed_(name)
        if base is None:
            return
        # Copy so overlapping cues don't cut each other off; keep a reference until done.
        s = base.copy()
        s.setVolume_(self.volume)
        s.play()
        self._playing = [p for p in self._playing if p.isPlaying()] + [s]
