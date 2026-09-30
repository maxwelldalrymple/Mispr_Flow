"""Sound cues: original WAVs in assets/sounds/, synthesized by tools/make_sounds.py."""

from pathlib import Path

from AppKit import NSSound

SOUNDS = Path(__file__).parent / "assets" / "sounds"

START = "start"        # recording began
STOP = "stop"          # recording finished, transcribing
LOCK = "lock"          # double-tap locked hands-free on
CANCEL = "cancel"      # recording cancelled
ERROR = "error"        # something failed (e.g. the model download)
PASTE = "paste"        # reserved for the main window: re-paste from history
NOTIFICATION = "notification"
ALERT = "alert"
SUCCESS = "success"
ACHIEVEMENT = "achievement"
ALL = (START, STOP, LOCK, CANCEL, ERROR, PASTE, NOTIFICATION, ALERT, SUCCESS, ACHIEVEMENT)


class Sounds:
    # The loudness is baked into each file, so play at full volume by default.
    def __init__(self, enabled=True, volume=1.0):
        self.enabled = enabled
        self.volume = volume
        self._loaded = {}
        self._playing = []

    def _load(self, name):
        if name not in self._loaded:
            path = SOUNDS / f"{name}.wav"
            self._loaded[name] = NSSound.alloc().initWithContentsOfFile_byReference_(str(path), True) if path.exists() else None
        return self._loaded[name]

    def play(self, name):
        if not self.enabled:
            return
        base = self._load(name)
        if base is None:
            return
        # Copy so overlapping cues don't cut each other off; keep a reference until done.
        s = base.copy()
        s.setVolume_(self.volume)
        s.play()
        self._playing = [p for p in self._playing if p.isPlaying()] + [s]
