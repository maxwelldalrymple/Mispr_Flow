"""Quiet while you talk: other sound (music, videos, calls on speakers) is muted while you
dictate or give a command, and comes back the moment you let go.

The Mac's output is muted rather than apps paused: the play/pause key would *start* music when
nothing is playing, while muting works for every source and does nothing when it's silent.
Only a mute this module made is undone (if you'd muted your Mac yourself, it stays muted), and a
marker file makes sure sound is restored even if the app quits mid-dictation.
"""

import subprocess
import threading
import time
from pathlib import Path

MARKER = Path.home() / "Library" / "Application Support" / "Mispr_Flow" / ".muted-while-dictating"
AFTER_CHIME = 0.3  # seconds: mute after the start chime has played


def _osascript(script):
    try:
        return subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=3).stdout.strip()
    except Exception:
        return ""


class Ducker:
    def __init__(self, run=_osascript, marker=MARKER, start=None, sleep=time.sleep):
        self.run, self.marker, self.sleep = run, marker, sleep
        self.start = start or (lambda fn: threading.Thread(target=fn, name="duck", daemon=True).start())
        self.lock = threading.Lock()
        self.wanted = False  # recording now
        self.ours = False  # we muted it (so we unmute it)

    def duck(self):
        """Recording started: mute other sound, a moment after the start chime (off the main thread)."""
        with self.lock:
            self.wanted = True
        self.start(self._mute_soon)

    def _mute_soon(self):
        self.sleep(AFTER_CHIME)
        with self.lock:
            if not self.wanted or self.ours:
                return  # already let go (a quick tap), or already muted
            if self.run("output muted of (get volume settings)") == "true":
                return  # you'd muted it yourself: leave it alone
            self.run("set volume output muted true")
            self.ours = True
            self._mark(True)

    def restore(self):
        """Recording stopped: sound back on, if we were the ones who muted it."""
        with self.lock:
            self.wanted = False
            if not self.ours:
                return
            self.run("set volume output muted false")
            self.ours = False
            self._mark(False)

    def _mark(self, on):
        try:
            if on:
                self.marker.parent.mkdir(parents=True, exist_ok=True)
                self.marker.write_text("1")
            else:
                self.marker.unlink(missing_ok=True)
        except OSError:
            pass

    def recover(self):
        """At startup: the app quit while sound was muted for dictation, so turn it back on."""
        if self.marker.exists():
            self.run("set volume output muted false")
            self._mark(False)
            return True
        return False
