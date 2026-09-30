"""Which screen the widget belongs on, and whether the focused app is fullscreen."""

from AppKit import NSEvent, NSPointInRect, NSScreen, NSWorkspace
import Quartz

_MIN_WINDOW_SIZE = 50


def _frontmost_window_bounds():
    """Bounds (CG coordinates, top-left origin) of the frontmost app's topmost normal window."""
    app = NSWorkspace.sharedWorkspace().frontmostApplication()
    if app is None:
        return None
    pid = app.processIdentifier()
    windows = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
        Quartz.kCGNullWindowID,
    ) or []
    for w in windows:
        if w.get("kCGWindowOwnerPID") != pid or w.get("kCGWindowLayer") != 0:
            continue
        b = w.get("kCGWindowBounds")
        if b and b["Width"] >= _MIN_WINDOW_SIZE and b["Height"] >= _MIN_WINDOW_SIZE:
            return b
    return None


def active_screen():
    """Return (screen, is_fullscreen) for the screen holding the focused window.

    Falls back to the screen under the mouse when the focused app has no window.
    """
    screens = NSScreen.screens()
    primary_h = screens[0].frame().size.height
    b = _frontmost_window_bounds()
    if b is not None:
        # Convert the window centre from CG (y down from primary top) to AppKit (y up).
        center = (b["X"] + b["Width"] / 2, primary_h - (b["Y"] + b["Height"] / 2))
        for s in screens:
            f = s.frame()
            if NSPointInRect(center, f):
                cg_top = primary_h - (f.origin.y + f.size.height)
                fullscreen = (
                    abs(b["Width"] - f.size.width) < 1
                    and abs(b["Height"] - f.size.height) < 1
                    and abs(b["X"] - f.origin.x) < 1
                    and abs(b["Y"] - cg_top) < 1
                )
                return s, fullscreen
    mouse = NSEvent.mouseLocation()
    for s in screens:
        if NSPointInRect(mouse, s.frame()):
            return s, False
    return NSScreen.mainScreen(), False
