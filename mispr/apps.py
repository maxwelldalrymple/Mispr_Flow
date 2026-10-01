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
FUZZY_CUTOFF = 0.82  # how close a misheard name must be (difflib ratio)

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
    for pattern, make in _SOUND:
        m = pattern.match(said)
        if m and make(m) is not None:
            return make(m)
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
    m = _OPEN_FOLDER.match(said)
    if m:  # "open folder projects", "open the downloads folder"
        return ("open_folder", m["a"] or m["b"])
    m = _OPEN.match(said)
    if m:  # "open budget": in Finder, something in this folder; elsewhere, an app
        return ("open", m["name"])
    name = _FILLER.sub("", said).strip()
    return ("switch", name) if name else None


_OPEN_FOLDER = re.compile(r"^(?:please\s+)?(?:open|show|go\s+to)\s+(?:the\s+|my\s+)?(?:folder\s+(?P<a>.+)|(?P<b>.+?)\s+folder)$")
_OPEN = re.compile(r"^(?:please\s+)?open\s+(?:the\s+|up\s+)?(?P<name>.+?)(?:\s+please)?$")


# --- Folders and files -------------------------------------------------------------------

SKIP_DIRS = {"Library", "node_modules", "__pycache__", "venv", ".venv", "site-packages", "build", "dist",
             "DerivedData", "Pods", "target"}


def name_key(name):
    """Folder/file names as spoken: "Mispr_Flow" / "voice-recordings" -> "misprflow" / "voicerecordings"."""
    return re.sub(r"[\W_]+", "", name.lower())


def find_in(root, name, files=True, max_depth=8, budget=1.5, clock=None):
    """The shallowest folder (or file, by name with or without its extension) under `root` whose
    name sounds like `name`, searching level by level so duplicates resolve to the highest one.
    Hidden folders, Library and build/dependency folders are skipped. None if not found in time."""
    import time as _time
    clock = clock or _time.monotonic
    want = name_key(name)
    if not want:
        return None
    deadline = clock() + budget
    level = [str(root)]
    for _ in range(max_depth):
        found, below = [], []
        for folder in level:
            try:
                entries = sorted(os.scandir(folder), key=lambda e: e.name.lower())
            except OSError:
                continue
            for e in entries:
                if e.name.startswith("."):
                    continue
                is_dir = e.is_dir(follow_symlinks=False)
                stem = e.name if is_dir else os.path.splitext(e.name)[0]
                if (is_dir or files) and want in (name_key(e.name), name_key(stem)):
                    found.append(e.path)
                if is_dir and e.name not in SKIP_DIRS and not e.name.endswith((".app", ".photoslibrary", ".bundle")):
                    below.append(e.path)
            if clock() > deadline:
                return found[0] if found else None
        if found:
            return min(found, key=lambda p: (not os.path.isdir(p), len(p)))  # folders first
        level = below
        if not level:
            return None
    return None


def finder_control(ask=False):
    """May Mispr Flow tell Finder what to show ("open folder")? True / False, or None when
    macOS hasn't asked yet. With `ask`, macOS shows its one-time prompt if it hasn't."""
    import ctypes
    cs = ctypes.CDLL("/System/Library/Frameworks/CoreServices.framework/CoreServices")

    class Desc(ctypes.Structure):
        _fields_ = [("descriptorType", ctypes.c_uint32), ("dataHandle", ctypes.c_void_p)]

    four = lambda code: int.from_bytes(code.encode(), "big")
    bundle = b"com.apple.finder"
    desc = Desc()
    if cs.AECreateDesc(four("bund"), bundle, len(bundle), ctypes.byref(desc)) != 0:
        return None
    try:
        cs.AEDeterminePermissionToAutomateTarget.restype = ctypes.c_int32
        status = cs.AEDeterminePermissionToAutomateTarget(ctypes.byref(desc), four("****"), four("****"), bool(ask))
    finally:
        cs.AEDisposeDesc(ctypes.byref(desc))
    return {0: True, -1743: False}.get(status)  # -1744: not decided yet


def _quote(path):
    return path.replace("\\", "\\\\").replace('"', '\\"')


def finder_folder(run=None):
    """The folder shown in the front Finder window, or None (no window, or not allowed)."""
    out = _osascript('tell application "Finder" to if (count of Finder windows) > 0 then '
                     'get POSIX path of (target of front Finder window as alias)', run)
    return (out.rstrip("/") or "/") if out.startswith("/") else None


def finder_go(path, run=None):
    """Show `path` in the front Finder window (same window, like double-clicking a folder)."""
    _osascript(f'tell application "Finder" to set target of front Finder window to (POSIX file "{_quote(path)}" as alias)', run)


def open_path(path, run=None):
    """Open a folder in a new Finder window, or a file in its usual app."""
    import subprocess
    (run or (lambda cmd: subprocess.run(cmd, capture_output=True, timeout=5)))(["open", path])


# Sound: media keys, volume, mic, tab muting.
_SOUND = (
    (re.compile(r"^(?:please\s+)?(?:play|pause|resume|play pause|stop the music|stop music|unpause)(?:\s+(?:music|it|the music|video|the video|song))?$"),
     lambda m: ("media", "play")),
    (re.compile(r"^(?:(?P<verb>skip|jump|go|fast)\s+)?(?P<dir>forward|ahead|back|backward|backwards|rewind)"
                r"(?:\s+(?:by\s+)?(?P<n>\d+)\s*(?P<unit>seconds?|secs?|minutes?|mins?)?)?(?:\s+(?:in|on)\s+(?P<app>.+))?$"),
     # plain "go back"/"forward" (no time, no skip/jump) is the browser's back/forward
     lambda m: ("seek", _seek_seconds(m), m["app"]) if (m["n"] or m["verb"] in ("skip", "jump", "fast")) else None),
    (re.compile(r"^rewind(?:\s+(?P<n>\d+)\s*(?P<unit>seconds?|secs?|minutes?|mins?)?)?(?:\s+(?:in|on)\s+(?P<app>.+))?$"),
     lambda m: ("seek", -abs(_seek_seconds(m, "back")), m["app"])),
    (re.compile(r"^scroll\s+(?:(?:all\s+the\s+way\s+)?to\s+(?:the\s+)?)?(?P<end>top|bottom)$"),
     lambda m: ("scroll_end", m["end"])),
    (re.compile(r"^(?:scroll\s+)?(?P<dir>up|down)(?:\s+(?P<amt>a\s+little|a\s+bit|a\s+lot|more|a\s+page|lots))?"
                r"(?:\s+(?P<n>\d+)(?:\s+times)?)?$"),
     lambda m: ("scroll", _scroll_pixels(m)) if m.string.startswith("scroll") else None),
    (re.compile(r"^page\s+(?P<dir>up|down)$"), lambda m: ("scroll", -SCROLL_PAGE if m["dir"] == "down" else SCROLL_PAGE)),
    (re.compile(r"^(?:next|skip)(?:\s+(?:track|song|one))?$"), lambda m: ("media", "next")),
    (re.compile(r"^(?:previous|last|go back a)\s+(?:track|song)$"), lambda m: ("media", "previous")),
    (re.compile(r"^(?:volume up|turn (?:it|the volume) up|louder|turn up(?: the volume)?)$"), lambda m: ("volume", "up")),
    (re.compile(r"^(?:volume down|turn (?:it|the volume) down|quieter|softer|turn down(?: the volume)?)$"), lambda m: ("volume", "down")),
    (re.compile(r"^(?:set\s+)?volume\s+(?:to\s+)?(?P<n>\d{1,3})(?:\s*percent)?$"), lambda m: ("volume", min(100, int(m["n"])))),
    (re.compile(r"^(?P<un>un)?mute\s+(?:my\s+|the\s+)?(?:mic|microphone)$"), lambda m: ("mic", not m["un"])),
    (re.compile(r"^(?P<un>un)?mute(?:\s+(?:the\s+)?(?:sound|volume|audio|speakers?|computer|mac))?$"), lambda m: ("volume", "unmute" if m["un"] else "mute")),
    (re.compile(r"^(?P<un>un)?mute\s+(?:this\s+|the\s+)?(?:tab|site)(?:\s+(?:in|on)\s+(?P<app>.+))?$"),
     lambda m: ("mute_tab", m["app"], not m["un"])),
    (re.compile(r"^(?P<un>un)?mute\s+(?:the\s+)?(?:app\s+)?(?P<app>.+?)(?:\s+app)?$"), lambda m: ("mute_app", m["app"], not m["un"])),
)

SCROLL_STEP, SCROLL_PAGE = 450, 900  # pixels: about half a screen, about a screen


def _scroll_pixels(m):
    amount = {"a little": 0.35, "a bit": 0.35, "a lot": 3, "lots": 3, "more": 2, "a page": 2}.get(
        " ".join((m["amt"] or "").split()), 1)
    pixels = int(SCROLL_STEP * amount * (int(m["n"]) if m["n"] else 1))
    return -pixels if m["dir"] == "down" else pixels


def scroll(pixels, post=None):
    """Scroll whatever is under the pointer, like a trackpad (+ up, - down)."""
    import Quartz
    post = post or (lambda event: Quartz.CGEventPost(Quartz.kCGHIDEventTap, event))
    step = 120 if pixels > 0 else -120
    for _ in range(max(1, abs(pixels) // 120)):  # several small steps scroll smoothly
        post(Quartz.CGEventCreateScrollWheelEvent(None, Quartz.kCGScrollEventUnitPixel, 1, step))


SEEK_STEP = 5  # seconds per arrow-key press in YouTube, most web players, QuickTime, IINA
SEEK_DEFAULT = 10


def _seek_seconds(m, direction=None):
    n = int(m["n"]) if m["n"] else SEEK_DEFAULT
    if (m["unit"] or "").startswith("min"):
        n *= 60
    back = (direction or m["dir"]) in ("back", "backward", "backwards", "rewind")
    return -n if back else n


def seek(seconds, post=None):
    """Skip forward (+) or back (-): one arrow-key press per 5 seconds, in the app in front."""
    import Quartz
    post = post or (lambda event: Quartz.CGEventPost(Quartz.kCGSessionEventTap, event))
    key = 124 if seconds > 0 else 123  # right / left arrow
    source = Quartz.CGEventSourceCreate(Quartz.kCGEventSourceStateHIDSystemState)
    for _ in range(max(1, round(abs(seconds) / SEEK_STEP))):
        for down in (True, False):
            event = Quartz.CGEventCreateKeyboardEvent(source, key, down)
            Quartz.CGEventSetFlags(event, 0)
            post(event)


MEDIA_KEYS = {"play": 16, "next": 17, "previous": 18}  # NX_KEYTYPE_PLAY / NEXT / PREVIOUS


def press_media(key, post=None):
    """Press a media key (play/pause, next, previous): it goes to whatever is playing."""
    import Quartz
    from AppKit import NSEvent
    post = post or (lambda event: Quartz.CGEventPost(Quartz.kCGHIDEventTap, event))
    for state in (0xA, 0xB):  # key down, key up
        event = NSEvent.otherEventWithType_location_modifierFlags_timestamp_windowNumber_context_subtype_data1_data2_(
            14, (0, 0), state << 8, 0, 0, None, 8, (MEDIA_KEYS[key] << 16) | (state << 8), -1)
        post(event.CGEvent())


def _osascript(script, run=None):
    import subprocess
    run = run or (lambda cmd: subprocess.run(cmd, capture_output=True, text=True, timeout=3).stdout.strip())
    return run(["osascript", "-e", script])


def set_volume(change, run=None):
    """"up"/"down" (10 points), "mute"/"unmute", or a level 0-100. Returns the new level (or None)."""
    if change in ("mute", "unmute"):
        _osascript(f"set volume output muted {'true' if change == 'mute' else 'false'}", run)
        return None
    if change in ("up", "down"):
        step = 10 if change == "up" else -10
        script = f"set volume output volume ((output volume of (get volume settings)) + {step}) without output muted"
    else:
        script = f"set volume output volume {int(change)} without output muted"
    _osascript(script, run)
    level = _osascript("output volume of (get volume settings)", run)
    return int(level) if level.isdigit() else None


def mic_level(run=None):
    level = _osascript("input volume of (get volume settings)", run)
    return int(level) if level.isdigit() else None


def set_mic_level(level, run=None):
    _osascript(f"set volume input volume {int(level)}", run)


def mute_tab(pid, mute=True):
    """Chrome-style browsers: press "Mute site" (or "Unmute site") in the selected tab's menu.
    True if done, None if it was already that way (the other item is there), False if no tab menu."""
    import ApplicationServices as AS
    def attr(el, name):
        err, v = AS.AXUIElementCopyAttributeValue(el, name, None)
        return v if err == 0 else None
    def find(el, test, depth=0):
        if el is None or depth > 12:
            return None
        if test(el):
            return el
        for child in attr(el, "AXChildren") or []:
            hit = find(child, test, depth + 1)
            if hit is not None:
                return hit
        return None
    win = _window(pid)
    tab = find(win, lambda e: attr(e, "AXRole") == "AXRadioButton" and attr(e, "AXValue") == 1
               and attr(attr(e, "AXParent"), "AXRole") == "AXTabGroup")
    if tab is None or AS.AXUIElementPerformAction(tab, "AXShowMenu") != 0:
        return False
    wanted = ("mute site", "mute tab") if mute else ("unmute site", "unmute tab")
    other = ("unmute site", "unmute tab") if mute else ("mute site", "mute tab")
    root = AS.AXUIElementCreateApplication(pid)
    title = lambda e: str(attr(e, "AXTitle") or "").lower()
    item = find(root, lambda e: attr(e, "AXRole") == "AXMenuItem" and title(e) in wanted)
    if item is not None:
        return AS.AXUIElementPerformAction(item, "AXPress") == 0
    if find(root, lambda e: attr(e, "AXRole") == "AXMenuItem" and title(e) in other) is not None:
        AS.AXUIElementPerformAction(tab, "AXCancel")  # close the menu again
        return None
    return False


# Keyboard shortcuts most Mac apps (and every browser) share: name -> (key code, modifiers).
_KEY = {"up": 126, "down": 125, "t": 17, "w": 13, "n": 45, "r": 15, "l": 37, "f": 3, "d": 2, "[": 33, "]": 30, "tab": 48,
        "0": 29, "=": 24, "-": 27, "1": 18, "2": 19, "3": 20, "4": 21, "5": 23, "6": 22, "7": 26, "8": 28, "9": 25}
SHORTCUTS = {
    "new tab": ("t", "cmd"), "close tab": ("w", "cmd"), "reopen tab": ("t", "cmd shift"),
    "next tab": ("tab", "ctrl"), "previous tab": ("tab", "ctrl shift"),
    "new window": ("n", "cmd"), "new private window": ("n", "cmd shift"), "close window": ("w", "cmd shift"),
    "reload": ("r", "cmd"), "back": ("[", "cmd"), "forward": ("]", "cmd"), "address bar": ("l", "cmd"),
    "find": ("f", "cmd"), "bookmark": ("d", "cmd"), "zoom in": ("=", "cmd"), "zoom out": ("-", "cmd"),
    "actual size": ("0", "cmd"), "full screen": ("f", "ctrl cmd"), "last tab": ("9", "cmd"),
    "top": ("up", "cmd"), "bottom": ("down", "cmd"),
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


# Words in many app names that say nothing about which app ("Logic Pro", "Visual Studio Code").
GENERIC_WORDS = {"pro", "app", "apps", "studio", "desktop", "mac", "for", "the", "plus", "mini", "lite", "player",
                 "helper", "one", "go", "x", "air", "max", "free", "beta", "new", "edition", "community"}


def match_scored(name, apps, nicknames=None, running=()):
    """(app, strong) for what was said, or (None, False). Strong: a nickname, the exact name, the
    name without spaces ("face time"), or one distinctive word of it ("chrome"). Weak: a near-prefix, a distinctive word of the name,
    a prefix, or a close-sounding name, used only for apps already open (see the widget).
    Generic words ("pro") never match, and a word that fits two apps is too unsure to use."""
    said = normalize(name)
    if not said:
        return None, False
    for nick, app in (nicknames or {}).items():
        if normalize(nick) == said:
            return app, True
    by_norm = {}
    for app in sorted(apps, key=lambda a: (a not in running, len(a))):
        by_norm.setdefault(normalize(app), app)
    if said in by_norm:
        return by_norm[said], True
    squashed = said.replace(" ", "")
    for norm, app in by_norm.items():  # "face time" -> FaceTime, "vs code" -> "VS Code"
        if norm.replace(" ", "") == squashed:
            return app, True
    if len(said) >= 3 and said not in GENERIC_WORDS:
        near = [app for norm, app in by_norm.items() if norm.startswith(said) and len(norm) - len(said) <= 2]
        if near:  # "photo" -> Photos
            return near[0], False
        words = {app for norm, app in by_norm.items() if said in norm.split() or (" " in said and said in norm)}
        if words:  # "chrome" -> Google Chrome; a distinctive word (5+ letters) is as good as the name
            share = lambda app: len(said) / len(normalize(app).replace(" ", ""))
            ranked = sorted(words, key=lambda app: (app not in running, -share(app)))
            if len(ranked) == 1 or share(ranked[0]) >= 1.3 * share(ranked[1]):
                return ranked[0], len(said) >= 5  # clearly the one ("Google Chrome" over "Chrome Remote Desktop")
            open_ = [app for app in ranked if app in running]
            if len(open_) == 1:  # two apps share it, one is open
                return open_[0], False
            return None, False  # too close to call: don't guess
        prefixed = [app for norm, app in by_norm.items() if norm.startswith(said)]
        if len(prefixed) == 1:  # "term" -> Terminal
            return prefixed[0], False
    close = difflib.get_close_matches(said, list(by_norm), n=2, cutoff=FUZZY_CUTOFF)
    if len(close) == 1 or (len(close) == 2 and difflib.SequenceMatcher(None, said, close[0]).ratio()
                           - difflib.SequenceMatcher(None, said, close[1]).ratio() > 0.08):
        return by_norm[close[0]], False
    return None, False


def match(name, apps, nicknames=None, running=()):
    """The app `name` refers to, or None if unsure (see match_scored)."""
    return match_scored(name, apps, nicknames, running)[0]


def bring_to_front(path, workspace=None):
    """Activate the app at `path`, launching it if it isn't running. True on success."""
    from AppKit import NSWorkspace, NSWorkspaceOpenConfiguration
    from Foundation import NSURL

    config = NSWorkspaceOpenConfiguration.configuration()
    config.setActivates_(True)
    (workspace or NSWorkspace.sharedWorkspace()).openApplicationAtURL_configuration_completionHandler_(
        NSURL.fileURLWithPath_(path), config, None)
    return True
