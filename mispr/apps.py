"""Voice app switcher: hold the switch key, say an app (or a nickname for one), let go, and
that app comes to the front. "Set nickname C to Chrome" teaches a nickname.

Everything here is local: apps are found on disk and in the running-apps list, never online.
"""

import difflib
import os
import sys
import re
import time
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
    said = fix_misheard(said)
    said = _number_words(said)
    said = re.sub(r"\b(tab|window)\s+(" + "|".join(_ONES) + r")\b", lambda m: f"{m[1]} {_ONES[m[2]]}", said)  # "tab nine"
    for pattern, make in _SOUND:
        m = pattern.match(said)
        if m and make(m) is not None:
            return make(m)
    m = _MENU.match(said) or _MENU_NAMED.match(said)
    if m:  # "click save", "press show sidebar", "file new window"
        return ("menu", m["item"])
    m = _WINDOW_N.match(said)
    if m:  # "window 2", "go to window one in chrome"
        return ("window", int(m["n"]), m["app"])
    m = _SPLIT_TAB.match(said)
    if m:  # "tabs side by side", "split tab"
        return ("split_tab", m["app"])
    m = _SITE_TAB.match(said)
    if m and not _SITE_TAB_RESERVED.match(m["site"]) and not _SITE_TAB_RESERVED_END.search(m["site"]):  # "github tab", "youtube tab 2"
        return ("site_tab", m["site"].strip(), int(m["n"]) if m["n"] else 1)
    m = _SHORTCUT.match(said)
    if m:  # "new tab", "close tab in chrome", "chrome reload", "tab 3"
        lead = r"^(?:(?:please|go|to|open|switch|then|and|a|the)\b\s*)+"
        app = next((n for n in (re.sub(lead, "", m[k] or "").strip() for k in ("app", "app2")) if n), None)
        name = m["cmd"]
        if re.fullmatch(r"(?:go to |switch to )?tab \d+", name):
            n = int(name.split()[-1])
            if not 1 <= n <= 9:
                return None
            name = "last tab" if n == 9 else f"tab {n}"  # ⌘9 is always the last tab
        return ("shortcut", SHORTCUT_ALIASES.get(name, name), _FILLER.sub("", app).strip() if app else None)
    m = _QUIT.match(said)
    if m:
        return ("quit", _FILLER.sub("", m["app"]).strip() if m["app"] else None)  # none named: the app you're in
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


# "github tab", "go to the youtube tab 2": a browser tab by its site. Words that already mean a
# tab command ("new tab", "close tab", "next tab", "tab 3") are never a site.
_SITE_TAB = re.compile(r"^(?:(?:go|switch|jump)\s+to\s+|open\s+|show\s+)?(?:the\s+|my\s+)?(?P<site>[a-z0-9][a-z0-9 .]*?)\s+tab(?:\s+(?:number\s+)?(?P<n>\d))?$")
_SITE_TAB_RESERVED = re.compile(r"^(?:new|close|closed|next|previous|prev|last|first|reopen|move|split|mute|unmute|this|that|a|the|"
                                r"open|go|switch|move|duplicate|pin|other|another|same|left|right|\d+)(?:\s|$)")

_SITE_TAB_RESERVED_END = re.compile(r"(?:^|\s)(?:new|close|closed|next|previous|prev|last|first|reopen|move|split|mute|"
                                    r"unmute|this|that|duplicate|pin|other|another|same)$")  # "chrome new tab"

_OPEN_FOLDER = re.compile(r"^(?:please\s+)?(?:open|show|go\s+to)\s+(?:the\s+|my\s+)?(?:folder\s+(?P<a>.+)|(?P<b>.+?)\s+folder)$")
_OPEN = re.compile(r"^(?:please\s+)?open\s+(?:the\s+|up\s+)?(?P<name>.+?)(?:\s+please)?$")


# --- Folders and files -------------------------------------------------------------------

SKIP_DIRS = {"Library", "node_modules", "__pycache__", "venv", ".venv", "site-packages", "build", "dist",
             "DerivedData", "Pods", "target"}


def name_key(name):
    """Folder/file names as spoken: "Mispr_Flow" / "voice-recordings" -> "misprflow" / "voicerecordings"."""
    return re.sub(r"[\W_]+", "", name.lower())


_SOUNDEX = {**dict.fromkeys("bfpv", "1"), **dict.fromkeys("cgjkqsxz", "2"), **dict.fromkeys("dt", "3"),
            "l": "4", **dict.fromkeys("mn", "5"), "r": "6"}


def sounds_like(name):
    """Soundex of the name with spaces and punctuation removed: "clawed", "claw to" and
    "Claude" are all C430, so a misheard name still finds the folder. Under 4 letters: None."""
    word = re.sub(r"[\W_]+", "", name.lower())
    if len(word) < 4:
        return None
    out, last = word[0].upper(), _SOUNDEX.get(word[0], "")
    for ch in word[1:]:
        code = _SOUNDEX.get(ch, "")
        if code and code != last:
            out += code
        if ch not in "hw":
            last = code
    return (out + "000")[:4]


def _hidden_or_skipped(path, root):
    rel = os.path.relpath(path, root)
    return any(part.startswith(".") or part in SKIP_DIRS or part.endswith((".app", ".photoslibrary", ".bundle"))
               for part in rel.split(os.sep))


def spotlight(root, name, files=True, run=None):
    """Like find_in, from the Spotlight index (instant, any depth): exact names first, then
    sound-alikes; the shallowest wins, folders first. None if Spotlight has nothing (or is off)."""
    import subprocess
    run = run or (lambda cmd: subprocess.run(cmd, capture_output=True, text=True, timeout=4).stdout)
    want, sound = name_key(name), sounds_like(name)
    words = [w for w in re.split(r"[\W_]+", name.lower()) if len(w) >= 2]
    if not want or not words:
        return None
    kind = "" if files else " && kMDItemContentType == 'public.folder'"
    queries = [f"kMDItemFSName == '*{max(words, key=len)}*'cd{kind}"]
    if sound:
        queries.append(f"kMDItemFSName == '{words[0][:2]}*'cd{kind}")  # sound-alikes start alike ("cla…")
    for query in queries:
        try:
            paths = [p for p in run(["mdfind", "-onlyin", str(root), query]).splitlines()
                     if p and not _hidden_or_skipped(p, root)]
        except Exception:
            return None
        def ok(p, exact):
            base = os.path.basename(p)
            stem = base if os.path.isdir(p) else os.path.splitext(base)[0]
            keys = (name_key(base), name_key(stem)) if exact else (sounds_like(base), sounds_like(stem))
            return (want if exact else sound) in keys
        for exact in (True, False):
            hits = [p for p in paths if ok(p, exact)]
            if hits:
                return min(hits, key=lambda p: (p.count(os.sep), not os.path.isdir(p), len(p)))
    return None


def find_in(root, name, files=True, max_depth=8, budget=1.5, clock=None):
    """The shallowest folder (or file, by name with or without its extension) under `root` whose
    name sounds like `name`, searching level by level so duplicates resolve to the highest one.
    Hidden folders, Library and build/dependency folders are skipped. If nothing has the name,
    the highest one that sounds like it ("clawed" -> Claude). None if not found in time."""
    import time as _time
    clock = clock or _time.monotonic
    want = name_key(name)
    if not want:
        return None
    deadline = clock() + budget
    level = [str(root)]
    sound = sounds_like(name)
    alike = None  # the first (highest) sound-alike, used only if no exact name turns up
    for _ in range(max_depth):
        found, below = [], []
        for folder in level:
            try:
                entries = sorted(os.scandir(folder), key=lambda e: e.name.lower())
            except PermissionError:  # Documents/Desktop/Downloads before "Files & Folders" is allowed
                print(f"mispr: no permission to look in {folder}", file=sys.stderr)
                continue
            except OSError:
                continue
            for e in entries:
                if e.name.startswith("."):
                    continue
                is_dir = e.is_dir(follow_symlinks=False)
                stem = e.name if is_dir else os.path.splitext(e.name)[0]
                if (is_dir or files) and want in (name_key(e.name), name_key(stem)):
                    found.append(e.path)
                elif alike is None and sound and (is_dir or files) and sound in (sounds_like(e.name), sounds_like(stem)):
                    alike = e.path
                if is_dir and e.name not in SKIP_DIRS and not e.name.endswith((".app", ".photoslibrary", ".bundle")):
                    below.append(e.path)
            if clock() > deadline:
                return found[0] if found else alike
        if found:
            return min(found, key=lambda p: (not os.path.isdir(p), len(p)))  # folders first
        level = below
        if not level:
            return alike
    return alike


TCC_DB = Path.home() / "Library" / "Application Support" / "com.apple.TCC" / "TCC.db"


def full_disk_access(probe=None):
    """Does Mispr Flow have Full Disk Access (so "open folder" can search everywhere, including
    Documents, Desktop and Downloads)? Reading this protected file says so without any prompt."""
    try:
        with open(probe or TCC_DB, "rb") as f:
            f.read(1)
        return True
    except PermissionError:
        return False
    except OSError:
        return True  # nothing there to protect: nothing is blocked


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
) + tuple((re.compile(pattern), (lambda action: lambda m: ("system", action))(action)) for pattern, action in (
    (r"^(?:take\s+(?:a\s+)?)?screen\s*shot(?:\s+(?:of\s+)?(?:the\s+)?(?:whole\s+|entire\s+|full\s+)?screen)?$", "screenshot"),
    (r"^(?:take\s+(?:a\s+)?)?screen\s*shot\s+(?:of\s+)?(?:an?\s+|the\s+)?(?:area|selection|part|portion|region)$", "screenshot_area"),
    (r"^(?:take\s+(?:a\s+)?)?screen\s*shot\s+(?:of\s+)?(?:the\s+|this\s+|a\s+)?window$", "screenshot_window"),
    (r"^(?:start\s+)?(?:a\s+)?(?:screen\s*recording|record(?:ing)?\s+(?:the\s+|my\s+)?screen|video\s+record(?:ing)?)$", "record_start"),
    (r"^(?:stop|end|finish)\s+(?:the\s+)?(?:screen\s*)?recording$", "record_stop"),
    (r"^(?:go\s+to\s+sleep|sleep(?:\s+now)?|put\s+(?:the\s+)?(?:computer|mac|it)\s+to\s+sleep)$", "sleep"),
    (r"^lock(?:\s+(?:the\s+|my\s+)?(?:screen|computer|mac))?$", "lock"),
    (r"^(?:log|sign)\s*(?:out|off)$", "log_out"),
    (r"^(?:restart|reboot)(?:\s+(?:the\s+|my\s+)?(?:computer|mac))?$", "restart"),
    (r"^(?:shut\s*down|power\s+off)(?:\s+(?:the\s+|my\s+)?(?:computer|mac))?$|^turn\s+off\s+(?:the\s+|my\s+)?(?:computer|mac)$", "shut_down"),
))

# Menu items by voice: "click save", "file new window", "edit find".
_MENU_NAMED = re.compile(r"^(?P<item>(?:file|edit|view|format|insert|tools|history|bookmarks|help)\s+.+)$")
_MENU = re.compile(r"^(?:click|press|choose|select|menu)\s+(?:on\s+)?(?:the\s+)?(?P<item>.+?)(?:\s+menu\s+item|\s+button)?$")

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


def _ax(el, name):
    import ApplicationServices as AS
    err, v = AS.AXUIElementCopyAttributeValue(el, name, None)
    return v if err == 0 else None


def _ax_find(el, test, depth=0):
    """The first element under `el` (depth-first, 12 levels) that passes `test`, or None."""
    if el is None or depth > 12:
        return None
    if test(el):
        return el
    for child in _ax(el, "AXChildren") or []:
        hit = _ax_find(child, test, depth + 1)
        if hit is not None:
            return hit
    return None


def _tab_menu(pid):
    """Open the selected tab's own menu (Chrome-style browsers). Returns (tab, app element) or None."""
    import ApplicationServices as AS
    tab = _ax_find(_window(pid), lambda e: _ax(e, "AXRole") == "AXRadioButton" and _ax(e, "AXValue") == 1
                   and _ax(_ax(e, "AXParent"), "AXRole") == "AXTabGroup")
    if tab is None or AS.AXUIElementPerformAction(tab, "AXShowMenu") != 0:
        return None
    return tab, AS.AXUIElementCreateApplication(pid)


def _menu_item(root, test):
    return _ax_find(root, lambda e: _ax(e, "AXRole") == "AXMenuItem" and test(str(_ax(e, "AXTitle") or "").lower()))


def mute_tab(pid, mute=True):
    """Chrome-style browsers: press "Mute site" (or "Unmute site") in the selected tab's menu.
    True if done, None if it was already that way (the other item is there), False if no tab menu."""
    import ApplicationServices as AS
    opened = _tab_menu(pid)
    if opened is None:
        return False
    tab, root = opened
    wanted = ("mute site", "mute tab") if mute else ("unmute site", "unmute tab")
    other = ("unmute site", "unmute tab") if mute else ("mute site", "mute tab")
    item = _menu_item(root, lambda t: t in wanted)
    if item is not None:
        return AS.AXUIElementPerformAction(item, "AXPress") == 0
    if _menu_item(root, lambda t: t in other) is not None:
        AS.AXUIElementPerformAction(tab, "AXCancel")  # close the menu again
        return None
    AS.AXUIElementPerformAction(tab, "AXCancel")
    return False


def windows(pid):
    """The app's normal, visible windows, numbered for "window 1, 2…": left to right, then top
    to bottom (so with two windows side by side, the left one is window 1)."""
    from AppKit import NSPointFromCGPoint  # noqa: F401  (keeps PyObjC's CG value types loaded)
    import ApplicationServices as AS
    found = []
    for win in _ax(AS.AXUIElementCreateApplication(pid), "AXWindows") or []:
        if _ax(win, "AXSubrole") not in (None, "AXStandardWindow") or _ax(win, "AXMinimized"):
            continue
        pos = _ax(win, "AXPosition")
        ok, point = AS.AXValueGetValue(pos, AS.kAXValueCGPointType, None) if pos is not None else (False, None)
        x, y = (point.x, point.y) if ok else (0, 0)
        found.append((round(x / 40), round(y / 40), win))  # within 40 px counts as the same column/row
    return [win for _, _, win in sorted(found, key=lambda t: (t[0], t[1]))]


def focus_window(pid, number):
    """Bring the app's window `number` (1-based, see windows()) to the front. True if it exists."""
    import ApplicationServices as AS
    wins = windows(pid)
    if not 1 <= number <= len(wins):
        return False
    win = wins[number - 1]
    AS.AXUIElementSetAttributeValue(win, "AXMain", True)
    return AS.AXUIElementPerformAction(win, "AXRaise") == 0


def tile_front_two(pid, screen):
    """Put the app's two front-most windows side by side: the one before on the left, the newest
    on the right (after "move tab to new window"). True if there were two."""
    import ApplicationServices as AS
    wins = [w for w in (_ax(AS.AXUIElementCreateApplication(pid), "AXWindows") or [])
            if _ax(w, "AXSubrole") in (None, "AXStandardWindow") and not _ax(w, "AXMinimized")]
    if len(wins) < 2:
        return False
    left, right = layout(screen, "beside")
    for win, (x, y, w, h) in ((wins[1], left), (wins[0], right)):
        size = AS.AXValueCreate(AS.kAXValueCGSizeType, (w, h))
        AS.AXUIElementSetAttributeValue(win, "AXSize", size)
        AS.AXUIElementSetAttributeValue(win, "AXPosition", AS.AXValueCreate(AS.kAXValueCGPointType, (x, y)))
        AS.AXUIElementSetAttributeValue(win, "AXSize", size)
    return True


def split_tab(pid):
    """Put the current tab side by side with another: Chrome's own split view if it has it
    ("split" returned); otherwise move the tab to a new window and tile the two windows
    ("windows"). False if the app has no tab menu."""
    import ApplicationServices as AS
    opened = _tab_menu(pid)
    if opened is None:
        return False
    tab, root = opened
    item = _menu_item(root, lambda t: "split view" in t or "side by side" in t)
    if item is not None:
        return "split" if AS.AXUIElementPerformAction(item, "AXPress") == 0 else False
    item = _menu_item(root, lambda t: t.startswith("move tab to new window") or t == "move to new window")
    if item is None or AS.AXUIElementPerformAction(item, "AXPress") != 0:
        AS.AXUIElementPerformAction(tab, "AXCancel")
        return False
    return "windows"


# Keyboard shortcuts most Mac apps (and every browser) share: name -> (key code, modifiers).
_KEY = {"q": 12, "space": 49, "up": 126, "down": 125, "pageup": 116, "pagedown": 121, "`": 50, "t": 17, "w": 13, "n": 45, "r": 15, "l": 37, "f": 3, "d": 2, "[": 33, "]": 30, "tab": 48,
        "0": 29, "=": 24, "-": 27, "1": 18, "2": 19, "3": 20, "4": 21, "5": 23, "6": 22, "7": 26, "8": 28, "9": 25}
SHORTCUTS = {
    "new tab": ("t", "cmd"), "close tab": ("w", "cmd"), "reopen tab": ("t", "cmd shift"),
    "next tab": ("tab", "ctrl"), "previous tab": ("tab", "ctrl shift"),
    "move tab left": ("pageup", "ctrl shift"), "move tab right": ("pagedown", "ctrl shift"),
    "next window": ("`", "cmd"), "previous window": ("`", "cmd shift"),
    "new window": ("n", "cmd"), "new private window": ("n", "cmd shift"), "close window": ("w", "cmd shift"),
    "reload": ("r", "cmd"), "back": ("[", "cmd"), "forward": ("]", "cmd"), "address bar": ("l", "cmd"),
    "find": ("f", "cmd"), "bookmark": ("d", "cmd"), "zoom in": ("=", "cmd"), "zoom out": ("-", "cmd"),
    "actual size": ("0", "cmd"), "full screen": ("f", "ctrl cmd"), "last tab": ("9", "cmd"),
    "top": ("up", "cmd"), "bottom": ("down", "cmd"),
    **{f"tab {n}": (str(n), "cmd") for n in range(1, 9)},
}
SHORTCUT_ALIASES = {
    "tab left": "previous tab", "left tab": "previous tab", "tab to the left": "previous tab",
    "tab right": "next tab", "right tab": "next tab", "tab to the right": "next tab",
    "move this tab left": "move tab left", "move the tab left": "move tab left",
    "move this tab right": "move tab right", "move the tab right": "move tab right",
    "other window": "next window", "switch window": "next window", "last window": "previous window",
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
_SHORTCUT = re.compile(rf"^(?:please\s+)?(?:(?P<app>.+?)\s+)??(?P<cmd>{_SHORTCUT_WORDS}|(?:go to |switch to )?tab \d+)"
                       rf"(?:\s+(?:in|on|for)\s+(?P<app2>.+))?$")
_WINDOW_N = re.compile(r"^(?:please\s+)?(?:(?:go|switch)\s+to\s+)?(?:the\s+)?window\s+(?:number\s+)?(?P<n>\d{1,2})"
                       r"(?:\s+(?:in|on|of)\s+(?P<app>.+))?$")
_SPLIT_TAB = re.compile(r"^(?:please\s+)?(?:put\s+)?(?:(?:the|these|my)\s+)?(?:tabs?\s+side\s+by\s+side|side\s+by\s+side\s+tabs?|"
                        r"split\s+(?:the\s+|this\s+)?(?:tab|tabs|view|screen\s+tabs)|split\s+view)"
                        r"(?:\s+(?:in|on)\s+(?P<app>.+))?$")
_QUIT = re.compile(r"^(?:please\s+)?(?:quit|exit)(?:\s+(?:this\s+app|the\s+app|app|it))?(?:\s+(?P<app>.+))?$")


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


SHORTCUTS.update({"screenshot": ("3", "cmd shift"), "screenshot area": ("4", "cmd shift"),
                  "screen capture tools": ("5", "cmd shift"), "lock screen": ("q", "ctrl cmd")})

# What each system command does, as shown afterwards.
SYSTEM_DONE = {"screenshot": "Screenshot saved", "screenshot_area": "Drag to choose the area",
               "screenshot_window": "Click a window to capture it", "record_start": "Recording the screen · say “stop recording”",
               "record_stop": "Screen recording saved", "sleep": "Going to sleep", "lock": "Locked",
               "log_out": "Log out?", "restart": "Restart?", "shut_down": "Shut down?"}
# macOS's own confirm dialogs for these (never done without asking): log out, restart, shut down.
_POWER_EVENTS = {"log_out": "aevtlogo", "restart": "aevtrrst", "shut_down": "aevtrsdn"}


def screenshot_folder(run=None):
    """Where macOS saves screenshots (Screenshot app > Options), else the Desktop."""
    import subprocess
    run = run or (lambda cmd: subprocess.run(cmd, capture_output=True, text=True, timeout=3).stdout.strip())
    try:
        where = run(["defaults", "read", "com.apple.screencapture", "location"])
    except Exception:
        where = ""
    path = Path(where).expanduser() if where else Path.home() / "Desktop"
    return path if path.is_dir() else Path.home() / "Desktop"


class ScreenRecorder:
    """"screen recording" starts macOS's screencapture in video mode (needs Screen Recording
    permission); "stop recording" ends it and the movie lands where screenshots go."""

    def __init__(self, popen=None, folder=screenshot_folder, clock=time.time):
        import subprocess
        self.popen, self.folder, self.clock = popen or subprocess.Popen, folder, clock
        self.process, self.path = None, None

    @property
    def recording(self):
        return self.process is not None and self.process.poll() is None

    def start(self):
        """True if recording started (False: already recording, or screencapture refused)."""
        if self.recording:
            return False
        stamp = time.strftime("%Y-%m-%d at %H.%M.%S", time.localtime(self.clock()))
        self.path = self.folder() / f"Screen Recording {stamp}.mov"
        self.process = self.popen(["screencapture", "-v", "-k", str(self.path)])
        return True

    def stop(self):
        """The saved movie's path, or None if nothing was recording."""
        import signal
        if not self.recording:
            return None
        self.process.send_signal(signal.SIGINT)  # like ⌃C: screencapture finishes the file
        try:
            self.process.wait(timeout=5)
        except Exception:
            self.process.kill()
        self.process = None
        return self.path


def system_action(action, run=None, press=None):
    """Do a system command: screenshots (macOS's own shortcuts), sleep, lock, or ask macOS to
    log out / restart / shut down (it shows its usual confirmation first)."""
    import subprocess
    run = run or (lambda cmd: subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout.strip())
    press = press or press_shortcut
    if action == "screenshot":
        press("screenshot")
    elif action == "screenshot_area":
        press("screenshot area")
    elif action == "screenshot_window":
        press("screenshot area")
        time.sleep(0.3)
        press_key("space")  # ⌘⇧4 then space: pick a window
    elif action == "sleep":
        run(["pmset", "sleepnow"])
    elif action == "lock":
        press("lock screen")
    elif action in _POWER_EVENTS:
        run(["osascript", "-e", f'tell application "loginwindow" to «event {_POWER_EVENTS[action]}»'])
    else:
        return False
    return True


def press_key(key, post=None):
    """Press one key with no modifiers."""
    import Quartz
    post = post or (lambda event: Quartz.CGEventPost(Quartz.kCGSessionEventTap, event))
    source = Quartz.CGEventSourceCreate(Quartz.kCGEventSourceStateHIDSystemState)
    for down in (True, False):
        post(Quartz.CGEventCreateKeyboardEvent(source, _KEY[key], down))


def _menu_title(text):
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", str(text or "").lower().replace("…", "")).split())


def menu_items(pid, limit=1500):
    """[(menu, item title, element)] of the app's menu bar: File, Edit, View, … and one level of
    submenus. Apple menu skipped. At most `limit` items (History and Bookmarks can be huge)."""
    import ApplicationServices as AS
    bar = _ax(AS.AXUIElementCreateApplication(pid), "AXMenuBar")
    out = []

    def walk(menu, top, depth):
        for item in _ax(menu, "AXChildren") or []:
            if len(out) >= limit:
                return
            title = _menu_title(_ax(item, "AXTitle"))
            if title and _ax(item, "AXRole") == "AXMenuItem":
                out.append((top, title, item))
            if depth < 2:
                for sub in _ax(item, "AXChildren") or []:
                    walk(sub, top, depth + 1)

    for top_item in (_ax(bar, "AXChildren") or [])[1:]:  # [0] is the Apple menu
        top = _menu_title(_ax(top_item, "AXTitle"))
        for menu in _ax(top_item, "AXChildren") or []:
            walk(menu, top, 0)
    return out


# Menu items never pressed by voice: they delete for good (a misheard word must not do that).
MENU_BLOCKED = re.compile(r"\b(?:empty\s+(?:the\s+)?trash|empty\s+bin|delete\s+immediately|erase|secure\s+empty|"
                          r"force\s+quit|delete\s+all|clear\s+(?:all\s+)?history)\b")


def find_menu_item(phrase, items):
    """The menu item for what was said: its title ("save as", "show sidebar"), menu plus title
    ("file new window"), or the title without the app's name ("new window" for "New Finder
    Window"). Items that delete for good (Empty Trash, Erase…) are never matched."""
    said = _menu_title(phrase)
    if not said or MENU_BLOCKED.search(said):
        return None
    app = items[0][0] if items else ""
    for loose in (False, True):
        for top, title, element in items:
            if MENU_BLOCKED.search(title):
                continue
            name = " ".join(w for w in title.split() if w != app) if loose else title
            if said == name or said == f"{top} {name}":
                return top, title, element
    return None


def press_menu_item(element):
    import ApplicationServices as AS
    return AS.AXUIElementPerformAction(element, "AXPress") == 0


def quit_app(pid):
    """Ask the app to quit normally (it can still ask about unsaved work). True if asked."""
    from AppKit import NSRunningApplication
    app = NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
    return bool(app and app.terminate())


# Whisper hears short commands without context: "tab left" came out as "Top left." every time.
# Fix the word "tab" only right before something a tab command takes, so "top" elsewhere stays.
_TAB_NEXT = r"(?:left|right|over|\d+|one|two|three|four|five|six|seven|eight|nine|side\s+by\s+side)\b"
_MISHEARD = [
    (re.compile(r"\b(?:top|tap|tub|tob|tad|tabb|tam)\s+(?=" + _TAB_NEXT + ")"), "tab "),
    (re.compile(r"\b(next|previous|new|close|reopen|last|move|split|mute|unmute)\s+(?:top|tap|tub|tob)\b"), r"\1 tab"),
    (re.compile(r"\btab(left|right)\b"), r"tab \1"),
    (re.compile(r"(?<!reopen )(?<!undo )\b(?:closed|closes|clothes)\s+tabs?\b"), "close tab"),  # "Closed tab." (not "reopen closed tab")
    (re.compile(r"^tab\s+(close|closed)$"), "close tab"),  # "Tab, close."
]


def fix_misheard(said):
    """Common mishearings of short commands: "top left" -> "tab left", "close top" -> "close tab"."""
    for pattern, fix in _MISHEARD:
        said = pattern.sub(fix, said)
    return said


# What Whisper should expect when the switch key is held (an initial prompt biases it toward these).
COMMAND_HINT = ("Voice commands: tab left, tab right, tab 3, new tab, close tab, move tab left, window 2, "
                "next window, tabs side by side, GitHub tab, YouTube tab 2, screenshot, stop recording, lock screen, open folder, scroll down, volume up, pause, mute mic, quit.")


def command_prompt(nicknames=None, names=()):
    """The hint for a voice command, with the user's nicknames and some app names."""
    extra = list(nicknames or {}) + list(names)[:20]
    return COMMAND_HINT + (" " + ", ".join(extra) + "." if extra else "")


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


def running_bundle_ids():
    """Bundle ids of the running Dock apps."""
    from AppKit import NSApplicationActivationPolicyRegular, NSWorkspace

    return [str(app.bundleIdentifier()) for app in NSWorkspace.sharedWorkspace().runningApplications()
            if app.activationPolicy() == NSApplicationActivationPolicyRegular and app.bundleIdentifier()]


def bundle_id(path):
    """The bundle id of the app at `path`, or None."""
    from AppKit import NSBundle

    bundle = NSBundle.bundleWithPath_(str(path)) if path else None
    return str(bundle.bundleIdentifier()) if bundle is not None and bundle.bundleIdentifier() else None


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


# --- Browser tabs by site --------------------------------------------------------------------

# Browsers whose tabs AppleScript can list and select (Chromium-based, and Safari).
CHROMIUM_SCRIPTABLE = {"com.google.Chrome": "Google Chrome", "com.google.Chrome.canary": "Google Chrome Canary",
                       "com.brave.Browser": "Brave Browser", "com.microsoft.edgemac": "Microsoft Edge",
                       "company.thebrowser.Browser": "Arc", "com.vivaldi.Vivaldi": "Vivaldi",
                       "org.chromium.Chromium": "Chromium", "com.operasoftware.Opera": "Opera"}
SAFARI_SCRIPTABLE = {"com.apple.Safari": "Safari", "com.apple.SafariTechnologyPreview": "Safari Technology Preview"}

_LIST_TABS = {
    "chromium": ('tell application "{app}"\nset out to ""\nrepeat with w from 1 to count windows\n'
                 'repeat with t from 1 to count tabs of window w\nset out to out & w & tab & t & tab & '
                 '(URL of tab t of window w) & tab & (title of tab t of window w) & linefeed\nend repeat\n'
                 'end repeat\nreturn out\nend tell'),
    "safari": ('tell application "{app}"\nset out to ""\nrepeat with w from 1 to count windows\n'
               'repeat with t from 1 to count tabs of window w\nset out to out & w & tab & t & tab & '
               '(URL of tab t of window w) & tab & (name of tab t of window w) & linefeed\nend repeat\n'
               'end repeat\nreturn out\nend tell'),
}
_SELECT_TAB = {
    "chromium": 'tell application "{app}"\nset active tab index of window {w} to {t}\nset index of window {w} to 1\nactivate\nend tell',
    "safari": 'tell application "{app}"\nset current tab of window {w} to tab {t} of window {w}\nset index of window {w} to 1\nactivate\nend tell',
}


def scriptable_browser(bundle_id):
    """(family, app name) for a browser whose tabs can be listed, else None."""
    if bundle_id in CHROMIUM_SCRIPTABLE:
        return "chromium", CHROMIUM_SCRIPTABLE[bundle_id]
    if bundle_id in SAFARI_SCRIPTABLE:
        return "safari", SAFARI_SCRIPTABLE[bundle_id]
    return None


def list_tabs(family, app, run=None):
    """[(window, tab, url, title)], front window first, tabs left to right."""
    out = _osascript(_LIST_TABS[family].format(app=app), run) or ""
    tabs = []
    for line in out.splitlines():
        parts = line.split("\t", 3)
        if len(parts) == 4 and parts[0].isdigit() and parts[1].isdigit():
            tabs.append((int(parts[0]), int(parts[1]), parts[2], parts[3]))
    return tabs


def _host(url):
    m = re.match(r"^[a-z]+://(?:www\d?\.|m\.)?([^/:?#]+)", url or "", re.I)
    return m[1].lower() if m else ""


# Sites people call by a name that isn't in the address.
SITE_ALIASES = {"gmail": "mail google", "google mail": "mail google", "google drive": "drive google",
                "google calendar": "calendar google", "google sheets": "docs google", "google slides": "docs google",
                "twitter": "x", "chat gpt": "chatgpt", "claude": "claude", "linked in": "linkedin"}


def site_tabs(site, tabs):
    """The tabs whose site is `site` ("github", "you tube", "google docs"), in order: the web
    address first (its name, then a sound-alike), else the page title."""
    site = SITE_ALIASES.get(site.lower().strip(), site)
    want = re.sub(r"[^a-z0-9]", "", site.lower())
    if not want:
        return []
    by_host, by_sound, by_title = [], [], []
    for entry in tabs:
        host = _host(entry[2])
        name = re.sub(r"[^a-z0-9]", "", host.rsplit(".", 1)[0]) if host else ""  # "docs.google" -> "docsgoogle"
        labels = [re.sub(r"[^a-z0-9]", "", part) for part in host.split(".")[:-1]] + [name]
        words = set(re.findall(r"[a-z0-9]+", site.lower()))
        if want in labels or (len(want) >= 4 and want in name) or (len(words) > 1 and words <= set(labels)):
            by_host.append(entry)
        elif sounds_like(want) and any(sounds_like(label) == sounds_like(want) for label in labels):
            by_sound.append(entry)
        elif len(want) >= 3 and want in re.sub(r"[^a-z0-9]", "", (entry[3] or "").lower()):
            by_title.append(entry)
    return by_host or by_sound or by_title


def select_tab(family, app, window, tab, run=None):
    _osascript(_SELECT_TAB[family].format(app=app, w=window, t=tab), run)
