import subprocess

import pytest
import Quartz

from whispr import hotkey
from whispr.hotkey import FN_MASK, GLOBE_KEYCODE, FnMonitor

FLAGS_CHANGED, KEY_DOWN, KEY_UP = Quartz.kCGEventFlagsChanged, Quartz.kCGEventKeyDown, Quartz.kCGEventKeyUp
CMD = Quartz.kCGEventFlagMaskCommand


def ev(keycode=0, flags=0):
    return {"keycode": keycode, "flags": flags}


@pytest.fixture
def fake_events(monkeypatch):
    enabled = []
    monkeypatch.setattr(hotkey.Quartz, "CGEventGetIntegerValueField", lambda e, field: e["keycode"])
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
    log = {"created": [], "removed": 0, "invalidated": 0}
    results = []  # queue of taps CGEventTapCreate returns (None = failure)

    def create(point, place, option, mask, callback, refcon):
        log["created"].append((point, option, mask))
        return results.pop(0) if results else "TAP"

    monkeypatch.setattr(hotkey.Quartz, "CGEventTapCreate", create)
    monkeypatch.setattr(hotkey.Quartz, "CFMachPortCreateRunLoopSource", lambda a, tap, o: f"SRC-{tap}")
    monkeypatch.setattr(hotkey.Quartz, "CFRunLoopAddSource", lambda *a: None)
    monkeypatch.setattr(hotkey.Quartz, "CFRunLoopRemoveSource", lambda *a: log.__setitem__("removed", log["removed"] + 1))
    monkeypatch.setattr(hotkey.Quartz, "CFMachPortInvalidate", lambda tap: log.__setitem__("invalidated", log["invalidated"] + 1))
    monkeypatch.setattr(hotkey.Quartz, "CGEventTapEnable", lambda tap, on: None)
    log["results"] = results
    return log


class TestInstall:
    def test_start_prefers_active_hid_tap(self, fake_tap_api):
        m = FnMonitor(None, None, None)
        assert m.start() is True and m.active is True
        point, option, mask = fake_tap_api["created"][0]
        assert point == Quartz.kCGHIDEventTap and option == Quartz.kCGEventTapOptionDefault
        for t in (FLAGS_CHANGED, KEY_DOWN, KEY_UP):
            assert mask & Quartz.CGEventMaskBit(t)

    def test_start_falls_back_to_listen_only(self, fake_tap_api):
        fake_tap_api["results"].extend([None, "LISTEN"])
        m = FnMonitor(None, None, None)
        assert m.start() is True and m.active is False
        point, option, _ = fake_tap_api["created"][1]
        assert point == Quartz.kCGSessionEventTap and option == Quartz.kCGEventTapOptionListenOnly

    def test_start_fails_without_any_permission(self, fake_tap_api):
        fake_tap_api["results"].extend([None, None])
        m = FnMonitor(None, None, None)
        assert m.start() is False and m._tap is None

    def test_upgrade_noop_when_already_active(self, fake_tap_api, monkeypatch):
        monkeypatch.setattr(hotkey, "has_accessibility", lambda: True)
        m = FnMonitor(None, None, None)
        m.active = True
        assert m.upgrade() is False and fake_tap_api["created"] == []

    def test_upgrade_noop_without_accessibility(self, fake_tap_api, monkeypatch):
        monkeypatch.setattr(hotkey, "has_accessibility", lambda: False)
        assert FnMonitor(None, None, None).upgrade() is False

    def test_upgrade_swaps_listen_tap_for_active(self, fake_tap_api, monkeypatch):
        monkeypatch.setattr(hotkey, "has_accessibility", lambda: True)
        m = FnMonitor(None, None, None)
        m._tap, m._source, m.active = "OLD", "SRC-OLD", False
        assert m.upgrade() is True and m.active is True
        assert fake_tap_api["removed"] == 1 and fake_tap_api["invalidated"] == 1

    def test_upgrade_failure_restores_listen_tap(self, fake_tap_api, monkeypatch):
        monkeypatch.setattr(hotkey, "has_accessibility", lambda: True)
        fake_tap_api["results"].extend([None, "LISTEN"])
        m = FnMonitor(None, None, None)
        m._tap, m._source = "OLD", "SRC"
        assert m.upgrade() is False and m.active is False and m._tap == "LISTEN"

    def test_remove_without_tap_is_safe(self, fake_tap_api):
        m = FnMonitor(None, None, None)
        m._remove()
        assert m._tap is None and fake_tap_api["removed"] == 0
