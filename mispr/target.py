"""Where a dictation goes: the text box you were in when you started talking, even if you've
switched windows or apps while it was being transcribed.

At the start, `capture()` notes the app, its window, and the focused text box (if one has the
cursor). At the end, if you're still there nothing changes; otherwise `deliver()`:
  1. quietly inserts the text into that box (Accessibility, no window switch), or
  2. when that isn't possible (or Auto-Enter must press Return there), brings that window back,
     pastes, sends, and returns you to where you were.
"""

import time
from dataclasses import dataclass

from AppKit import NSApplicationActivateIgnoringOtherApps, NSRunningApplication, NSWorkspace

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


def insert_quietly(element, text):
    """Put `text` at the cursor of `element` without switching windows. True if it landed."""
    import ApplicationServices as AS
    before = pointer._ax(element, "AXValue")
    if AS.AXUIElementSetAttributeValue(element, "AXSelectedText", text) != 0:
        return False
    after = pointer._ax(element, "AXValue")
    # Some boxes accept the call but change nothing: check the text is really there now.
    return isinstance(after, str) and after != before and text.strip()[:20] in after


def bring_back(spot, element):
    """Bring the start window to the front with the cursor in `element`."""
    import ApplicationServices as AS
    app = NSRunningApplication.runningApplicationWithProcessIdentifier_(spot.pid)
    if app is None:
        return False
    app.activateWithOptions_(NSApplicationActivateIgnoringOtherApps)
    if spot.window is not None:
        AS.AXUIElementPerformAction(spot.window, "AXRaise")
    if element is not None:
        AS.AXUIElementSetAttributeValue(element, "AXFocused", True)
    return True


def return_to(spot):
    """Go back to where you were (the app and window you'd switched to)."""
    if spot is None:
        return
    import ApplicationServices as AS
    app = NSRunningApplication.runningApplicationWithProcessIdentifier_(spot.pid)
    if app is not None:
        app.activateWithOptions_(NSApplicationActivateIgnoringOtherApps)
        if spot.window is not None:
            AS.AXUIElementPerformAction(spot.window, "AXRaise")


def settle(seconds=0.15):
    time.sleep(seconds)
