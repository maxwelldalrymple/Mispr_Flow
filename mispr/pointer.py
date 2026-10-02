"""Voice clicking: "click Sign in", "double click Budget", "right click the logo", "show numbers".

What's on screen comes from the app itself, through the macOS Accessibility API: every button,
link, field, tab, menu item and labeled image of the window in front, with its name and place.
Browsers (Chrome, Safari, Firefox, Edge, Arc, Brave) and normal Mac apps all report this, so no
screenshot or text recognition is needed. Chrome and Electron apps only report web pages once
asked (`enable_web_accessibility`).

Clicks are real mouse events at the element's center, so the pointer visibly moves there.
"""

import difflib
import re
import time
from dataclasses import dataclass

# Roles a person would click, and how each is named.
CLICKABLE = {"AXButton", "AXLink", "AXMenuItem", "AXMenuBarItem", "AXCheckBox", "AXRadioButton", "AXTab",
             "AXPopUpButton", "AXMenuButton", "AXComboBox", "AXTextField", "AXTextArea", "AXSearchField",
             "AXDisclosureTriangle", "AXCell", "AXRow", "AXImage", "AXStaticText", "AXSlider", "AXSwitch",
             "AXToggle", "AXIncrementor", "AXColorWell", "AXHeading"}
# Plain text is clickable when it's what you read on a link or a list row.
NAME_ATTRS = ("AXTitle", "AXDescription", "AXValue", "AXPlaceholderValue", "AXHelp")
MAX_NAME = 80  # a longer value is a paragraph, not a label
CLOSE_MIN = 0.6  # the closest name must be at least this close (pointer.closeness) to be clicked
CLOSE_TIE = 0.05  # names this close to the best are shown as numbers to pick from
SCAN_LIMIT, SCAN_SECONDS = 6000, 2.0  # big pages: stop after this many elements, or this long
FIELD_ROLES = {"AXTextField", "AXTextArea", "AXSearchField", "AXComboBox"}
FIELD_WORDS = {"search", "search box", "search bar", "text box", "text field", "box", "field", "input", "address bar"}


@dataclass
class Target:
    name: str
    role: str
    frame: tuple  # (x, y, width, height), screen points from the top-left
    element: object = None

    @property
    def center(self):
        x, y, w, h = self.frame
        return x + w / 2, y + h / 2


def _ax(el, attr):
    import ApplicationServices as AS
    err, value = AS.AXUIElementCopyAttributeValue(el, attr, None)
    return value if err == 0 else None


def _frame(el):
    import ApplicationServices as AS
    pos, size = _ax(el, "AXPosition"), _ax(el, "AXSize")
    if pos is None or size is None:
        return None
    ok1, point = AS.AXValueGetValue(pos, AS.kAXValueCGPointType, None)
    ok2, extent = AS.AXValueGetValue(size, AS.kAXValueCGSizeType, None)
    if not (ok1 and ok2) or extent.width < 2 or extent.height < 2:
        return None
    return (float(point.x), float(point.y), float(extent.width), float(extent.height))


def name_of(el, role):
    """What the element is called on screen: its title, label, or (short) text."""
    for attr in NAME_ATTRS:
        if attr == "AXValue" and role not in ("AXStaticText", "AXTextField", "AXSearchField", "AXComboBox", "AXCell", "AXHeading"):
            continue
        value = _ax(el, attr)
        if isinstance(value, str):
            text = " ".join(value.split())
            if text and len(text) <= MAX_NAME:
                return text
    return ""


def enable_web_accessibility(pid):
    """Chrome and Electron apps only report a web page's contents once asked (as screen readers do)."""
    import ApplicationServices as AS
    app = AS.AXUIElementCreateApplication(pid)
    for attr in ("AXManualAccessibility", "AXEnhancedUserInterface"):
        AS.AXUIElementSetAttributeValue(app, attr, True)


def _visible(frame, bounds):
    x, y, w, h = frame
    bx, by, bw, bh = bounds
    return x + w > bx and y + h > by and x < bx + bw and y < by + bh


def targets(pid, limit=SCAN_LIMIT, budget=SCAN_SECONDS, clock=time.monotonic):
    """Everything clickable and visible in the app's front window (and its menu bar)."""
    import ApplicationServices as AS
    app = AS.AXUIElementCreateApplication(pid)
    window = _ax(app, "AXFocusedWindow") or _ax(app, "AXMainWindow")
    if window is None:
        return []
    bounds = _frame(window)
    if bounds is None:
        return []
    found, queue, seen, started = [], [window], 0, clock()
    while queue and seen < limit and clock() - started < budget:
        el = queue.pop(0)
        seen += 1
        role = _ax(el, "AXRole") or ""
        frame = _frame(el)
        if frame is not None and not _visible(frame, bounds):
            continue  # scrolled away: neither it nor its children are on screen
        if role in CLICKABLE and frame is not None:
            name = name_of(el, role)
            if name or role in FIELD_ROLES or role == "AXImage":
                found.append(Target(name, role, frame, el))
        queue.extend(_ax(el, "AXChildren") or [])
    for item in (_ax(_ax(app, "AXMenuBar"), "AXChildren") or [])[1:] if _ax(app, "AXMenuBar") else []:
        frame, name = _frame(item), name_of(item, "AXMenuBarItem")  # File, Edit, View… ([0] is the Apple menu)
        if frame and name:
            found.append(Target(name, "AXMenuBarItem", frame, item))
    return found


def _norm(text):
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", text.lower().replace("’", "").replace("'", "")).split())


def match(spoken, found):
    """The targets `spoken` names, best first: all of the best kind of match (several means
    the user picks a number). Exact name, then a name that starts with it, then one containing
    it as words, then a close spelling. "the search box" finds a field; "the Sign in button"
    finds "Sign in" (the full phrase is tried first, so "New Tab" stays "New Tab")."""
    said = _norm(re.sub(r"^(?:on\s+|the\s+)+", "", spoken.strip(), flags=re.I))
    if not said:
        return []
    short = re.sub(r"\s+(?:button|link|tab|icon|field)$", "", said)
    phrases = [said] + ([short] if short != said else [])
    named = [(t, _norm(t.name)) for t in found]
    tiers = (lambda p, n: n == p,
             lambda p, n: n.startswith(p + " "),
             lambda p, n: f" {p} " in f" {n} ")
    for test in tiers:
        for phrase in phrases:
            hits = [t for t, n in named if n and test(phrase, n)]
            if hits:
                return _dedupe(hits)
    if said in FIELD_WORDS or said.endswith((" box", " field", " bar")):
        fields = [t for t in found if t.role in FIELD_ROLES]
        if fields:
            return _dedupe(fields)
    # Nothing named exactly: the closest name wins ("opus" -> "Opus 4.6", "pref five" -> "Preferences 5").
    scored = [(max(closeness(p, n) for p in phrases), t) for t, n in named if n]
    best = max((s for s, _ in scored), default=0)
    if best < CLOSE_MIN:
        return []
    return _dedupe([t for s, t in scored if s >= best - CLOSE_TIE])


_NUMBERS = {w: str(i) for i, w in enumerate("zero one two three four five six seven eight nine ten".split())}


def _words(text):
    return [_NUMBERS.get(w, w) for w in text.split()]


def closeness(said, name):
    """0-1: how well `said` names `name`, allowing mishearing. Each spoken word is matched to
    its best word in the name (same word, a digit for a number word, a prefix like "pref" for
    "preferences", a close spelling, or the same sound); the average, a bit lower for names
    with many extra words."""
    from .apps import sounds_like
    spoken, words = _words(said), _words(name)
    if not spoken or not words:
        return 0.0
    total = 0.0
    for w in spoken:
        best = 0.0
        for n in words:
            if w == n:
                score = 1.0
            elif len(w) >= 3 and n.startswith(w):
                score = 0.85  # "pref" for "preferences"
            elif w.isdigit() or n.isdigit():
                score = 0.0  # numbers must match exactly
            else:
                score = difflib.SequenceMatcher(None, w, n).ratio()
                if len(w) >= 4 and sounds_like(w) and sounds_like(w) == sounds_like(n):
                    score = max(score, 0.8)  # "thru" / "through"
            best = max(best, score)
        total += best
    extra = max(0, len(words) - len(spoken))
    by_word = total / len(spoken) * (1 - 0.04 * min(extra, 5))
    joined = difflib.SequenceMatcher(None, "".join(spoken), "".join(words)).ratio()  # "walkthrough" / "Walk through setup"
    return max(by_word, joined)


PASSIVE = {"AXStaticText", "AXHeading", "AXImage", "AXCell", "AXRow"}


def _inside(point, frame):
    x, y, w, h = frame
    return x <= point[0] <= x + w and y <= point[1] <= y + h


def _dedupe(found):
    """One target per place: text or a picture inside a link or button is the same click, and
    two elements at the same spot are one."""
    active = [t for t in found if t.role not in PASSIVE]
    keep = [t for t in found if t.role not in PASSIVE or not any(_inside(t.center, a.frame) for a in active)]
    out = []
    for t in sorted(keep, key=lambda t: (t.role in PASSIVE, t.frame[1], t.frame[0])):
        cx, cy = t.center
        if not any(abs(cx - o.center[0]) < 6 and abs(cy - o.center[1]) < 6 for o in out):
            out.append(t)
    return sorted(out, key=lambda t: (t.frame[1], t.frame[0]))


NUMBER_LIMIT = 150  # badges on screen at once: more is unreadable


def numberable(found, limit=NUMBER_LIMIT):
    """What "show numbers" labels: everything you can act on (links, buttons, fields, tabs,
    menu items, pictures), not plain text, one per place, top to bottom."""
    keep = [t for t in found if t.role not in ("AXStaticText", "AXHeading", "AXRow", "AXCell") or not t.name]
    return _dedupe(keep)[:limit]


def click_at(point, button="left", count=1, move_only=False, post=None, pause=time.sleep):
    """Move the mouse to `point` (screen points from the top-left) and click it: left, right,
    or double (count=2)."""
    import Quartz
    post = post or (lambda event: Quartz.CGEventPost(Quartz.kCGHIDEventTap, event))
    x, y = point
    moved = Quartz.CGEventCreateMouseEvent(None, Quartz.kCGEventMouseMoved, (x, y), Quartz.kCGMouseButtonLeft)
    post(moved)
    if move_only:
        return
    pause(0.05)  # let hover effects settle, as a hand would
    down, up, which = ((Quartz.kCGEventRightMouseDown, Quartz.kCGEventRightMouseUp, Quartz.kCGMouseButtonRight)
                       if button == "right" else
                       (Quartz.kCGEventLeftMouseDown, Quartz.kCGEventLeftMouseUp, Quartz.kCGMouseButtonLeft))
    for n in range(1, count + 1):
        for kind in (down, up):
            event = Quartz.CGEventCreateMouseEvent(None, kind, (x, y), which)
            Quartz.CGEventSetIntegerValueField(event, Quartz.kCGMouseEventClickState, n)
            post(event)


def mouse_position():
    """Where the pointer is now, in screen points from the top-left."""
    import Quartz
    point = Quartz.CGEventGetLocation(Quartz.CGEventCreate(None))
    return float(point.x), float(point.y)
