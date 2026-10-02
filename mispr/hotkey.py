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

KEY_M = 46  # ⌥M starts or stops a meeting note

# The dictation key (Settings > General > Shortcuts). "fn" is the default; "modifier" is one
# side of a modifier key (e.g. right ⌥); "key" is any other key (e.g. F5).
FN_TRIGGER = {"kind": "fn", "keycode": 63, "label": "fn"}
# Device-dependent flag bits, to tell left from right modifiers (IOKit NX_DEVICE*KEYMASK).
MODIFIER_MASKS = {59: 0x01, 62: 0x2000, 56: 0x02, 60: 0x04, 58: 0x20, 61: 0x40, 55: 0x08, 54: 0x10}


def normalize_trigger(trigger):
    """A usable trigger dict, falling back to fn for anything malformed."""
    if not isinstance(trigger, dict):
        return dict(FN_TRIGGER)
    kind, keycode = trigger.get("kind"), trigger.get("keycode")
    if kind == "modifier" and keycode in MODIFIER_MASKS:
        return {"kind": kind, "keycode": keycode, "label": str(trigger.get("label") or "key")}
    if kind == "key" and isinstance(keycode, int) and 0 <= keycode < 256 and keycode != GLOBE_KEYCODE:
        return {"kind": kind, "keycode": keycode, "label": str(trigger.get("label") or "key")}
    return dict(FN_TRIGGER)


# Combos: modifiers held together (by name), optionally plus one key, e.g. ⌃⌥ or ⌥S.
COMBO_FLAGS = {
    "control": Quartz.kCGEventFlagMaskControl, "option": Quartz.kCGEventFlagMaskAlternate,
    "shift": Quartz.kCGEventFlagMaskShift, "command": Quartz.kCGEventFlagMaskCommand,
}
_ALL_COMBO_FLAGS = sum(COMBO_FLAGS.values())


def normalize_combo(trigger):
    """{"kind": "combo", "mods": [...], "keycode": int | None, "label"} or None if unusable:
    it needs a key with at least one modifier, or at least two modifiers on their own."""
    mods = trigger.get("mods")
    if not isinstance(mods, list) or not mods or any(m not in COMBO_FLAGS for m in mods):
        return None
    keycode = trigger.get("keycode")
    if keycode is not None and not (isinstance(keycode, int) and 0 <= keycode < 256 and keycode != GLOBE_KEYCODE):
        return None
    if keycode is None and len(set(mods)) < 2:
        return None
    return {"kind": "combo", "mods": sorted(set(mods)), "keycode": keycode, "label": str(trigger.get("label") or "keys")}


def combo_mask(trigger):
    return sum(COMBO_FLAGS[m] for m in trigger["mods"])


KEY_RETURN = 36
# The Auto-Enter key: press it to turn Auto-Enter on or off. Default ⌃⌥Return.
DEFAULT_AUTO_ENTER_KEY = {"kind": "combo", "mods": ["control", "option"], "keycode": KEY_RETURN, "label": "⌃⌥↩"}


def normalize_toggle_trigger(trigger):
    """The Auto-Enter key: a key with modifiers ({"kind": "combo", ...}), or None (off/unusable)."""
    if not isinstance(trigger, dict) or trigger.get("kind") != "combo" or trigger.get("keycode") is None:
        return None
    return normalize_combo(trigger)


def normalize_switch_trigger(trigger, dictation=None):
    """The app switcher key, or None when it's off, malformed, fn, or the dictation key itself."""
    if not isinstance(trigger, dict) or trigger.get("kind") not in ("modifier", "key", "combo"):
        return None
    if trigger["kind"] == "combo":
        return normalize_combo(trigger)
    trigger = normalize_trigger(trigger)
    if trigger["kind"] == "fn" or (dictation and trigger["keycode"] == normalize_trigger(dictation)["keycode"]):
        return None
    return trigger


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
    """Calls on_down / on_up for the dictation key (fn unless set_trigger chose another), and
    on_combo when another key is pressed while it's held.

    `on_key(keycode) -> bool` is asked about every plain (unmodified) key press; returning
    True swallows the key (and its key-up) so it doesn't reach the focused app. It runs
    inside the tap, so it must only inspect state and defer any real work.
    """

    def __init__(self, on_down, on_up, on_combo, on_key=None, trigger=None, on_note=None,
                 on_switch=None, switch_trigger=None, on_toggle=None, toggle_trigger=None):
        self.on_down, self.on_up, self.on_combo = on_down, on_up, on_combo
        self.on_key = on_key
        self.on_note = on_note  # ⌥M: new meeting note
        self.trigger = normalize_trigger(trigger)
        self.fn_down = False
        # The app switcher key: on_switch("down" | "up" | "combo"). Off when switch_trigger is None.
        self.on_switch = on_switch
        self.switch_trigger = normalize_switch_trigger(switch_trigger, self.trigger)
        self.switch_down = False
        # The Auto-Enter key: on_toggle() once per press. Off when toggle_trigger is None.
        self.on_toggle = on_toggle
        self.toggle_trigger = normalize_toggle_trigger(toggle_trigger)
        self._swallowed_keys = set()  # swallow the key-up of keys whose key-down we took
        self.active = False  # True when fn presses are swallowed
        self._tap = None
        self._source = None

    def set_trigger(self, trigger):
        """Switch the dictation key; a press in progress on the old key is released."""
        trigger = normalize_trigger(trigger)
        if trigger == self.trigger:
            return
        if self.fn_down:
            self.fn_down = False
            AppHelper.callAfter(self.on_up)
        self.trigger = trigger

    def set_switch_trigger(self, trigger):
        """Change (or turn off, with None) the app switcher key."""
        trigger = normalize_switch_trigger(trigger, self.trigger)
        if trigger == self.switch_trigger:
            return
        if self.switch_down:
            self.switch_down = False
            AppHelper.callAfter(self.on_switch, "combo")  # abandon a press on the old key
        self.switch_trigger = trigger

    def set_toggle_trigger(self, trigger):
        """Change (or turn off, with None) the Auto-Enter key."""
        self.toggle_trigger = normalize_toggle_trigger(trigger)

    def _is_toggle(self, event, keycode):
        t = self.toggle_trigger
        return (t is not None and self.on_toggle is not None and keycode == t["keycode"]
                and Quartz.CGEventGetFlags(event) & _ALL_COMBO_FLAGS == combo_mask(t))

    def _switch_edge(self, event_type, event):
        """For the switch key: "down", "up", "repeat" (held key-repeat), or None (another key)."""
        t = self.switch_trigger
        if t is None or self.on_switch is None:
            return None
        keycode = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode)
        if t["kind"] == "combo":
            return self._combo_edge(t, event_type, event, keycode)
        if keycode != t["keycode"]:
            return None
        if t["kind"] == "key" and event_type in (Quartz.kCGEventKeyDown, Quartz.kCGEventKeyUp):
            if Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventAutorepeat):
                return "repeat"
            return "down" if event_type == Quartz.kCGEventKeyDown else "up"
        if t["kind"] == "modifier" and event_type == Quartz.kCGEventFlagsChanged:
            return "down" if Quartz.CGEventGetFlags(event) & MODIFIER_MASKS[t["keycode"]] else "up"
        return None

    def _combo_edge(self, t, event_type, event, keycode):
        held = Quartz.CGEventGetFlags(event) & _ALL_COMBO_FLAGS
        exact = held == combo_mask(t)
        if t["keycode"] is None:  # modifiers only: down while exactly those are held
            if event_type != Quartz.kCGEventFlagsChanged:
                return None
            if exact and not self.switch_down:
                return "down"
            if not exact and self.switch_down:
                return "up"
            return None
        if keycode != t["keycode"] or event_type not in (Quartz.kCGEventKeyDown, Quartz.kCGEventKeyUp):
            return None
        if event_type == Quartz.kCGEventKeyUp:
            return "up" if self.switch_down else None
        if not exact:
            return None  # the key alone (or with other modifiers) types as usual
        if Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventAutorepeat):
            return "repeat"
        return "down"

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
        kind, trigger_code = self.trigger["kind"], self.trigger["keycode"]
        swallow = None if self.active else event
        edge = self._switch_edge(event_type, event)
        if edge is not None:
            if edge != "repeat" and (edge == "down") != self.switch_down:
                self.switch_down = edge == "down"
                AppHelper.callAfter(self.on_switch, edge)
            # Modifiers still reach apps (they do nothing alone); a key press is swallowed.
            t = self.switch_trigger
            if t["kind"] == "modifier" or (t["kind"] == "combo" and event_type == Quartz.kCGEventFlagsChanged):
                return event
            return swallow
        if self.switch_down and event_type == Quartz.kCGEventKeyDown:
            # ⌘-style shortcut with the switch modifier held: it wasn't meant for us.
            self.switch_down = False
            AppHelper.callAfter(self.on_switch, "combo")
        if event_type in (Quartz.kCGEventKeyDown, Quartz.kCGEventKeyUp):
            keycode = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode)
            if keycode == GLOBE_KEYCODE and kind == "fn":
                return swallow
            if kind == "key" and keycode == trigger_code:
                down = event_type == Quartz.kCGEventKeyDown
                if Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventAutorepeat):
                    return swallow  # holding the key: one press, not a stream of them
                if down != self.fn_down:
                    self.fn_down = down
                    AppHelper.callAfter(self.on_down if down else self.on_up)
                return swallow
        if event_type == Quartz.kCGEventKeyUp:
            if keycode in self._swallowed_keys:
                self._swallowed_keys.discard(keycode)
                return None
            return event
        if event_type == Quartz.kCGEventKeyDown:
            flags = Quartz.CGEventGetFlags(event)
            if (keycode == KEY_M and self.on_note is not None and flags & Quartz.kCGEventFlagMaskAlternate
                    and not flags & (Quartz.kCGEventFlagMaskCommand | Quartz.kCGEventFlagMaskControl)):
                if not Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventAutorepeat):
                    AppHelper.callAfter(self.on_note)
                if self.active:
                    self._swallowed_keys.add(keycode)
                    return None  # ⌥M would otherwise type "µ"
                return event
            if self._is_toggle(event, keycode):  # the Auto-Enter key: on/off, and the app never sees it
                if not Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventAutorepeat):
                    AppHelper.callAfter(self.on_toggle)
                if self.active:
                    self._swallowed_keys.add(keycode)
                    return None
                return event
            if self.fn_down:
                AppHelper.callAfter(self.on_combo)
                return event  # fn+arrow etc. still reach the app
            plain = not (Quartz.CGEventGetFlags(event) & _COMMAND_MODIFIERS)
            if self.active and plain and self.on_key is not None and self.on_key(keycode):
                self._swallowed_keys.add(keycode)
                return None
            return event
        if kind == "key":
            return event  # modifier changes don't matter for a regular trigger key
        if kind == "modifier":
            keycode = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode)
            if keycode != trigger_code:
                return event  # a different modifier
            down = bool(Quartz.CGEventGetFlags(event) & MODIFIER_MASKS[trigger_code])
        else:
            down = bool(Quartz.CGEventGetFlags(event) & FN_MASK)
        if down == self.fn_down:
            return event  # another modifier changed
        self.fn_down = down
        AppHelper.callAfter(self.on_down if down else self.on_up)
        # Swallow the key so macOS (and the focused app) never act on it.
        return swallow
