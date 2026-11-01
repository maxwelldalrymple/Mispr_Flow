"""Pause while you talk: the moment you press the dictation key, whatever is playing pauses (Apple
Music, Spotify, the TV app, and videos or audio in Chrome-family browser tabs); when you let go,
exactly those resume. Nothing that wasn't playing is ever started, and an app that isn't running
is never opened.

Media apps are asked through AppleScript ("player state"); browser tabs through a page script
(the browser's "Allow JavaScript from Apple Events" setting, also used to type into tabs in the
background). All of it runs on one worker thread, in order, so the mic is never held up and a
resume can't overtake its pause.
"""

import queue
import subprocess
import threading

from AppKit import NSWorkspace

# Players with an AppleScript "player state": bundle id -> app name.
PLAYERS = {"com.apple.Music": "Music", "com.spotify.client": "Spotify", "com.apple.TV": "TV"}
# Browsers that run page scripts from AppleScript.
BROWSERS = {"com.google.Chrome": "Google Chrome", "com.brave.Browser": "Brave Browser",
            "com.microsoft.edgemac": "Microsoft Edge", "com.vivaldi.Vivaldi": "Vivaldi",
            "org.chromium.Chromium": "Chromium"}

_PAUSE_PAGE = ("(function(){var n=0;document.querySelectorAll('video,audio').forEach(function(m){"
               "if(!m.paused&&!m.ended){m.pause();m.setAttribute('data-mispr-paused','1');n++;}});return n;})()")
_RESUME_PAGE = ("(function(){var n=0;document.querySelectorAll('[data-mispr-paused]').forEach(function(m){"
                "m.removeAttribute('data-mispr-paused');var p=m.play();if(p&&p.catch)p.catch(function(){});n++;});return n;})()")


def _osascript(script):
    try:
        return subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=4).stdout.strip()
    except Exception:
        return ""


def _running():
    return {str(a.bundleIdentifier()) for a in NSWorkspace.sharedWorkspace().runningApplications() if a.bundleIdentifier()}


def _every_tab(app, js):
    """Run `js` in every tab of `app`; the total of the numbers it returns."""
    escaped = js.replace("\\", "\\\\").replace('"', '\\"')
    script = (f'tell application "{app}"\nset total to 0\nrepeat with w in windows\nrepeat with t in tabs of w\n'
              f'try\nset total to total + (execute t javascript "{escaped}")\nend try\nend repeat\nend repeat\n'
              f'return total\nend tell')
    return script


class Ducker:
    """pause() on press, resume() on release (resume(later=…) after a tap, in case it's a double-tap)."""

    def __init__(self, run=_osascript, running=_running, worker=True):
        self.run, self.running = run, running
        self.paused = None  # what we paused: {"players": [...], "browsers": [...]}, or None
        self.pending = None  # a delayed resume (threading.Timer)
        self.tasks = queue.Queue()
        if worker:
            threading.Thread(target=self._work, name="pause-media", daemon=True).start()
        self.synchronous = not worker  # tests run tasks inline

    def _do(self, fn):
        fn() if self.synchronous else self.tasks.put(fn)

    def _work(self):
        while True:
            fn = self.tasks.get()
            try:
                fn()
            except Exception:
                pass

    # The widget's interface ----------------------------------------------------------------------

    def duck(self):
        """Dictation started: pause what's playing (straight away, off the main thread)."""
        self._cancel_pending()
        self._do(self._pause_all)

    def restore(self, later=0.0):
        """Dictation over: resume what we paused. `later` waits (a tap may be the first of two)."""
        self._cancel_pending()
        if later:
            self.pending = threading.Timer(later, lambda: self._do(self._resume_all))
            self.pending.daemon = True
            self.pending.start()
        else:
            self._do(self._resume_all)

    def recover(self):
        return False  # nothing to undo after a crash: paused music simply stays paused

    def _cancel_pending(self):
        if self.pending is not None:
            self.pending.cancel()
            self.pending = None

    # The work --------------------------------------------------------------------------------------

    def _pause_all(self):
        if self.paused is not None:
            return  # already paused (a double-tap's second tap)
        running = self.running()
        paused = {"players": [], "browsers": []}
        for bundle, app in PLAYERS.items():
            if bundle in running and self.run(f'tell application "{app}" to player state as string') == "playing":
                self.run(f'tell application "{app}" to pause')
                paused["players"].append(app)
        for bundle, app in BROWSERS.items():
            if bundle in running and (self.run(_every_tab(app, _PAUSE_PAGE)) or "0") not in ("", "0"):
                paused["browsers"].append(app)
        self.paused = paused

    def _resume_all(self):
        paused, self.paused = self.paused, None
        if not paused:
            return
        for app in paused["players"]:
            self.run(f'tell application "{app}" to play')
        for app in paused["browsers"]:
            self.run(_every_tab(app, _RESUME_PAGE))
