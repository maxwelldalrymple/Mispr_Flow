"""More of your Mac by voice: keys and shortcuts, typing and editing text, window halves and
desktops, system switches (dark mode, Wi-Fi, brightness, sound output), web searches, Shortcuts,
and repeating the last command.

`parse(text)` turns what was said into a command tuple (or None); the widget carries it out with
the functions here. Everything runs on this Mac: macOS's own tools (osascript, networksetup,
shortcuts, open) or synthetic key and mouse events.
"""

import re
import subprocess
import time
from urllib.parse import quote_plus

# --- Keys -------------------------------------------------------------------------------------

KEYCODES = {
    "a": 0, "s": 1, "d": 2, "f": 3, "h": 4, "g": 5, "z": 6, "x": 7, "c": 8, "v": 9, "b": 11, "q": 12, "w": 13,
    "e": 14, "r": 15, "y": 16, "t": 17, "1": 18, "2": 19, "3": 20, "4": 21, "6": 22, "5": 23, "=": 24, "9": 25,
    "7": 26, "-": 27, "8": 28, "0": 29, "]": 30, "o": 31, "u": 32, "[": 33, "i": 34, "p": 35, "return": 36,
    "l": 37, "j": 38, "'": 39, "k": 40, ";": 41, "\\": 42, ",": 43, "/": 44, "n": 45, "m": 46, ".": 47,
    "tab": 48, "space": 49, "`": 50, "delete": 51, "escape": 53, "f5": 96, "f6": 97, "f7": 98, "f3": 99,
    "f8": 100, "f9": 101, "f11": 103, "f10": 109, "f12": 111, "home": 115, "pageup": 116, "forwarddelete": 117,
    "f4": 118, "end": 119, "f2": 120, "pagedown": 121, "f1": 122, "left": 123, "right": 124, "down": 125, "up": 126,
}
# Spoken names for keys.
KEY_WORDS = {
    "enter": "return", "return": "return", "escape": "escape", "esc": "escape", "tab": "tab", "space": "space",
    "spacebar": "space", "space bar": "space", "delete": "delete", "backspace": "delete", "back space": "delete",
    "forward delete": "forwarddelete", "up": "up", "down": "down", "left": "left", "right": "right",
    "up arrow": "up", "down arrow": "down", "left arrow": "left", "right arrow": "right", "home": "home", "end": "end",
    "page up": "pageup", "page down": "pagedown", "comma": ",", "period": ".", "dot": ".", "slash": "/",
    "minus": "-", "dash": "-", "equals": "=", "plus": "=", "semicolon": ";", "quote": "'", "backtick": "`",
    **{f"f{i}": f"f{i}" for i in range(1, 13)}, **{c: c for c in "abcdefghijklmnopqrstuvwxyz0123456789"},
    **dict(zip("zero one two three four five six seven eight nine".split(), "0123456789")),
}
MOD_WORDS = {"command": "cmd", "cmd": "cmd", "commands": "cmd", "shift": "shift", "option": "option", "alt": "option",
             "control": "ctrl", "ctrl": "ctrl", "ctl": "ctrl"}

# Edits that work in every app (no menu needed).
EDIT_KEYS = {
    "select all": ("a", "cmd"), "copy": ("c", "cmd"), "copy that": ("c", "cmd"), "paste": ("v", "cmd"),
    "paste that": ("v", "cmd"), "cut": ("x", "cmd"), "cut that": ("x", "cmd"), "undo": ("z", "cmd"),
    "undo that": ("z", "cmd"), "redo": ("z", "cmd shift"), "redo that": ("z", "cmd shift"), "save": ("s", "cmd"),
    "save it": ("s", "cmd"), "new line": ("return", "shift"), "next line": ("return", "shift"),
    "go to end of line": ("right", "cmd"), "end of line": ("right", "cmd"), "go to start of line": ("left", "cmd"),
    "start of line": ("left", "cmd"), "beginning of line": ("left", "cmd"), "go to the top": ("up", "cmd"),
    "go to the bottom": ("down", "cmd"), "end of document": ("down", "cmd"), "start of document": ("up", "cmd"),
    "next word": ("right", "option"), "previous word": ("left", "option"), "delete last word": ("delete", "option"),
    "delete word": ("delete", "option"), "delete line": ("delete", "cmd"), "select line": ("right", "cmd shift"),
    "select last word": ("left", "option shift"), "select next word": ("right", "option shift"),
    "select to end of line": ("right", "cmd shift"), "select to start of line": ("left", "cmd shift"),
    "print": ("p", "cmd"),
}


def parse_keys(words):
    """"command shift t" -> [("t", "cmd shift")]; "enter" -> [("return", "")]; None if not keys."""
    mods, rest = [], words.split()
    while rest and rest[0] in MOD_WORDS:
        mods.append(MOD_WORDS[rest.pop(0)])
    key = " ".join(rest)
    if key in KEY_WORDS:
        return [(KEY_WORDS[key], " ".join(dict.fromkeys(mods)))]
    return None


def press(key, mods="", times=1, post=None):
    """Press `key` (KEYCODES name) with modifiers ("cmd shift"), `times` times."""
    import Quartz
    flags = 0
    for m in mods.split():
        flags |= {"cmd": Quartz.kCGEventFlagMaskCommand, "shift": Quartz.kCGEventFlagMaskShift,
                  "ctrl": Quartz.kCGEventFlagMaskControl, "option": Quartz.kCGEventFlagMaskAlternate}[m]
    if key in ("up", "down", "left", "right", "home", "end", "pageup", "pagedown", "forwarddelete") or key.startswith("f"):
        flags |= Quartz.kCGEventFlagMaskSecondaryFn if key.startswith("f") and len(key) > 1 else 0
    post = post or (lambda event: Quartz.CGEventPost(Quartz.kCGSessionEventTap, event))
    source = Quartz.CGEventSourceCreate(Quartz.kCGEventSourceStateHIDSystemState)
    for _ in range(max(1, min(times, 200))):
        for down in (True, False):
            event = Quartz.CGEventCreateKeyboardEvent(source, KEYCODES[key], down)
            Quartz.CGEventSetFlags(event, flags)
            post(event)


# --- Windows and desktops ---------------------------------------------------------------------

def snap_frame(screen, where):
    """The frame (x, y, w, h, top-left origin) for "left half", "top half", "center"… of `screen`."""
    x, y, w, h = screen
    return {
        "left": (x, y, w / 2, h), "right": (x + w / 2, y, w / 2, h),
        "top": (x, y, w, h / 2), "bottom": (x, y + h / 2, w, h / 2),
        "left third": (x, y, w / 3, h), "middle third": (x + w / 3, y, w / 3, h), "right third": (x + 2 * w / 3, y, w / 3, h),
        "left two thirds": (x, y, 2 * w / 3, h), "right two thirds": (x + w / 3, y, 2 * w / 3, h),
        "top left": (x, y, w / 2, h / 2), "top right": (x + w / 2, y, w / 2, h / 2),
        "bottom left": (x, y + h / 2, w / 2, h / 2), "bottom right": (x + w / 2, y + h / 2, w / 2, h / 2),
        "center": (x + w * 0.15, y + h * 0.1, w * 0.7, h * 0.8), "maximize": (x, y, w, h),
    }[where]


def screens():
    """Every display's usable area (no menu bar or Dock), top-left origin, main display first."""
    from AppKit import NSScreen
    all_screens = NSScreen.screens()
    main_height = all_screens[0].frame().size.height
    out = []
    for s in all_screens:
        f = s.visibleFrame()
        out.append((f.origin.x, main_height - f.origin.y - f.size.height, f.size.width, f.size.height))
    return out


def mission_control(view="all", run=None):
    """Mission Control ("all"), the desktop ("desktop"), or the front app's windows ("app")."""
    run = run or _run
    run(["open", "-a", "Mission Control", "--args", {"all": "", "desktop": "1", "app": "2"}[view]] if view != "all"
        else ["open", "-a", "Mission Control"])


def open_app(name, run=None):
    (run or _run)(["open", "-a", name])


# --- System switches --------------------------------------------------------------------------

def _run(cmd, timeout=5):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout.strip()
    except Exception:
        return ""


def dark_mode(on, run=None):
    """on True/False, or None to flip. Asks once for permission to control System Events."""
    run = run or _run
    value = "not dark mode" if on is None else ("true" if on else "false")
    run(["osascript", "-e", f'tell application "System Events" to tell appearance preferences to set dark mode to {value}'])


def wifi_device(run=None):
    run = run or _run
    out = run(["networksetup", "-listallhardwareports"])
    m = re.search(r"Hardware Port: Wi-Fi\nDevice: (\S+)", out)
    return m[1] if m else "en0"


def wifi(on, run=None):
    run = run or _run
    device = wifi_device(run)
    if on is None:
        on = "On" not in run(["networksetup", "-getairportpower", device])
    run(["networksetup", "-setairportpower", device, "on" if on else "off"])
    return on


BRIGHTNESS_KEYS = {"up": 2, "down": 3}  # NX_KEYTYPE_BRIGHTNESS_UP / _DOWN


def brightness(direction, steps=2, post=None):
    """Press the brightness key like the keyboard's own (built-in display)."""
    import Quartz
    from AppKit import NSEvent
    post = post or (lambda event: Quartz.CGEventPost(Quartz.kCGHIDEventTap, event))
    for _ in range(steps):
        for state in (0xA, 0xB):
            event = NSEvent.otherEventWithType_location_modifierFlags_timestamp_windowNumber_context_subtype_data1_data2_(
                14, (0, 0), state << 8, 0, 0, None, 8, (BRIGHTNESS_KEYS[direction] << 16) | (state << 8), -1)
            post(event.CGEvent())


def output_devices():
    """{name: id} of sound outputs (CoreAudio)."""
    import CoreAudio as CA
    import objc  # noqa: F401
    devices = {}
    try:
        address = CA.AudioObjectPropertyAddress(CA.kAudioHardwarePropertyDevices, CA.kAudioObjectPropertyScopeGlobal,
                                                CA.kAudioObjectPropertyElementMain)
        err, size = CA.AudioObjectGetPropertyDataSize(CA.kAudioObjectSystemObject, address, 0, None, None)
        err, size, ids = CA.AudioObjectGetPropertyData(CA.kAudioObjectSystemObject, address, 0, None, size, None)
        for device in ids or []:
            out = CA.AudioObjectPropertyAddress(CA.kAudioDevicePropertyStreams, CA.kAudioObjectPropertyScopeOutput,
                                                CA.kAudioObjectPropertyElementMain)
            err, streams = CA.AudioObjectGetPropertyDataSize(device, out, 0, None, None)
            if err or not streams:
                continue
            name_addr = CA.AudioObjectPropertyAddress(CA.kAudioObjectPropertyName, CA.kAudioObjectPropertyScopeGlobal,
                                                      CA.kAudioObjectPropertyElementMain)
            err, _, name = CA.AudioObjectGetPropertyData(device, name_addr, 0, None, 8, None)
            if not err and name:
                devices[str(name)] = device
    except Exception:
        return {}
    return devices


def use_output(spoken, devices=None, setter=None):
    """Switch the sound output to the device whose name is closest to `spoken` ("AirPods").
    Returns its name, or None."""
    import difflib
    devices = devices if devices is not None else output_devices()
    if not devices:
        return None
    said = spoken.lower()
    named = [d for d in devices if said in d.lower()] or difflib.get_close_matches(spoken, list(devices), n=1, cutoff=0.4)
    if not named:
        return None
    name = named[0]
    (setter or _set_default_output)(devices[name])
    return name


def _set_default_output(device):
    import CoreAudio as CA
    address = CA.AudioObjectPropertyAddress(CA.kAudioHardwarePropertyDefaultOutputDevice,
                                            CA.kAudioObjectPropertyScopeGlobal, CA.kAudioObjectPropertyElementMain)
    CA.AudioObjectSetPropertyData(CA.kAudioObjectSystemObject, address, 0, None, 4, device)


# --- The web ---------------------------------------------------------------------------------

SEARCH_URLS = {
    "google": "https://www.google.com/search?q={}", "youtube": "https://www.youtube.com/results?search_query={}",
    "amazon": "https://www.amazon.com/s?k={}", "wikipedia": "https://en.wikipedia.org/w/index.php?search={}",
    "github": "https://github.com/search?q={}", "reddit": "https://www.reddit.com/search/?q={}",
    "maps": "https://www.google.com/maps/search/{}", "images": "https://www.google.com/search?tbm=isch&q={}",
    "duckduckgo": "https://duckduckgo.com/?q={}", "bing": "https://www.bing.com/search?q={}",
}


def search_url(engine, query):
    return SEARCH_URLS[engine].format(quote_plus(query))


def open_url(url, app=None, run=None):
    """Open a web address in `app` (the browser in front) or the default browser."""
    run = run or _run
    run(["open", "-a", app, url] if app else ["open", url])


# --- Shortcuts (the Shortcuts app) ---------------------------------------------------------------

def shortcut_names(run=None):
    return [n for n in (run or _run)(["shortcuts", "list"], timeout=10).splitlines() if n.strip()]


def run_shortcut(spoken, names=None, run=None):
    """Run the Shortcut whose name is closest to `spoken`. Returns its name, or None."""
    import difflib
    run = run or _run
    names = names if names is not None else shortcut_names(run)
    lowered = {n.lower(): n for n in names}
    said = spoken.lower().strip()
    name = lowered.get(said) or next((n for k, n in lowered.items() if said in k), None)
    if name is None:
        close = difflib.get_close_matches(said, list(lowered), n=1, cutoff=0.6)
        name = lowered[close[0]] if close else None
    if name:
        subprocess.Popen(["shortcuts", "run", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) if run is _run \
            else run(["shortcuts", "run", name])
    return name


# --- What was said ----------------------------------------------------------------------------

_TYPE = re.compile(r"^\s*(?:type|write|enter text)\s+(?P<text>.+?)\s*$", re.I | re.S)
_PRESS = re.compile(r"^(?:press|hit|push|key)\s+(?P<keys>.+?)(?:\s+(?P<n>\d+)\s+times?)?$")
_ARROWS = re.compile(r"^(?:arrow\s+)?(?P<key>up|down|left|right)(?:\s+arrow)?\s+(?P<n>\d+|two|three|four|five|six|seven|eight|nine|ten)(?:\s+times)?$")
_COUNT = dict(zip("two three four five six seven eight nine ten".split(), range(2, 11)))
_SNAP_PREFIX = r"(?:move\s+(?:it\s+|this\s+|the\s+window\s+)?(?:to\s+)?(?:the\s+)?|snap\s+(?:it\s+)?(?:to\s+)?(?:the\s+)?|window\s+)"
_SNAP = re.compile(rf"^{_SNAP_PREFIX}?(?P<where>left half|right half|top half|bottom half|left third|middle third|right third|"
                   r"left two thirds|right two thirds|center|left side|right side)(?:\s+(?:of\s+)?(?:the\s+)?screen)?$|"
                   # Corners need "corner" or "move to": plain "top left" is how Whisper hears "tab left".
                   rf"^(?:{_SNAP_PREFIX}(?P<corner1>top left|top right|bottom left|bottom right)(?:\s+corner)?|"
                   r"(?:the\s+)?(?P<corner2>top left|top right|bottom left|bottom right)\s+corner)$")
_OTHER_SCREEN = re.compile(r"^(?:move\s+(?:it\s+|this\s+|the\s+window\s+)?)?(?:to\s+)?(?:the\s+)?(?:other|next|second)\s+(?:screen|display|monitor)$")
_DESKTOP = re.compile(r"^(?:go\s+to\s+|switch\s+to\s+)?(?:desktop|space)\s+(?P<n>\d)$|^(?P<dir>next|previous|last)\s+(?:desktop|space)$")
_MISSION = re.compile(r"^(?P<what>mission control|show (?:the )?desktop|show desktop|app windows|all windows|show all windows"
                      r"|launchpad|notification center|open notification center|notifications|control center|open control center)$")
_DARK = re.compile(r"^(?:turn\s+(?P<v1>on|off)\s+)?(?P<mode>dark|light)\s+mode(?:\s+(?P<v2>on|off))?$")
_WIFI = re.compile(r"^(?:turn\s+(?P<v1>on|off)\s+)?(?:the\s+)?wi\s*-?\s*fi(?:\s+(?P<v2>on|off))?$")
_BRIGHT = re.compile(r"^(?:(?:turn\s+)?(?:the\s+)?)?(?:brightness|screen)\s+(?P<dir>up|down)$|^(?P<dir2>brighter|dimmer|darker)$")
_OUTPUT = re.compile(r"^(?:use|play\s+(?:through|on)|sound\s+(?:to|through|on)|output\s+to)\s+(?:my\s+|the\s+)?(?P<device>.+?)(?:\s+for\s+sound)?$")
_SEARCH = re.compile(r"^(?:search\s+(?P<eng2>youtube|amazon|wikipedia|github|reddit|maps|images|duckduckgo|bing)\s+for\s+(?P<q2>.+)|"
                     r"(?P<eng1>google|search(?:\s+(?:google|the\s+web))?)\s+(?:for\s+)?(?P<q1>.+)|"
                     r"(?:look\s+up|show\s+me)\s+(?P<q3>.+?)\s+on\s+(?P<eng3>youtube|amazon|wikipedia|maps|reddit))$")
# "go to apple.com" (heard "go to apple com"); endings that are also words ("app", "tv") need "dot".
_GO_TO = re.compile(r"^(?:go\s+to|open\s+(?:the\s+)?(?:website|site|page))\s+(?P<site>[a-z0-9][a-z0-9 \-]*?)\s+"
                    r"(?:(?:dot\s+)?(?P<tld>com|org|net|io|ai|edu|gov)|dot\s+(?P<tld2>co|app|so|tv|dev|me|gg|uk|ca))$")
_FIND = re.compile(r"^(?:find|search\s+(?:the\s+)?page\s+for|find\s+on\s+(?:the\s+)?page)\s+(?P<q>.+?)(?:\s+on\s+(?:the\s+|this\s+)?page)?$")
_SPOTLIGHT = re.compile(r"^spotlight(?:\s+(?:search\s+)?(?:for\s+)?(?P<q>.+))?$")
_SHORTCUT = re.compile(r"^(?:run|start)\s+(?:the\s+|my\s+)?shortcut\s+(?P<name>.+)$|^(?:run|start)\s+(?:the\s+|my\s+)?(?P<name2>.+?)\s+shortcut$")
_AGAIN = re.compile(r"^(?:again|repeat(?:\s+that)?|do\s+(?:it|that)\s+again)$|^(?:do\s+(?:it|that)|repeat(?:\s+that)?)\s+(?P<n>\d+)\s+times$")
_THAT = re.compile(r"^(?P<what>select|delete|scratch|capitalize|uppercase|lowercase|bold)\s+that$")
_DRAG = re.compile(r"^drag\s+(?:the\s+)?(?P<a>.+?)\s+(?:to|onto|into)\s+(?:the\s+)?(?P<b>.+)$")
_SCROLL_IN = re.compile(r"^scroll\s+(?:the\s+)?(?P<what>.+?)\s+(?P<dir>up|down)$")
_GRID = re.compile(r"^(?:show\s+(?:the\s+)?)?(?:mouse\s+)?grid$")


def _state(*values):
    v = next((x for x in values if x), None)
    return None if v is None else v == "on"


def parse(said, original=""):
    """A command tuple for the controls in this module, or None. `said` is normalized (apps.normalize);
    `original` is the transcript as heard, for "type …" (which keeps its capitals and punctuation)."""
    m = _TYPE.match(original or "")
    if m:
        return ("type", re.sub(r"(?<=\w)\.$", "", m["text"].strip()))  # Whisper's closing period isn't typed
    m = _AGAIN.match(said)
    if m:
        return ("again", int(m["n"]) if m["n"] else 1)
    m = _PRESS.match(said)
    if m:
        keys = parse_keys(m["keys"])
        if keys:
            return ("keys", keys, int(m["n"]) if m["n"] else 1)
    m = _ARROWS.match(said)
    if m:  # "down 3": the arrow key three times ("down" alone is too easy to mishear)
        return ("keys", [(m["key"], "")], _COUNT.get(m["n"]) or int(m["n"]))
    if said in EDIT_KEYS:
        key, mods = EDIT_KEYS[said]
        return ("keys", [(key, mods)], 1)
    if said in ("new paragraph",):
        return ("keys", [("return", "shift")], 2)
    m = _THAT.match(said)
    if m:
        return ("that", {"scratch": "delete"}.get(m["what"], m["what"]))
    m = _SNAP.match(said)
    if m:
        where = m["where"] or m["corner1"] or m["corner2"]
        return ("snap", {"left side": "left", "right side": "right"}.get(where, where.replace(" half", "")))
    if _OTHER_SCREEN.match(said):
        return ("other_screen",)
    m = _DESKTOP.match(said)
    if m:
        return ("desktop", int(m["n"]) if m["n"] else ("next" if m["dir"] == "next" else "previous"))
    m = _MISSION.match(said)
    if m:
        what = m["what"]
        view = ("desktop" if "desktop" in what else "app" if "app" in what else "launchpad" if what == "launchpad"
                else "notifications" if "notification" in what else "control" if "control center" in what else "all")
        return ("mission", view)
    m = _DARK.match(said)
    if m:
        state = _state(m["v1"], m["v2"])
        return ("dark_mode", (m["mode"] == "dark") if state is None else (state if m["mode"] == "dark" else not state))
    m = _WIFI.match(said)
    if m:
        return ("wifi", _state(m["v1"], m["v2"]))
    m = _BRIGHT.match(said)
    if m:
        direction = m["dir"] or ("up" if m["dir2"] == "brighter" else "down")
        return ("brightness", direction)
    m = _SHORTCUT.match(said)
    if m:
        return ("run_shortcut", (m["name"] or m["name2"]).strip())
    m = _SEARCH.match(said)
    if m:
        engine = (m["eng2"] or m["eng3"] or "google").replace("search", "google").split()[0]
        engine = "google" if engine not in SEARCH_URLS else engine
        return ("search", engine, (m["q1"] or m["q2"] or m["q3"]).strip())
    m = _GO_TO.match(said)
    if m:  # "go to apple.com" (heard as "go to apple com"), "go to news dot ycombinator dot com"
        return ("go_to", re.sub(r"\s+dot\s+", ".", m["site"]).replace(" ", "") + "." + (m["tld"] or m["tld2"]))
    m = _FIND.match(said)
    if m and not m["q"].startswith(("folder", "my ", "the folder")):
        return ("find", m["q"])
    m = _SPOTLIGHT.match(said)
    if m:
        return ("spotlight", m["q"] or "")
    m = _GRID.match(said)
    if m:
        return ("grid",)
    m = _DRAG.match(said)
    if m:
        return ("drag", m["a"].strip(), m["b"].strip())
    m = _SCROLL_IN.match(said)
    if m and m["what"] not in ("a little", "a bit", "a lot", "more", "a page", "lots", "all the way"):
        return ("scroll_in", m["what"], m["dir"])
    m = _OUTPUT.match(said)
    if m and not re.match(r"^(?:tab|window|desktop|space|the\s+)", m["device"]):
        return ("output", m["device"])
    return None


# --- "select that" / "delete that": the last dictation --------------------------------------------

def select_back(length, press_fn=None):
    """Select the last `length` characters (what was just dictated): ⇧← that many times."""
    (press_fn or press)("left", "shift", length)


def transform(text, how):
    return {"capitalize": text[:1].upper() + text[1:], "uppercase": text.upper(), "lowercase": text.lower()}.get(how, text)


# --- The grid --------------------------------------------------------------------------------------

def grid_cells(region, rows=3, cols=3):
    """The 9 cells of `region` (x, y, w, h, top-left origin), numbered left to right, top to bottom."""
    x, y, w, h = region
    return [(x + c * w / cols, y + r * h / rows, w / cols, h / rows) for r in range(rows) for c in range(cols)]


# --- Your own commands (Settings) -------------------------------------------------------------------

def custom(text, commands):
    """("custom", phrase, keys, text) when `text` is one of your own commands: its phrase said as
    it was set, ignoring case and punctuation. Keys like "cmd shift t" or "enter"; None if not one."""
    from .apps import normalize
    said = normalize(text)
    for entry in commands or []:
        if not isinstance(entry, dict) or not entry.get("say") or normalize(entry["say"]) != said:
            continue
        keys = []
        for combo in str(entry.get("keys") or "").split(","):
            words = combo.strip().lower().replace("+", " ")
            parsed = parse_keys(" ".join({"cmd": "command", "opt": "option"}.get(w, w) for w in words.split())) if words else None
            keys += parsed or []
        return ("custom", entry["say"], keys, str(entry.get("type") or ""))
    return None
