"""The functions that start things: app.main's wiring, its helpers, the models CLI, and the
few methods only reached from AppKit or the meeting worker loop."""

import io

import numpy as np
import pytest

from mispr import app, cleanup, host, meeting, models, onboarding, transcribe


# --- app.main ---------------------------------------------------------------------------------

class FakeNSApp:
    def __init__(self):
        self.policy = self.icon = self.menu = self.delegate = None

    def setActivationPolicy_(self, policy):
        self.policy = policy

    def setApplicationIconImage_(self, icon):
        self.icon = icon

    def setMainMenu_(self, menu):
        self.menu = menu

    def setDelegate_(self, delegate):
        self.delegate = delegate


@pytest.fixture
def wired(monkeypatch):
    """Run app.main with every AppKit, hardware, and event-loop call replaced."""
    calls = {"loop": 0, "setup_shown": 0, "connected": None}
    fake_app = FakeNSApp()

    class Widget:
        settings = type("S", (), {"hotkey": {"kind": "fn"}, "switch_hotkey": {"kind": "key", "keycode": 96}})()
        sounds = type("Snd", (), {"play": lambda self, name: None})()
        started = 0

        def start(self):
            Widget.started += 1

        fn_down = fn_up = fn_combo = handle_key = request_note = switch_key = lambda self, *a: None

    class Fn:
        def __init__(self, *args, trigger=None, on_note=None, **kw):
            self.args, self.trigger, self.on_note = args, trigger, on_note
            self._tap, self.active = object(), True

    monkeypatch.setattr(app, "_single_instance_lock", lambda: "lock")
    monkeypatch.setattr(app, "_brand_process", lambda: None)
    monkeypatch.setattr(app, "NSApplication", type("A", (), {"sharedApplication": staticmethod(lambda: fake_app)}))
    monkeypatch.setattr(app, "_app_icon", lambda: "icon")
    monkeypatch.setattr(app, "WidgetController", Widget)
    monkeypatch.setattr(app.hotkey, "FnMonitor", Fn)
    monkeypatch.setattr(app, "_status_item", lambda: "status")
    monkeypatch.setattr(app, "_install_shutdown", lambda status, widget: calls.setdefault("shutdown", (status, widget)))
    monkeypatch.setattr(app, "add_setup_menu_item", lambda status, opener: calls.setdefault("menu_item", opener) and "actions")
    monkeypatch.setattr(app, "_setup_flow", lambda widget: type("F", (), {"needed": lambda self: calls.get("needed", False)})())
    monkeypatch.setattr(app, "make_setup_opener", lambda widget: lambda: calls.__setitem__("setup_shown", calls["setup_shown"] + 1))
    monkeypatch.setattr(app, "maintain_hotkey", lambda fn: None)
    monkeypatch.setattr(app, "_connect_host", lambda a, w, opener, fn: calls.__setitem__("connected", (a, w, fn)))
    class Timer:  # Python stand-in: ObjC class methods can't be monkeypatched
        @staticmethod
        def scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(*args):
            calls["timer"] = args
            return "timer"

    monkeypatch.setattr(app, "NSTimer", Timer)
    monkeypatch.setattr(app.AppHelper, "runEventLoop", lambda **kw: calls.__setitem__("loop", calls["loop"] + 1))
    monkeypatch.setattr(app, "_keepalive", [])
    return calls, fake_app, Widget


class TestMain:
    def test_standalone_is_a_dock_app_with_its_own_menu(self, wired, monkeypatch):
        calls, fake_app, Widget = wired
        monkeypatch.delenv("MISPR_HOSTED", raising=False)
        app.main()
        assert fake_app.policy == app.NSApplicationActivationPolicyRegular
        assert fake_app.icon == "icon" and fake_app.menu is not None and fake_app.delegate is not None
        assert calls["connected"] is None and Widget.started == 1 and calls["loop"] == 1
        assert calls["timer"][0] == 1.0  # the fn keeper ticks every second

    def test_hosted_hands_the_dock_to_the_swift_app(self, wired, monkeypatch):
        calls, fake_app, _ = wired
        monkeypatch.setenv("MISPR_HOSTED", "1")
        monkeypatch.setattr(host, "open_channel", lambda: calls.setdefault("channel", True))
        app.main()
        assert fake_app.policy == app.NSApplicationActivationPolicyAccessory
        assert fake_app.menu is None and calls["connected"] is not None and calls["channel"]

    def test_fn_monitor_uses_the_chosen_key_and_option_m(self, wired, monkeypatch):
        calls, _, _ = wired
        monkeypatch.delenv("MISPR_HOSTED", raising=False)
        captured = {}
        original = app.hotkey.FnMonitor
        monkeypatch.setattr(app.hotkey, "FnMonitor", lambda *a, **kw: captured.update(kw) or original(*a, **kw))
        app.main()
        assert captured["trigger"] == {"kind": "fn"} and captured["on_note"] is not None
        assert captured["switch_trigger"] == {"kind": "key", "keycode": 96} and captured["on_switch"] is not None

    def test_setup_window_opens_only_when_something_is_missing(self, wired, monkeypatch):
        calls, _, _ = wired
        monkeypatch.delenv("MISPR_HOSTED", raising=False)
        app.main()
        assert calls["setup_shown"] == 0
        calls["needed"] = True
        app.main()
        assert calls["setup_shown"] == 1

    def test_warns_when_fn_cannot_start(self, wired, monkeypatch, capsys):
        monkeypatch.delenv("MISPR_HOSTED", raising=False)

        class NoTap:
            def __init__(self, *a, **kw):
                self._tap, self.active = None, False

        monkeypatch.setattr(app.hotkey, "FnMonitor", NoTap)
        app.main()
        assert "fn is off until Accessibility is allowed" in capsys.readouterr().err


class TestSetupOpener:
    def make(self, monkeypatch):
        created = []

        class Window:
            def __init__(self, flow, play, on_finish=lambda: None):
                self.flow, self.play, self.shown, self.on_finish = flow, play, 0, on_finish
                self.window = type("W", (), {"visible": True, "isVisible": lambda s: s.visible})()
                created.append(self)

            def show(self):
                self.shown += 1

        widget = type("Widget", (), {"sounds": type("S", (), {"play": lambda s, n: None})()})()
        monkeypatch.setattr(app, "_setup_flow", lambda w: "flow")
        return app.make_setup_opener(widget, window_class=Window), created

    def test_reuses_the_open_window(self, monkeypatch):
        opener, created = self.make(monkeypatch)
        opener()
        opener()
        assert len(created) == 1 and created[0].shown == 2 and created[0].flow == "flow"

    def test_makes_a_new_one_after_it_was_closed(self, monkeypatch):
        opener, created = self.make(monkeypatch)
        opener()
        created[0].window.visible = False
        opener()
        assert len(created) == 2


class TestFnKeeper:
    def test_logs_only_changes(self, monkeypatch):
        changes = iter([None, "upgraded"])
        monkeypatch.setattr(app, "maintain_hotkey", lambda fn: next(changes))
        out = io.StringIO()
        keep = app.fn_keeper(type("Fn", (), {"active": True})(), log=out)
        keep()
        assert out.getvalue() == ""
        keep()
        assert out.getvalue() == "mispr: fn tap upgraded (active)\n"


# --- models CLI -------------------------------------------------------------------------------

class TestModelsCli:
    def test_prints_every_five_percent_once(self):
        out = io.StringIO()
        report = models.progress_printer(out)
        for pct in (0, 3, 4, 5, 5, 6, 10):  # 3, 4, 6: not on a 5% step; the second 5: already shown
            report(pct * 10_000_000, 1_000_000_000)
        assert out.getvalue().splitlines() == ["0% (0 / 1000 MB)", "5% (50 / 1000 MB)", "10% (100 / 1000 MB)"]

    def test_downloads_the_named_models(self):
        asked = []
        paths = models.cli(["cleanup"], ensure=lambda spec, progress: asked.append(spec) or "path")
        assert asked == [models.CLEANUP_MODEL] and paths == ["path"]

    def test_meeting_models_by_name(self):
        asked = []
        models.cli(["preview", "speakers"], ensure=lambda spec, progress: asked.append(spec))
        assert asked == [models.PREVIEW_MODEL, models.SPEAKER_MODEL]

    def test_defaults_to_both(self):
        asked = []
        models.cli([], ensure=lambda spec, progress: asked.append(spec))
        assert asked == [models.DEFAULT_MODEL, models.CLEANUP_MODEL]


# --- methods reached only from AppKit or worker threads ----------------------------------------

def test_cleaner_complete_returns_the_reply():
    class Llm:
        def create_chat_completion(self, messages, max_tokens, temperature):
            self.args = (messages, max_tokens, temperature)
            return {"choices": [{"message": {"content": "Summary."}}]}

    c = cleanup.Cleaner()
    c._llm = Llm()
    c._ready.set()
    assert c.complete([{"role": "user", "content": "hi"}], max_tokens=50) == "Summary."
    assert c._llm.args[1:] == (50, 0.2)


def test_cleaner_complete_without_a_model_is_none():
    c = cleanup.Cleaner()
    c._ready.set()
    assert c.complete([]) is None


def test_transcriber_transcribe_runs_on_the_calling_thread(monkeypatch):
    t = transcribe.Transcriber()
    monkeypatch.setattr(t, "_transcribe", lambda audio: f"{len(audio)} samples")
    assert t.transcribe(np.zeros(16000, dtype=np.float32)) == "16000 samples"


def test_meeting_worker_keeps_going_after_a_failed_job(capsys):
    jobs = []
    worker = meeting.MeetingWorker(None, None, lambda *a, **k: None, start=lambda target, name: None)

    class Stop(BaseException):
        pass

    def boom():
        raise ValueError("bad chunk")

    queue = iter([boom, lambda: jobs.append("ran"), lambda: (_ for _ in ()).throw(Stop())])
    worker._jobs.get = lambda: next(queue)
    with pytest.raises(Stop):
        worker._run()
    assert jobs == ["ran"] and "meeting job failed: bad chunk" in capsys.readouterr().err


def test_widget_view_draws_through_its_controller():
    from AppKit import NSBitmapImageRep, NSGraphicsContext, NSMakeRect
    import mispr.widget as W

    drawn = []
    view = W.WidgetView.alloc().initWithFrame_(NSMakeRect(0, 0, 10, 10))
    view.ctrl = type("C", (), {"draw": lambda self: drawn.append(True)})()
    rep = NSBitmapImageRep.alloc().initWithBitmapDataPlanes_pixelsWide_pixelsHigh_bitsPerSample_samplesPerPixel_hasAlpha_isPlanar_colorSpaceName_bytesPerRow_bitsPerPixel_(
        None, 10, 10, 8, 4, True, False, "NSDeviceRGBColorSpace", 0, 0)
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.setCurrentContext_(NSGraphicsContext.graphicsContextWithBitmapImageRep_(rep))
    try:
        view.drawRect_(NSMakeRect(0, 0, 10, 10))
    finally:
        NSGraphicsContext.restoreGraphicsState()
    assert drawn == [True]


def test_setup_window_show_brings_it_forward_and_starts_refreshing(monkeypatch):
    flow = onboarding.SetupFlow(onboarding.default_permissions(), models_ready=lambda: True)
    w = onboarding.SetupWindow(flow)
    activated = []
    monkeypatch.setattr("AppKit.NSApp", lambda: type("App", (), {"activateIgnoringOtherApps_": lambda s, f: activated.append(f)})())
    try:
        w.show()
        first = w.timer
        w.show()  # a second show doesn't add another timer
        assert w.window.isVisible() and activated == [True, True] and w.timer is first and first is not None
    finally:
        w.close()
    assert w.timer is None and not w.window.isVisible()


def test_finishing_setup_tells_the_app(monkeypatch):
    finished = []
    made = []

    class Window:
        def __init__(self, flow, play, on_finish):
            self.on_finish = on_finish
            self.window = type("W", (), {"isVisible": lambda s: True})()
            made.append(self)

        def show(self):
            pass

    widget = type("Widget", (), {"sounds": type("S", (), {"play": lambda s, n: None})(),
                                 "on_setup_finished": staticmethod(lambda: finished.append(True))})()
    monkeypatch.setattr(app, "_setup_flow", lambda w: "flow")
    app.make_setup_opener(widget, window_class=Window)()
    made[0].on_finish()
    assert finished == [True]
