"""Pause while you talk: the moment you press the dictation key, whatever is playing pauses; when
you let go, it plays again.

macOS is asked whether something is playing (its "now playing" media: a video, Music, Spotify…).
If so, it gets an explicit *pause* (not the play/pause toggle, which started paused videos), and
an explicit *play* on release, only if this paused it. A paused or idle player is never started.
(`playing_apps` below reports which apps send sound to the speakers; it stays as a diagnostic, but
it can't tell a paused video from a playing one: Chrome keeps its audio open after a pause.)
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


# --- macOS's media commands (what Control Center's play/pause uses): an explicit pause, never a toggle ---

_MR = {}
_PLAY, _PAUSE = 0, 1  # MRMediaRemoteCommand values


def _media_remote():
    """MediaRemote's functions, loaded once: (is_playing(queue, block), send_command(cmd, options))."""
    if not _MR:
        import objc
        from Foundation import NSBundle
        bundle = NSBundle.bundleWithPath_("/System/Library/PrivateFrameworks/MediaRemote.framework")
        objc.loadBundleFunctions(bundle, _MR, [
            ("MRMediaRemoteGetNowPlayingApplicationIsPlaying", b"v@@?", "",
             {"arguments": {1: {"callable": {"retval": {"type": b"v"}, "arguments": {0: {"type": b"^v"}, 1: {"type": b"Z"}}}}}}),
            ("MRMediaRemoteSendCommand", b"ZI@"),
        ])
        libsystem = ctypes.CDLL("/usr/lib/libSystem.dylib")
        libsystem.dispatch_queue_create.restype = ctypes.c_void_p
        libsystem.dispatch_queue_create.argtypes = [ctypes.c_char_p, ctypes.c_void_p]
        _MR["queue"] = objc.objc_object(c_void_p=libsystem.dispatch_queue_create(b"mispr.media", None))
    return _MR


def media_is_playing(timeout=0.3):
    """True if something is playing now (the "now playing" app: a video, Music, Spotify…). False if
    paused, nothing, or no answer in time."""
    try:
        mr = _media_remote()
        answer, done = [], threading.Event()

        def got(playing):  # runs on macOS's queue: must return None and never raise (that aborts the process)
            try:
                answer.append(bool(playing))
            finally:
                done.set()

        mr["MRMediaRemoteGetNowPlayingApplicationIsPlaying"](mr["queue"], got)
        done.wait(timeout)
        return bool(answer and answer[0])
    except Exception:
        return False


def send_media(command):
    """Pause or play the "now playing" app: an explicit command, so pause never starts anything."""
    try:
        return bool(_media_remote()["MRMediaRemoteSendCommand"](command, None))
    except Exception:
        return False


class Ducker:
    """duck() on press, restore() on release (restore(later=…) after a tap: it may be a double-tap).
    Pause only if something is playing; play again only what this paused."""

    def __init__(self, playing=media_is_playing, send=send_media, timer=threading.Timer):
        self.playing, self.send, self.timer = playing, send, timer
        self.paused = False  # we paused it (so we play it)
        self.pending = None  # a delayed restore
        self.lock = threading.RLock()
        try:
            _media_remote()  # load now, so the first press is as quick as the rest
        except Exception:
            pass

    def duck(self):
        """Dictation started: if something is playing, pause it (an explicit pause: never a toggle)."""
        with self.lock:
            self._cancel_pending()
            if self.paused:
                return  # still paused from a double-tap's first tap
            if self.playing():
                self.send(_PAUSE)
                self.paused = True

    def restore(self, later=0.0):
        """Dictation over: play again, only if we paused it. `later` waits first (a tap may be the first of two)."""
        with self.lock:
            self._cancel_pending()
            if not self.paused:
                return
            if later:
                self.pending = self.timer(later, self.restore)
                self.pending.daemon = True
                self.pending.start()
                return
            self.send(_PLAY)
            self.paused = False

    def recover(self):
        return False

    def _cancel_pending(self):
        if self.pending is not None:
            self.pending.cancel()
            self.pending = None
