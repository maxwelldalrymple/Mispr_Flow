"""Voice app switcher: hold the switch key, say an app (or a nickname for one), let go, and
that app comes to the front. "Set nickname C to Chrome" teaches a nickname.

Everything here is local: apps are found on disk and in the running-apps list, never online.
"""

import difflib
import os
import re
from pathlib import Path

APP_DIRS = (
    "/Applications", "/Applications/Utilities", "/System/Applications", "/System/Applications/Utilities",
    str(Path.home() / "Applications"), "/System/Library/CoreServices/Applications",
)
FUZZY_CUTOFF = 0.75  # how close a misheard name must be (difflib ratio)

# "set nickname scooby snacks to chrome", "nickname C for Chrome", "set the nickname for Chrome to C".
_NICKNAME_PATTERNS = (
    re.compile(r"^(?:please\s+)?(?:set|make|add|create)?\s*(?:a|the)?\s*nick\s*name\s+for\s+(?P<app>.+?)\s+(?:to|as|is)\s+(?P<nick>.+)$"),
    re.compile(r"^(?:please\s+)?(?:set|make|add|create)?\s*(?:a|the)?\s*nick\s*name\s+(?P<nick>.+?)\s+(?:to|for|as|is|means)\s+(?P<app>.+)$"),
)
# Spoken filler around an app name: "open chrome", "switch to the terminal", "go to Slack please".
_FILLER = re.compile(r"^(?:(?:please|ok|okay|hey|um|uh)\s+)*(?:(?:open|switch|go|bring|show|launch|focus)(?:\s+(?:to|up|me))?\s+)?(?:the\s+)?|\s+(?:app|please)$")


def normalize(text):
    """Lowercase words only: "Google Chrome." -> "google chrome"."""
    text = re.sub(r"[^\w\s]", " ", text.lower().replace("’", "").replace("'", ""))
    return " ".join(text.split())


def parse(text):
    """What was said: ("nickname", nick, app), ("switch", name), or None for nothing usable."""
    said = normalize(text)
    if not said:
        return None
    for pattern in _NICKNAME_PATTERNS:
        m = pattern.match(said)
        if m:
            return ("nickname", m["nick"].strip(), m["app"].strip())
    said = _number_words(said)
    m = _SHORTCUT.match(said)
    if m:  # "new tab", "close tab in chrome", "chrome reload", "tab 3"
        lead = r"^(?:(?:please|go|to|open|switch|then|and|a|the)\b\s*)+"
        app = next((n for n in (re.sub(lead, "", m[k] or "").strip() for k in ("app", "app2")) if n), None)
        name = m["cmd"]
        if name.startswith(("tab ", "go to tab ", "switch to tab ")):
            n = int(name.split()[-1])
            if not 1 <= n <= 9:
                return None
            name = f"tab {n}"
        return ("shortcut", SHORTCUT_ALIASES.get(name, name), _FILLER.sub("", app).strip() if app else None)
    m = _QUIT.match(said)
    if m:
        return ("quit", _FILLER.sub("", m["app"]).strip())
    m = _ACTION.match(said)
    if m:  # close / minimize / expand, of an app or (none named) the current one
        target = _FILLER.sub("", m["rest"] or "").strip() or None
        return (_ACTIONS[m["verb"]], target)
    m = _BESIDE.match(said)
    if m:  # "chrome beside vs code", "window layout chrome 70% next to terminal"
        left, right = _FILLER.sub("", m["left"]).strip(), _FILLER.sub("", m["right"]).strip()
        pct = int(m["pct"]) if m["pct"] else None
        return ("beside", left, right, pct if pct and 10 <= pct <= 90 else None)
    m = _SIZE.match(said)
    if m and 10 <= int(m["pct"]) <= 100:  # "chrome 80%"
        return ("size", _FILLER.sub("", m["app"]).strip(), int(m["pct"]))
    name = _FILLER.sub("", said).strip()
    return ("switch", name) if name else None


# Keyboard shortcuts most Mac apps (and every browser) share: name -> (key code, modifiers).
_KEY = {"t": 17, "w": 13, "n": 45, "r": 15, "l": 37, "f": 3, "d": 2, "[": 33, "]": 30, "tab": 48,
        "0": 29, "=": 24, "-": 27, "1": 18, "2": 19, "3": 20, "4": 21, "5": 23, "6": 22, "7": 26, "8": 28, "9": 25}
SHORTCUTS = {
    "new tab": ("t", "cmd"), "close tab": ("w", "cmd"), "reopen tab": ("t", "cmd shift"),
    "next tab": ("tab", "ctrl"), "previous tab": ("tab", "ctrl shift"),
    "new window": ("n", "cmd"), "new private window": ("n", "cmd shift"), "close window": ("w", "cmd shift"),
    "reload": ("r", "cmd"), "back": ("[", "cmd"), "forward": ("]", "cmd"), "address bar": ("l", "cmd"),
    "find": ("f", "cmd"), "bookmark": ("d", "cmd"), "zoom in": ("=", "cmd"), "zoom out": ("-", "cmd"),
    "actual size": ("0", "cmd"), "full screen": ("f", "ctrl cmd"), "last tab": ("9", "cmd"),
    **{f"tab {n}": (str(n), "cmd") for n in range(1, 9)},
}
SHORTCUT_ALIASES = {
    "open tab": "new tab", "open a new tab": "new tab", "a new tab": "new tab", "close this tab": "close tab",
    "close the tab": "close tab", "reopen closed tab": "reopen tab", "reopen the tab": "reopen tab",
    "undo close tab": "reopen tab", "next": "next tab", "previous": "previous tab", "prev tab": "previous tab",
    "new incognito window": "new private window", "incognito window": "new private window",
    "private window": "new private window", "incognito": "new private window", "refresh": "reload",
    "reload page": "reload", "refresh page": "reload", "go back": "back", "go forward": "forward",
    "search bar": "address bar", "url bar": "address bar", "url": "address bar", "search": "find",
    "find on page": "find", "bookmark this": "bookmark", "bookmark page": "bookmark", "zoom": "zoom in",
    "reset zoom": "actual size", "fullscreen": "full screen", "enter full screen": "full screen",
    "exit full screen": "full screen", "close this window": "close window",
}
_SHORTCUT_WORDS = "|".join(sorted((re.escape(k) for k in list(SHORTCUTS) + list(SHORTCUT_ALIASES)), key=len, reverse=True))
_SHORTCUT = re.compile(rf"^(?:please\s+)?(?:(?P<app>.+?)\s+)?(?P<cmd>{_SHORTCUT_WORDS}|(?:go to |switch to )?tab \d+)"
                       rf"(?:\s+(?:in|on|for)\s+(?P<app2>.+))?$")
_QUIT = re.compile(r"^(?:please\s+)?(?:quit|exit)\s+(?P<app>.+)$")


def press_shortcut(name, post=None):
    """Press the shortcut `name` (see SHORTCUTS) in the app in front."""
    import Quartz
    key, mods = SHORTCUTS[name]
    flags = 0
    for m in mods.split():
        flags |= {"cmd": Quartz.kCGEventFlagMaskCommand, "shift": Quartz.kCGEventFlagMaskShift,
                  "ctrl": Quartz.kCGEventFlagMaskControl}[m]
    post = post or (lambda event: Quartz.CGEventPost(Quartz.kCGSessionEventTap, event))
    source = Quartz.CGEventSourceCreate(Quartz.kCGEventSourceStateHIDSystemState)
    for down in (True, False):
        event = Quartz.CGEventCreateKeyboardEvent(source, _KEY[key], down)
        Quartz.CGEventSetFlags(event, flags)
        post(event)


def quit_app(pid):
    """Ask the app to quit normally (it can still ask about unsaved work). True if asked."""
    from AppKit import NSRunningApplication
    app = NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
    return bool(app and app.terminate())


_ACTIONS = {"close": "close", "minimize": "minimize", "minimise": "minimize", "hide": "minimize",
            "expand": "expand", "maximize": "expand", "maximise": "expand", "fill": "expand"}
_ACTION = re.compile(r"^(?:please\s+)?(?P<verb>close|minimi[sz]e|hide|expand|maximi[sz]e|fill)(?:\s+(?P<rest>.+))?$")
_LAYOUT = r"(?:(?:window\s+)?layout\s+|put\s+|place\s+|split\s+)?"
_BESIDE = re.compile(_LAYOUT + r"(?P<left>.+?)(?:\s+(?P<pct>\d{1,3})\s*(?:percent)?)?\s+(?:beside|next\s+to|and|with)\s+(?P<right>.+)$")
_SIZE = re.compile(r"^(?:make\s+|resize\s+|size\s+)?(?P<app>.+?)\s+(?:to\s+)?(?P<pct>\d{1,3})\s*(?:percent)?$")
_TENS = {"ten": 10, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
         "eighty": 80, "ninety": 90, "hundred": 100, "a hundred": 100, "one hundred": 100, "half": 50}
_ONES = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9}


def _number_words(said):
    """"eighty five percent" -> "85 percent" (normalize() already turned "80%" into "80")."""
    for tens, n in sorted(_TENS.items(), key=lambda kv: -len(kv[0])):
        for ones, k in _ONES.items():
            said = re.sub(rf"\b{tens}[ -]{ones}\b", str(n + k), said)
        said = re.sub(rf"\b{tens}\b", str(n), said)
    return said


# --- Windows (Accessibility, already granted for pasting) ---------------------------------

def layout(screen, kind, pct=None):
    """Window frames (x, y, w, h; top-left origin) inside `screen` (the same):
    "expand" fills it, "size" is pct% of its width and height centred, "beside" is two
    side-by-side frames, the first pct% wide (half by default)."""
    x, y, w, h = screen
    if kind == "expand":
        return (x, y, w, h)
    if kind == "size":
        fw, fh = w * pct / 100, h * pct / 100
        return (x + (w - fw) / 2, y + (h - fh) / 2, fw, fh)
    left = w * (pct or 50) / 100
    return (x, y, left, h), (x + left, y, w - left, h)


def screen_frame():
    """The main screen's usable area (no menu bar or Dock), in Accessibility's top-left coordinates."""
    from AppKit import NSScreen
    full = NSScreen.screens()[0].frame().size.height
    v = NSScreen.mainScreen().visibleFrame()
    return (v.origin.x, full - v.origin.y - v.size.height, v.size.width, v.size.height)


def pid_for(path):
    """Process id of the running app at `path`, or None."""
    from AppKit import NSWorkspace
    for app in NSWorkspace.sharedWorkspace().runningApplications():
        if app.bundleURL() is not None and str(app.bundleURL().path()) == path:
            return app.processIdentifier()
    return None


def frontmost_pid():
    from AppKit import NSWorkspace
    app = NSWorkspace.sharedWorkspace().frontmostApplication()
    return app.processIdentifier() if app is not None else None


def _window(pid):
    import ApplicationServices as AS
    app = AS.AXUIElementCreateApplication(pid)
    for name in ("AXFocusedWindow", "AXMainWindow"):
        err, win = AS.AXUIElementCopyAttributeValue(app, name, None)
        if err == 0 and win is not None:
            return win
    err, wins = AS.AXUIElementCopyAttributeValue(app, "AXWindows", None)
    return wins[0] if err == 0 and wins else None


def window_action(pid, action, frame=None):
    """Do `action` ("close", "minimize", or "frame" with (x, y, w, h)) to app `pid`'s front
    window. True if done; False if it has no window (or won't say)."""
    import ApplicationServices as AS
    win = _window(pid)
    if win is None:
        return False
    if action == "close":
        err, button = AS.AXUIElementCopyAttributeValue(win, "AXCloseButton", None)
        return err == 0 and button is not None and AS.AXUIElementPerformAction(button, "AXPress") == 0
    if action == "minimize":
        return AS.AXUIElementSetAttributeValue(win, "AXMinimized", True) == 0
    x, y, w, h = frame
    AS.AXUIElementSetAttributeValue(win, "AXMinimized", False)
    pos = AS.AXValueCreate(AS.kAXValueCGPointType, (x, y))
    size = AS.AXValueCreate(AS.kAXValueCGSizeType, (w, h))
    # Size, move, size again: some apps clamp the size against the old position.
    AS.AXUIElementSetAttributeValue(win, "AXSize", size)
    AS.AXUIElementSetAttributeValue(win, "AXPosition", pos)
    return AS.AXUIElementSetAttributeValue(win, "AXSize", size) == 0


def find_apps(dirs=APP_DIRS):
    """{display name: path} for every .app in the usual folders (one level of subfolders)."""
    found = {}
    for top in dirs:
        try:
            entries = list(os.scandir(top))
        except OSError:
            continue
        for entry in entries:
            if entry.name.endswith(".app"):
                found.setdefault(entry.name[:-4], entry.path)
            elif entry.is_dir() and not entry.name.startswith("."):
                try:
                    for sub in os.scandir(entry.path):
                        if sub.name.endswith(".app"):
                            found.setdefault(sub.name[:-4], sub.path)
                except OSError:
                    pass
    return found


def running_apps():
    """{name: path} of apps with a window in the Dock (not background helpers)."""
    from AppKit import NSApplicationActivationPolicyRegular, NSWorkspace

    out = {}
    for app in NSWorkspace.sharedWorkspace().runningApplications():
        if app.activationPolicy() == NSApplicationActivationPolicyRegular and app.bundleURL() is not None:
            out[str(app.localizedName())] = str(app.bundleURL().path())
    return out


def match(name, apps, nicknames=None, running=()):
    """The app `name` refers to: a nickname, an exact name, a word of a name ("chrome" ->
    "Google Chrome"), a prefix, or a close-sounding name. Running apps win ties. None if unsure."""
    said = normalize(name)
    if not said:
        return None
    for nick, app in (nicknames or {}).items():
        if normalize(nick) == said:
            return app
    by_norm = {}
    for app in sorted(apps, key=lambda a: (a not in running, len(a))):
        by_norm.setdefault(normalize(app), app)
    if said in by_norm:
        return by_norm[said]
    squashed = said.replace(" ", "")
    for norm, app in by_norm.items():  # "face time" -> FaceTime, "vs code" -> "VS Code"
        if norm.replace(" ", "") == squashed:
            return app
    if len(said) >= 3:
        for norm, app in by_norm.items():  # "photo" -> Photos (not Photo Booth)
            if norm.startswith(said) and len(norm) - len(said) <= 2:
                return app
        for norm, app in by_norm.items():  # "chrome" -> Google Chrome, "code" -> Visual Studio Code
            if said in norm.split() or (" " in said and said in norm):
                return app
        for norm, app in by_norm.items():  # "photo" -> Photos, "term" -> Terminal
            if norm.startswith(said):
                return app
    close = difflib.get_close_matches(said, list(by_norm), n=1, cutoff=FUZZY_CUTOFF)
    return by_norm[close[0]] if close else None


def bring_to_front(path, workspace=None):
    """Activate the app at `path`, launching it if it isn't running. True on success."""
    from AppKit import NSWorkspace, NSWorkspaceOpenConfiguration
    from Foundation import NSURL

    config = NSWorkspaceOpenConfiguration.configuration()
    config.setActivates_(True)
    (workspace or NSWorkspace.sharedWorkspace()).openApplicationAtURL_configuration_completionHandler_(
        NSURL.fileURLWithPath_(path), config, None)
    return True
