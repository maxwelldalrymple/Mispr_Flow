"""Global `fn` key monitoring via a listen-only Quartz event tap.

Needs the Input Monitoring permission. A listen-only tap cannot swallow the key,
so macOS's own fn action must be off: System Settings > Keyboard >
"Press 🌐 key to" > Do Nothing.
"""

import subprocess
import sys

import Quartz

FN_MASK = Quartz.kCGEventFlagMaskSecondaryFn

_FN_USAGE_DO_NOTHING = "0"  # AppleFnUsageType value for "Do Nothing"


def has_permission():
    return bool(Quartz.CGPreflightListenEventAccess())


def request_permission():
    """Shows the system Input Monitoring prompt (only the first time)."""
    return bool(Quartz.CGRequestListenEventAccess())


def fn_key_does_nothing():
    """True when macOS won't open the emoji picker / dictation / input switcher on fn."""
    out = subprocess.run(
        ["defaults", "read", "com.apple.HIToolbox", "AppleFnUsageType"],
        capture_output=True, text=True,
    )
    return out.returncode == 0 and out.stdout.strip() == _FN_USAGE_DO_NOTHING


class FnMonitor:
    """Calls on_down / on_up for fn, and on_combo when another key is pressed while fn is held."""

    def __init__(self, on_down, on_up, on_combo):
        self.on_down, self.on_up, self.on_combo = on_down, on_up, on_combo
        self.fn_down = False
        self._tap = None

    def start(self):
        mask = Quartz.CGEventMaskBit(Quartz.kCGEventFlagsChanged) | Quartz.CGEventMaskBit(Quartz.kCGEventKeyDown)
        self._tap = Quartz.CGEventTapCreate(
            Quartz.kCGSessionEventTap,
            Quartz.kCGHeadInsertEventTap,
            Quartz.kCGEventTapOptionListenOnly,
            mask,
            self._callback,
            None,
        )
        if self._tap is None:
            print("whispr: cannot watch the fn key; grant Input Monitoring and restart", file=sys.stderr)
            return False
        source = Quartz.CFMachPortCreateRunLoopSource(None, self._tap, 0)
        Quartz.CFRunLoopAddSource(Quartz.CFRunLoopGetCurrent(), source, Quartz.kCFRunLoopCommonModes)
        Quartz.CGEventTapEnable(self._tap, True)
        return True

    def _callback(self, proxy, event_type, event, refcon):
        if event_type in (Quartz.kCGEventTapDisabledByTimeout, Quartz.kCGEventTapDisabledByUserInput):
            Quartz.CGEventTapEnable(self._tap, True)
            return event
        if event_type == Quartz.kCGEventKeyDown:
            if self.fn_down:
                self.on_combo()
            return event
        down = bool(Quartz.CGEventGetFlags(event) & FN_MASK)
        if down != self.fn_down:
            self.fn_down = down
            (self.on_down if down else self.on_up)()
        return event
