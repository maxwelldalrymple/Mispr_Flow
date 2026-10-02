import subprocess

import pytest
import Quartz

from mispr import hotkey
from mispr.hotkey import FN_MASK, GLOBE_KEYCODE, FnMonitor

FLAGS_CHANGED, KEY_DOWN, KEY_UP = Quartz.kCGEventFlagsChanged, Quartz.kCGEventKeyDown, Quartz.kCGEventKeyUp
CMD = Quartz.kCGEventFlagMaskCommand


def ev(keycode=0, flags=0, repeat=0):
    return {"keycode": keycode, "flags": flags, "repeat": repeat}


@pytest.fixture
def fake_events(monkeypatch):
    enabled = []
    monkeypatch.setattr(hotkey.Quartz, "CGEventGetIntegerValueField",
                        lambda e, field: e["repeat"] if field == Quartz.kCGKeyboardEventAutorepeat else e["keycode"])
    monkeypatch.setattr(hotkey.Quartz, "CGEventGetFlags", lambda e: e["flags"])
    monkeypatch.setattr(hotkey.Quartz, "CGEventTapEnable", lambda tap, on: enabled.append((tap, on)))
    return enabled


@pytest.fixture
def monitor(fake_events):
    calls = []
    keys = {}  # keycode -> whether on_key should handle it

    def on_key(code):
        calls.append(("key", code))
        return keys.get(code, False)

    m = FnMonitor(lambda: calls.append("down"), lambda: calls.append("up"), lambda: calls.append("combo"), on_key)
    m.active = True
    m.calls, m.keys = calls, keys
    return m


def cb(m, etype, event):
    return m._callback(None, etype, event, None)


class TestPermissions:
    @pytest.mark.parametrize("value,expected", [(1, True), (0, False), (True, True), (None, False)])
    def test_input_monitoring(self, monkeypatch, value, expected):
        monkeypatch.setattr(hotkey.Quartz, "CGPreflightListenEventAccess", lambda: value)
        assert hotkey.has_input_monitoring() is expected

    def test_request_input_monitoring(self, monkeypatch):
        monkeypatch.setattr(hotkey.Quartz, "CGRequestListenEventAccess", lambda: 0)
        assert hotkey.request_input_monitoring() is False

    @pytest.mark.parametrize("value,expected", [(True, True), (False, False)])
    def test_accessibility(self, monkeypatch, value, expected):
        monkeypatch.setattr(hotkey.AS, "AXIsProcessTrusted", lambda: value)
        assert hotkey.has_accessibility() is expected

    def test_request_accessibility_asks_for_prompt(self, monkeypatch):
        seen = {}
        monkeypatch.setattr(hotkey.AS, "AXIsProcessTrustedWithOptions", lambda opts: seen.update(opts) or True)
        assert hotkey.request_accessibility() is True
        assert seen == {hotkey.AS.kAXTrustedCheckOptionPrompt: True}


class TestSpec:
    def test_globe_keycode(self):
        assert GLOBE_KEYCODE == 179  # the 🌐/fn key's own key event on Apple keyboards

    def test_fn_flag_is_secondary_fn(self):
        assert FN_MASK == Quartz.kCGEventFlagMaskSecondaryFn


class TestFnKeySetting:
    @pytest.mark.parametrize("code,out,expected", [
        (0, "0\n", True),
        (0, "0", True),
        (0, "2\n", False),  # emoji picker
        (0, "3\n", False),  # dictation
        (1, "", False),     # key never set: macOS default action
    ])
    def test_reads_defaults(self, monkeypatch, code, out, expected):
        monkeypatch.setattr(hotkey.subprocess, "run",
                            lambda *a, **kw: subprocess.CompletedProcess(a, code, stdout=out, stderr=""))
        assert hotkey.fn_key_does_nothing() is expected

    def test_runs_defaults_read_capturing_text(self, monkeypatch):
        seen = {}

        def run(cmd, **kw):
            seen.update(cmd=cmd, **kw)
            return subprocess.CompletedProcess(cmd, 0, stdout="0\n", stderr="")

        monkeypatch.setattr(hotkey.subprocess, "run", run)
        hotkey.fn_key_does_nothing()
        assert seen == {"cmd": ["defaults", "read", "com.apple.HIToolbox", "AppleFnUsageType"],
                        "capture_output": True, "text": True}


class TestFnFlag:
    def test_fn_press_and_release(self, monitor):
        assert cb(monitor, FLAGS_CHANGED, ev(63, FN_MASK)) is None  # swallowed
        assert monitor.fn_down is True
        assert cb(monitor, FLAGS_CHANGED, ev(63, 0)) is None
        assert monitor.calls == ["down", "up"] and monitor.fn_down is False

    def test_listen_only_passes_fn_through(self, monitor):
        monitor.active = False
        e = ev(63, FN_MASK)
        assert cb(monitor, FLAGS_CHANGED, e) is e
        assert monitor.calls == ["down"]

    def test_other_modifier_while_fn_held_is_ignored(self, monitor):
        cb(monitor, FLAGS_CHANGED, ev(63, FN_MASK))
        e = ev(56, FN_MASK | Quartz.kCGEventFlagMaskShift)
        assert cb(monitor, FLAGS_CHANGED, e) is e
        assert monitor.calls == ["down"]

    def test_other_modifier_without_fn_passes(self, monitor):
        e = ev(56, Quartz.kCGEventFlagMaskShift)
        assert cb(monitor, FLAGS_CHANGED, e) is e and monitor.calls == []


class TestGlobeKey:
    @pytest.mark.parametrize("etype", [KEY_DOWN, KEY_UP])
    def test_swallowed_when_active(self, monitor, etype):
        assert cb(monitor, etype, ev(GLOBE_KEYCODE)) is None
        assert monitor.calls == []  # not treated as a combo or shortcut

    @pytest.mark.parametrize("etype", [KEY_DOWN, KEY_UP])
    def test_passes_when_listen_only(self, monitor, etype):
        monitor.active = False
        e = ev(GLOBE_KEYCODE)
        assert cb(monitor, etype, e) is e

    def test_globe_while_fn_held_is_not_a_combo(self, monitor):
        cb(monitor, FLAGS_CHANGED, ev(63, FN_MASK))
        cb(monitor, KEY_DOWN, ev(GLOBE_KEYCODE, FN_MASK))
        assert "combo" not in monitor.calls


class TestKeys:
    def test_key_while_fn_held_is_combo_and_passes(self, monitor):
        cb(monitor, FLAGS_CHANGED, ev(63, FN_MASK))
        e = ev(123, FN_MASK)  # fn + left arrow
        assert cb(monitor, KEY_DOWN, e) is e
        assert monitor.calls == ["down", "combo"]

    def test_handled_key_swallowed_with_its_key_up(self, monitor):
        monitor.keys[49] = True
        assert cb(monitor, KEY_DOWN, ev(49)) is None
        assert cb(monitor, KEY_UP, ev(49)) is None
        e = ev(49)
        assert cb(monitor, KEY_UP, e) is e  # only the one matching key-up is swallowed

    def test_unhandled_key_passes(self, monitor):
        e = ev(0)
        assert cb(monitor, KEY_DOWN, e) is e and ("key", 0) in monitor.calls
        assert cb(monitor, KEY_UP, e) is e

    @pytest.mark.parametrize("flag", [Quartz.kCGEventFlagMaskCommand, Quartz.kCGEventFlagMaskControl,
                                      Quartz.kCGEventFlagMaskAlternate])
    def test_modified_keys_never_offered(self, monitor, flag):
        monitor.keys[49] = True
        e = ev(49, flag)  # e.g. cmd+space (Spotlight)
        assert cb(monitor, KEY_DOWN, e) is e
        assert ("key", 49) not in monitor.calls

    def test_shift_does_not_block_shortcuts(self, monitor):
        monitor.keys[49] = True
        assert cb(monitor, KEY_DOWN, ev(49, Quartz.kCGEventFlagMaskShift)) is None

    def test_listen_only_never_swallows_keys(self, monitor):
        monitor.active = False
        monitor.keys[49] = True
        e = ev(49)
        assert cb(monitor, KEY_DOWN, e) is e and ("key", 49) not in monitor.calls

    def test_no_on_key_handler(self, fake_events):
        m = FnMonitor(lambda: None, lambda: None, lambda: None)
        m.active = True
        e = ev(49)
        assert cb(m, KEY_DOWN, e) is e


class TestTapHealth:
    @pytest.mark.parametrize("etype", [Quartz.kCGEventTapDisabledByTimeout, Quartz.kCGEventTapDisabledByUserInput])
    def test_disabled_tap_is_reenabled(self, monitor, fake_events, etype):
        monitor._tap = "TAP"
        e = ev()
        assert cb(monitor, etype, e) is e
        assert fake_events == [("TAP", True)]


@pytest.fixture
def fake_tap_api(monkeypatch):
    """Spy for the Quartz event-tap API: records every call in order."""
    calls = []
    results = []  # queue of taps CGEventTapCreate returns (None = failure)

    def create(point, place, option, mask, callback, refcon):
        calls.append(("create", point, place, option, mask))
        return results.pop(0) if results else "TAP"

    q = hotkey.Quartz
    monkeypatch.setattr(q, "CGEventTapCreate", create)
    monkeypatch.setattr(q, "CFMachPortCreateRunLoopSource", lambda a, tap, order: calls.append(("source", tap, order)) or f"SRC-{tap}")
    monkeypatch.setattr(q, "CFRunLoopGetCurrent", lambda: "LOOP")
    monkeypatch.setattr(q, "CFRunLoopAddSource", lambda loop, src, mode: calls.append(("add", loop, src, mode)))
    monkeypatch.setattr(q, "CFRunLoopRemoveSource", lambda loop, src, mode: calls.append(("remove", loop, src, mode)))
    monkeypatch.setattr(q, "CFMachPortInvalidate", lambda tap: calls.append(("invalidate", tap)))
    monkeypatch.setattr(q, "CGEventTapEnable", lambda tap, on: calls.append(("enable", tap, on)))
    return calls, results


class TestInstall:
    def test_start_installs_active_hid_tap(self, fake_tap_api):
        calls, _ = fake_tap_api
        m = FnMonitor(None, None, None)
        assert m.start() is True and m.active is True and m._tap == "TAP"
        mask = (Quartz.CGEventMaskBit(FLAGS_CHANGED) | Quartz.CGEventMaskBit(KEY_DOWN)
                | Quartz.CGEventMaskBit(KEY_UP))
        assert calls == [
            ("create", Quartz.kCGHIDEventTap, Quartz.kCGHeadInsertEventTap, Quartz.kCGEventTapOptionDefault, mask),
            ("source", "TAP", 0),
            ("add", "LOOP", "SRC-TAP", Quartz.kCFRunLoopCommonModes),  # keeps firing during menus/drags
            ("enable", "TAP", True),
        ]

    def test_start_falls_back_to_listen_only_session_tap(self, fake_tap_api):
        calls, results = fake_tap_api
        results.extend([None, "LISTEN"])
        m = FnMonitor(None, None, None)
        assert m.start() is True and m.active is False and m._tap == "LISTEN"
        create = [c for c in calls if c[0] == "create"][1]
        assert create[1] == Quartz.kCGSessionEventTap and create[3] == Quartz.kCGEventTapOptionListenOnly
        assert ("enable", "LISTEN", True) in calls

    def test_start_fails_without_any_permission(self, fake_tap_api):
        calls, results = fake_tap_api
        results.extend([None, None])
        m = FnMonitor(None, None, None)
        assert m.start() is False and m._tap is None and m.active is False
        assert [c[0] for c in calls] == ["create", "create"]  # nothing half-installed

    def test_remove_tears_down_in_order(self, fake_tap_api):
        calls, _ = fake_tap_api
        m = FnMonitor(None, None, None)
        m._tap, m._source, m.active = "OLD", "SRC-OLD", True
        m._remove()
        assert calls == [("enable", "OLD", False), ("remove", "LOOP", "SRC-OLD", Quartz.kCFRunLoopCommonModes),
                         ("invalidate", "OLD")]
        assert (m._tap, m._source, m.active) == (None, None, False)

    def test_remove_without_tap_is_safe(self, fake_tap_api):
        calls, _ = fake_tap_api
        m = FnMonitor(None, None, None)
        m._remove()
        assert calls == [] and m._tap is None

    def test_upgrade_noop_when_already_active(self, fake_tap_api, monkeypatch):
        monkeypatch.setattr(hotkey, "has_accessibility", lambda: True)
        m = FnMonitor(None, None, None)
        m.active = True
        assert m.upgrade() is False and fake_tap_api[0] == []

    def test_upgrade_noop_without_accessibility(self, fake_tap_api, monkeypatch):
        monkeypatch.setattr(hotkey, "has_accessibility", lambda: False)
        assert FnMonitor(None, None, None).upgrade() is False and fake_tap_api[0] == []

    def test_upgrade_swaps_listen_tap_for_active(self, fake_tap_api, monkeypatch):
        calls, _ = fake_tap_api
        monkeypatch.setattr(hotkey, "has_accessibility", lambda: True)
        m = FnMonitor(None, None, None)
        m._tap, m._source, m.active = "OLD", "SRC-OLD", False
        assert m.upgrade() is True and m.active is True and m._tap == "TAP"
        assert ("invalidate", "OLD") in calls and ("enable", "TAP", True) in calls

    def test_upgrade_failure_restores_listen_tap(self, fake_tap_api, monkeypatch):
        calls, results = fake_tap_api
        monkeypatch.setattr(hotkey, "has_accessibility", lambda: True)
        results.extend([None, "LISTEN"])
        m = FnMonitor(None, None, None)
        m._tap, m._source = "OLD", "SRC"
        assert m.upgrade() is False and m.active is False and m._tap == "LISTEN"


# --- Custom dictation key (Settings > General > Shortcuts) ------------------------------

RIGHT_OPTION, F5 = 61, 96


class TestNormalizeTrigger:
    @pytest.mark.parametrize("bad", [None, "fn", {}, {"kind": "modifier", "keycode": 12},
                                     {"kind": "key", "keycode": GLOBE_KEYCODE}, {"kind": "key", "keycode": "x"},
                                     {"kind": "chord", "keycode": 5}])
    def test_malformed_means_fn(self, bad):
        assert hotkey.normalize_trigger(bad) == hotkey.FN_TRIGGER

    def test_valid_triggers_kept(self):
        assert hotkey.normalize_trigger({"kind": "modifier", "keycode": RIGHT_OPTION, "label": "Right ⌥"}) == \
            {"kind": "modifier", "keycode": RIGHT_OPTION, "label": "Right ⌥"}
        assert hotkey.normalize_trigger({"kind": "key", "keycode": F5})["label"] == "key"


class TestModifierTrigger:
    @pytest.fixture
    def m(self, monitor):
        monitor.set_trigger({"kind": "modifier", "keycode": RIGHT_OPTION, "label": "Right ⌥"})
        return monitor

    def test_press_and_release_swallowed(self, m):
        assert cb(m, FLAGS_CHANGED, ev(RIGHT_OPTION, Quartz.kCGEventFlagMaskAlternate | 0x40)) is None
        assert cb(m, FLAGS_CHANGED, ev(RIGHT_OPTION, 0)) is None
        assert m.calls == ["down", "up"]

    def test_left_option_passes_and_does_nothing(self, m):
        event = ev(58, Quartz.kCGEventFlagMaskAlternate | 0x20)
        assert cb(m, FLAGS_CHANGED, event) is event and m.calls == []

    def test_fn_no_longer_dictates(self, m):
        event = ev(63, FN_MASK)
        assert cb(m, FLAGS_CHANGED, event) is event and m.calls == []

    def test_globe_key_passes_when_fn_is_not_the_trigger(self, m):
        event = ev(GLOBE_KEYCODE)
        assert cb(m, KEY_DOWN, event) is event

    def test_key_while_held_is_a_combo(self, m):
        cb(m, FLAGS_CHANGED, ev(RIGHT_OPTION, 0x40))
        cb(m, KEY_DOWN, ev(0))
        assert m.calls == ["down", "combo"]


class TestKeyTrigger:
    @pytest.fixture
    def m(self, monitor):
        monitor.set_trigger({"kind": "key", "keycode": F5, "label": "F5"})
        return monitor

    def test_press_hold_release(self, m):
        assert cb(m, KEY_DOWN, ev(F5)) is None
        assert cb(m, KEY_DOWN, ev(F5, repeat=1)) is None  # auto-repeat while held
        assert cb(m, KEY_UP, ev(F5)) is None
        assert m.calls == ["down", "up"]

    def test_listen_only_passes_the_key(self, m):
        m.active = False
        event = ev(F5)
        assert cb(m, KEY_DOWN, event) is event and m.calls == ["down"]

    def test_other_key_while_held_is_a_combo(self, m):
        cb(m, KEY_DOWN, ev(F5))
        event = ev(0)
        assert cb(m, KEY_DOWN, event) is event and m.calls == ["down", "combo"]

    def test_fn_flag_ignored(self, m):
        event = ev(63, FN_MASK)
        assert cb(m, FLAGS_CHANGED, event) is event and m.calls == []


class TestSetTrigger:
    def test_switching_mid_press_releases(self, monitor):
        cb(monitor, FLAGS_CHANGED, ev(63, FN_MASK))
        monitor.set_trigger({"kind": "key", "keycode": F5})
        assert monitor.calls == ["down", "up"] and not monitor.fn_down

    def test_same_trigger_is_a_no_op(self, monitor):
        cb(monitor, FLAGS_CHANGED, ev(63, FN_MASK))
        monitor.set_trigger(hotkey.FN_TRIGGER)
        assert monitor.calls == ["down"] and monitor.fn_down


class TestNoteShortcut:
    @pytest.fixture
    def m(self, monitor):
        monitor.on_note = lambda: monitor.calls.append("note")
        return monitor

    def test_option_m_opens_a_note_and_is_swallowed(self, m):
        assert cb(m, KEY_DOWN, ev(hotkey.KEY_M, Quartz.kCGEventFlagMaskAlternate)) is None
        assert cb(m, KEY_UP, ev(hotkey.KEY_M)) is None
        assert m.calls == ["note"]

    def test_plain_m_and_cmd_option_m_pass(self, m):
        plain = ev(hotkey.KEY_M)
        assert cb(m, KEY_DOWN, plain) is plain
        cmd = ev(hotkey.KEY_M, Quartz.kCGEventFlagMaskAlternate | CMD)
        assert cb(m, KEY_DOWN, cmd) is cmd
        assert "note" not in m.calls

    def test_auto_repeat_opens_once(self, m):
        cb(m, KEY_DOWN, ev(hotkey.KEY_M, Quartz.kCGEventFlagMaskAlternate))
        cb(m, KEY_DOWN, ev(hotkey.KEY_M, Quartz.kCGEventFlagMaskAlternate, repeat=1))
        assert m.calls == ["note"]


OPT, CTRL, SHIFT = Quartz.kCGEventFlagMaskAlternate, Quartz.kCGEventFlagMaskControl, Quartz.kCGEventFlagMaskShift


def switcher(fake_events, trigger):
    edges = []
    m = FnMonitor(lambda: edges.append("dictate"), lambda: edges.append("dictate-up"), lambda: None,
                  on_switch=edges.append, switch_trigger=trigger)
    m.active = True
    m.edges = edges
    return m


class TestSwitchTrigger:
    """Which app switcher keys are allowed: a key, one side of a modifier, or a combo."""

    @pytest.mark.parametrize("bad", [None, {}, {"kind": "fn", "keycode": 63}, {"kind": "modifier", "keycode": 1},
                                     {"kind": "combo", "mods": ["option"]}, {"kind": "combo", "mods": []},
                                     {"kind": "combo", "mods": ["hyper"], "keycode": 1},
                                     {"kind": "combo", "mods": ["option"], "keycode": GLOBE_KEYCODE}])
    def test_off_or_unusable(self, bad):
        assert hotkey.normalize_switch_trigger(bad) is None

    def test_never_the_dictation_key(self):
        right_opt = {"kind": "modifier", "keycode": 61, "label": "Right ⌥"}
        assert hotkey.normalize_switch_trigger(right_opt, dictation=right_opt) is None
        assert hotkey.normalize_switch_trigger(right_opt)["keycode"] == 61

    def test_combos_are_tidied(self):
        t = hotkey.normalize_switch_trigger({"kind": "combo", "mods": ["option", "control", "option"], "label": "⌃⌥"})
        assert t == {"kind": "combo", "mods": ["control", "option"], "keycode": None, "label": "⌃⌥"}
        assert hotkey.normalize_switch_trigger({"kind": "combo", "mods": ["option"], "keycode": 1})["keycode"] == 1


class TestSwitchKey:
    """The app switcher key's press and release, without disturbing dictation."""

    def test_single_key_down_up_swallowed_and_repeat_ignored(self, fake_events):
        m = switcher(fake_events, {"kind": "key", "keycode": 96, "label": "F5"})
        assert cb(m, KEY_DOWN, ev(96)) is None
        assert cb(m, KEY_DOWN, ev(96, repeat=1)) is None
        assert cb(m, KEY_UP, ev(96)) is None
        assert m.edges == ["down", "up"]

    def test_single_modifier_side_passes_through(self, fake_events):
        m = switcher(fake_events, {"kind": "modifier", "keycode": 61, "label": "Right ⌥"})
        e = ev(61, OPT | 0x40)
        assert cb(m, FLAGS_CHANGED, e) is e
        cb(m, FLAGS_CHANGED, ev(61, 0))
        cb(m, FLAGS_CHANGED, ev(58, OPT | 0x20))  # left ⌥ is someone else
        assert m.edges == ["down", "up"]

    def test_modifier_combo_needs_exactly_those_modifiers(self, fake_events):
        m = switcher(fake_events, {"kind": "combo", "mods": ["control", "option"], "label": "⌃⌥"})
        cb(m, FLAGS_CHANGED, ev(59, CTRL))  # ⌃ alone: nothing yet
        assert m.edges == []
        cb(m, FLAGS_CHANGED, ev(58, CTRL | OPT))
        cb(m, FLAGS_CHANGED, ev(58, CTRL | OPT))  # no change: no second down
        cb(m, FLAGS_CHANGED, ev(58, CTRL))
        assert m.edges == ["down", "up"]

    def test_key_combo_fires_only_with_its_modifiers(self, fake_events):
        m = switcher(fake_events, {"kind": "combo", "mods": ["option"], "keycode": 1, "label": "⌥S"})
        plain = ev(1, 0)
        assert cb(m, KEY_DOWN, plain) is plain  # S alone still types
        assert cb(m, KEY_DOWN, ev(1, OPT | SHIFT)) is not None  # ⌥⇧S isn't ours either
        assert cb(m, KEY_DOWN, ev(1, OPT)) is None
        cb(m, KEY_DOWN, ev(1, OPT, repeat=1))
        cb(m, KEY_UP, ev(1, OPT))
        assert m.edges == ["down", "up"]

    def test_a_shortcut_with_the_switch_modifier_held_is_dropped(self, fake_events):
        m = switcher(fake_events, {"kind": "combo", "mods": ["command", "option"], "label": "⌘⌥"})
        cb(m, FLAGS_CHANGED, ev(55, CMD | OPT))
        cb(m, KEY_DOWN, ev(17, CMD | OPT))  # ⌘⌥T: a real shortcut
        cb(m, FLAGS_CHANGED, ev(55, 0))
        assert m.edges == ["down", "combo"]

    def test_dictation_still_works_beside_it(self, fake_events):
        m = switcher(fake_events, {"kind": "key", "keycode": 96, "label": "F5"})
        cb(m, FLAGS_CHANGED, ev(63, FN_MASK))
        cb(m, FLAGS_CHANGED, ev(63, 0))
        assert m.edges == ["dictate", "dictate-up"]

    def test_changing_the_key_drops_a_press_in_progress(self, fake_events):
        m = switcher(fake_events, {"kind": "key", "keycode": 96, "label": "F5"})
        cb(m, KEY_DOWN, ev(96))
        m.set_switch_trigger(None)
        assert m.edges == ["down", "combo"] and m.switch_trigger is None
        assert cb(m, KEY_DOWN, ev(96)) is not None  # off: F5 is just F5 again
        m.set_switch_trigger(None)  # unchanged: nothing happens

    def test_off_without_a_handler(self, fake_events):
        m = FnMonitor(lambda: None, lambda: None, lambda: None, switch_trigger={"kind": "key", "keycode": 96})
        e = ev(96)
        m.active = True
        assert cb(m, KEY_DOWN, e) is e


class TestAutoEnterKey:
    """⌃⌥Return (by default) turns Auto-Enter on or off; the app in front never sees it."""

    @pytest.fixture
    def m(self, monitor):
        monitor.on_toggle = lambda: monitor.calls.append("toggle")
        monitor.set_toggle_trigger(hotkey.DEFAULT_AUTO_ENTER_KEY)
        return monitor

    def test_press_toggles_and_is_swallowed(self, m):
        assert cb(m, KEY_DOWN, ev(hotkey.KEY_RETURN, CTRL | OPT)) is None
        assert cb(m, KEY_UP, ev(hotkey.KEY_RETURN)) is None
        assert m.calls == ["toggle"]

    def test_return_alone_or_with_other_keys_types_as_usual(self, m):
        for flags in (0, CMD, CTRL, OPT, CTRL | OPT | SHIFT):
            e = ev(hotkey.KEY_RETURN, flags)
            assert cb(m, KEY_DOWN, e) is e
        assert "toggle" not in m.calls

    def test_held_key_toggles_once(self, m):
        cb(m, KEY_DOWN, ev(hotkey.KEY_RETURN, CTRL | OPT))
        cb(m, KEY_DOWN, ev(hotkey.KEY_RETURN, CTRL | OPT, repeat=1))
        assert m.calls == ["toggle"]

    def test_off(self, m):
        m.set_toggle_trigger(None)
        e = ev(hotkey.KEY_RETURN, CTRL | OPT)
        assert cb(m, KEY_DOWN, e) is e and "toggle" not in m.calls

    @pytest.mark.parametrize("trigger", [None, {"kind": "key", "keycode": 36}, {"kind": "combo", "mods": ["control"], "keycode": None},
                                         {"kind": "combo", "mods": [], "keycode": 36}])
    def test_only_a_key_with_modifiers_is_usable(self, trigger):
        assert hotkey.normalize_toggle_trigger(trigger) is None
