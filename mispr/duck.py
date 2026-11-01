"""Pause while you talk: the moment you press the dictation key, whatever is playing pauses; when
you let go, it plays again.

macOS reports which apps are sending sound to the speakers (CoreAudio's per-process output,
macOS 14.4+; ~4 ms once loaded). If one of them is a music or video source (a browser, Apple
Music, Spotify, VLC…), the play/pause media key is pressed straight away, exactly like the
keyboard's own key; it's pressed again on release. When nothing is playing, nothing is pressed,
so it can never start music on its own.
"""

import ctypes
import struct
import threading

# Apps whose sound means "media is playing" (a browser's sound comes from its helper process).
MEDIA_SOURCES = {
    "com.google.Chrome", "com.google.Chrome.canary", "com.brave.Browser", "com.microsoft.edgemac",
    "company.thebrowser.Browser", "company.thebrowser.dia", "com.vivaldi.Vivaldi", "org.chromium.Chromium",
    "com.operasoftware.Opera", "org.mozilla.firefox", "org.mozilla.plugincontainer", "com.apple.Safari",
    "com.apple.WebKit.GPU", "com.apple.WebKit.WebContent", "com.apple.Music", "com.spotify.client",
    "com.apple.TV", "com.apple.podcasts", "org.videolan.vlc", "com.colliderli.iina", "com.apple.QuickTimePlayerX",
    "com.tidal.desktop", "com.amazon.music", "com.soundcloud.desktop",
}


def is_media(bundle_id):
    return bundle_id.split(".helper")[0] in MEDIA_SOURCES


class _Address(ctypes.Structure):
    _fields_ = [("selector", ctypes.c_uint32), ("scope", ctypes.c_uint32), ("element", ctypes.c_uint32)]


def _code(s):
    return struct.unpack(">I", s.encode())[0]


try:  # loaded once, when the app starts, so the check at a key press is quick
    _CA = ctypes.CDLL("/System/Library/Frameworks/CoreAudio.framework/CoreAudio")
    _CF = ctypes.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
    _CF.CFStringGetCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_long, ctypes.c_uint32]
except OSError:
    _CA = _CF = None
_GLOBAL, _SYSTEM, _UTF8 = _code("glob"), 1, 0x08000100


def _read(obj, selector, ctype, count=1):
    buf = (ctype * count)()
    size = ctypes.c_uint32(ctypes.sizeof(buf))
    err = _CA.AudioObjectGetPropertyData(obj, ctypes.byref(_Address(_code(selector), _GLOBAL, 0)), 0, None,
                                         ctypes.byref(size), buf)
    return buf if err == 0 else None


def playing_apps():
    """Bundle ids of the processes sending sound to the speakers right now. Empty if unknown."""
    if _CA is None:
        return set()
    try:
        size = ctypes.c_uint32(0)
        if _CA.AudioObjectGetPropertyDataSize(_SYSTEM, ctypes.byref(_Address(_code("prs#"), _GLOBAL, 0)), 0, None,
                                              ctypes.byref(size)):
            return set()
        out = set()
        for process in _read(_SYSTEM, "prs#", ctypes.c_uint32, size.value // 4) or []:
            running = _read(process, "piro", ctypes.c_uint32)
            if not running or not running[0]:
                continue
            ref = _read(process, "pbid", ctypes.c_void_p)
            name = ctypes.create_string_buffer(256)
            if ref and ref[0] and _CF.CFStringGetCString(ref[0], name, 256, _UTF8):
                out.add(name.value.decode())
        return out
    except Exception:
        return set()


def _press_play_pause():
    from .apps import press_media
    press_media("play")


class Ducker:
    """duck() on press, restore() on release (restore(later=…) after a tap: it may be a double-tap)."""

    def __init__(self, sounding=playing_apps, media_key=_press_play_pause, timer=threading.Timer):
        self.sounding, self.media_key, self.timer = sounding, media_key, timer
        self.paused = False  # we pressed pause (so we press play)
        self.pending = None  # a delayed restore
        self.lock = threading.RLock()
        sounding()  # warm up now, so the first press is as quick as the rest

    def duck(self):
        """Dictation started: if media is playing, press pause now."""
        with self.lock:
            self._cancel_pending()
            if self.paused:
                return  # still paused from a double-tap's first tap
            if any(is_media(b) for b in self.sounding()):
                self.media_key()
                self.paused = True

    def restore(self, later=0.0):
        """Dictation over: press play if we paused. `later` waits first (a tap may be the first of two)."""
        with self.lock:
            self._cancel_pending()
            if not self.paused:
                return
            if later:
                self.pending = self.timer(later, self.restore)
                self.pending.daemon = True
                self.pending.start()
                return
            self.media_key()
            self.paused = False

    def recover(self):
        return False

    def _cancel_pending(self):
        if self.pending is not None:
            self.pending.cancel()
            self.pending = None
