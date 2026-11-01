"""Where a dictation goes: the text box you were in when you started talking, even if you've
switched windows or apps while it was being transcribed. Windows are never switched for you.

At the start, `capture()` notes the app, its window, and the focused text box (if one has the
cursor). At the end, if you're still there nothing changes; otherwise:
  1. the text is inserted into that box in the background (`insert_quietly`), or
  2. where the box doesn't allow that (rich web editors) or Auto-Enter must press Return, it
     waits, and goes in the moment you go back to that window.
"""

import time
from dataclasses import dataclass

from AppKit import NSWorkspace

from . import context, pointer

AX_TIMEOUT = 0.3  # seconds: never let a hung app stall dictation


@dataclass
class Spot:
    pid: int
    app: str
    window: object = None
    element: object = None  # the text box with the cursor, or None (its main box is used)


def _app_element(pid):
    import ApplicationServices as AS
    app = AS.AXUIElementCreateApplication(pid)
    AS.AXUIElementSetMessagingTimeout(app, AX_TIMEOUT)
    return app


def capture():
    """Where you are now: the front app, its window, and the focused text box. None if unknown."""
    front = NSWorkspace.sharedWorkspace().frontmostApplication()
    if front is None:
        return None
    pid = front.processIdentifier()
    try:
        app = _app_element(pid)
        window = pointer._ax(app, "AXFocusedWindow")
        focused = pointer._ax(app, "AXFocusedUIElement")
        element = focused if focused is not None and context._is_text_input(focused) else None
    except Exception:
        window = element = None
    return Spot(pid, str(front.localizedName() or "the app"), window, element)


_NOW = object()  # "look it up"


def still_there(spot, now=_NOW):
    """True if you're still where the dictation started (same app and window, and the same box
    if one had the cursor), so the usual paste is right. `now` is where you are (looked up if
    not given; None means unknown)."""
    now = capture() if now is _NOW else now
    if spot is None or now is None:
        return True  # can't tell: behave as before
    if now.pid != spot.pid:
        return False
    if spot.window is not None and now.window is not None and spot.window != now.window:
        return False
    return spot.element is None or now.element is None or spot.element == now.element


def box_for(spot):
    """The text box to deliver to: the one that had the cursor, else the window's main one."""
    if spot.element is not None:
        return spot.element
    found = pointer.main_input(pointer.text_inputs(spot.pid))
    return found.element if found else None


def _value(element):
    value = pointer._ax(element, "AXValue")
    return value if isinstance(value, str) else None


def insert_quietly(element, text, wait=0.25, pause=time.sleep):
    """Put `text` at the cursor of `element` in the background, without switching windows.
    Tries the box's own "insert" (native Mac text boxes), then setting its whole text with the
    words added at the cursor (plain web text boxes). Rich web editors (Claude, ChatGPT, Slack…)
    refuse both: False. Chrome applies changes a moment later, hence the short wait."""
    import ApplicationServices as AS
    before = _value(element)
    if before is None:
        return False
    if AS.AXUIElementSetAttributeValue(element, "AXSelectedText", text) == 0:
        pause(wait)
        if _landed(element, before, text):
            return True
    cursor = len(before)
    selected = pointer._ax(element, "AXSelectedTextRange")
    if selected is not None:
        ok, rng = AS.AXValueGetValue(selected, AS.kAXValueCFRangeType, None)
        if ok and 0 <= rng.location <= len(before):
            cursor = rng.location
    spaced = text if cursor == 0 or before[cursor - 1:cursor].isspace() else " " + text
    if AS.AXUIElementSetAttributeValue(element, "AXValue", before[:cursor] + spaced + before[cursor:]) != 0:
        return False
    pause(wait)
    return _landed(element, before, text)


def _landed(element, before, text):
    after = _value(element)
    return after is not None and after != before and text.strip()[:20] in after


def focus(element):
    """Put the cursor in `element` (the window is already in front: you came back to it)."""
    import ApplicationServices as AS
    return AS.AXUIElementSetAttributeValue(element, "AXFocused", True) == 0


def settle(seconds=0.15):
    time.sleep(seconds)
