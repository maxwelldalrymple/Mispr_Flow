"""Global `fn` key handling via a Quartz event tap.

Preferred: an *active* tap that swallows fn presses, so macOS never sees them and
doesn't open the emoji picker / input switcher / dictation (what Wispr Flow does).
That needs the Accessibility permission. Without it we fall back to a listen-only
tap (Input Monitoring), which works but lets macOS's own fn action fire too.
"""

import subprocess
import sys

import ApplicationServices as AS
import Quartz
from PyObjCTools import AppHelper

FN_MASK = Quartz.kCGEventFlagMaskSecondaryFn
# Besides the fn modifier flag, the 🌐/fn key also sends its own key-down/up with this
# keycode; macOS opens the Emoji & Symbols picker from these, so they must be swallowed too.
GLOBE_KEYCODE = 179

_FN_USAGE_DO_NOTHING = "0"  # AppleFnUsageType value for "Do Nothing"


def has_input_monitoring():
    return bool(Quartz.CGPreflightListenEventAccess())


def request_input_monitoring():
    """Shows the system Input Monitoring prompt (only the first time)."""
    return bool(Quartz.CGRequestListenEventAccess())


def has_accessibility():
    return bool(AS.AXIsProcessTrusted())


def request_accessibility():
    """Shows the system Accessibility prompt (only the first time)."""
    return bool(AS.AXIsProcessTrustedWithOptions({AS.kAXTrustedCheckOptionPrompt: True}))


def fn_key_does_nothing():
    """True when macOS won't open the emoji picker / dictation / input switcher on fn."""
    out = subprocess.run(
        ["defaults", "read", "com.apple.HIToolbox", "AppleFnUsageType"],
        capture_output=True, text=True,
    )
    return out.returncode == 0 and out.stdout.strip() == _FN_USAGE_DO_NOTHING


_COMMAND_MODIFIERS = (
    Quartz.kCGEventFlagMaskCommand | Quartz.kCGEventFlagMaskControl | Quartz.kCGEventFlagMaskAlternate
)


class FnMonitor:
    """Calls on_down / on_up for fn, and on_combo when another key is pressed while fn is held.

    `on_key(keycode) -> bool` is asked about every plain (unmodified) key press; returning
    True swallows the key (and its key-up) so it doesn't reach the focused app. It runs
    inside the tap, so it must only inspect state and defer any real work.
    """

    def __init__(self, on_down, on_up, on_combo, on_key=None):
        self.on_down, self.on_up, self.on_combo = on_down, on_up, on_combo
        self.on_key = on_key
        self.fn_down = False
        self._swallowed_keys = set()  # swallow the key-up of keys whose key-down we took
        self.active = False  # True when fn presses are swallowed
        self._tap = None
        self._source = None

    def start(self):
        return self._install(active=True) or self._install(active=False)

    def upgrade(self):
        """Switch from listen-only to swallowing fn once Accessibility is granted."""
        if self.active or not has_accessibility():
            return False
        self._remove()
        if self._install(active=True):
            return True
        self._install(active=False)
        return False

    def _install(self, active):
        mask = (
            Quartz.CGEventMaskBit(Quartz.kCGEventFlagsChanged)
            | Quartz.CGEventMaskBit(Quartz.kCGEventKeyDown)
            | Quartz.CGEventMaskBit(Quartz.kCGEventKeyUp)
        )
        # The HID tap sees keys before the window server acts on them; swallowing fn at the
        # later session tap is too late to stop the emoji picker.
        tap = Quartz.CGEventTapCreate(
            Quartz.kCGHIDEventTap if active else Quartz.kCGSessionEventTap,
            Quartz.kCGHeadInsertEventTap,
            Quartz.kCGEventTapOptionDefault if active else Quartz.kCGEventTapOptionListenOnly,
            mask,
            self._callback,
            None,
        )
        if tap is None:
            return False
        self._tap, self.active = tap, active
        self._source = Quartz.CFMachPortCreateRunLoopSource(None, tap, 0)
        Quartz.CFRunLoopAddSource(Quartz.CFRunLoopGetCurrent(), self._source, Quartz.kCFRunLoopCommonModes)
        Quartz.CGEventTapEnable(tap, True)
        return True

    def _remove(self):
        if self._tap is not None:
            Quartz.CGEventTapEnable(self._tap, False)
            Quartz.CFRunLoopRemoveSource(Quartz.CFRunLoopGetCurrent(), self._source, Quartz.kCFRunLoopCommonModes)
            Quartz.CFMachPortInvalidate(self._tap)
        self._tap = self._source = None
        self.active = False

    def _callback(self, proxy, event_type, event, refcon):
        if event_type in (Quartz.kCGEventTapDisabledByTimeout, Quartz.kCGEventTapDisabledByUserInput):
            Quartz.CGEventTapEnable(self._tap, True)
            return event
        # Handlers run on the next run-loop pass: an active tap holds up every keystroke
        # system-wide until this callback returns, and starting the mic takes ~50-100 ms.
        if event_type in (Quartz.kCGEventKeyDown, Quartz.kCGEventKeyUp):
            keycode = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode)
            if keycode == GLOBE_KEYCODE:
                return None if self.active else event
        if event_type == Quartz.kCGEventKeyUp:
            if keycode in self._swallowed_keys:
                self._swallowed_keys.discard(keycode)
                return None
            return event
        if event_type == Quartz.kCGEventKeyDown:
            if self.fn_down:
                AppHelper.callAfter(self.on_combo)
                return event  # fn+arrow etc. still reach the app
            plain = not (Quartz.CGEventGetFlags(event) & _COMMAND_MODIFIERS)
            if self.active and plain and self.on_key is not None and self.on_key(keycode):
                self._swallowed_keys.add(keycode)
                return None
            return event
        down = bool(Quartz.CGEventGetFlags(event) & FN_MASK)
        if down == self.fn_down:
            return event  # another modifier changed
        self.fn_down = down
        AppHelper.callAfter(self.on_down if down else self.on_up)
        # Swallow fn so macOS (and the focused app) never act on it.
        return None if self.active else event
