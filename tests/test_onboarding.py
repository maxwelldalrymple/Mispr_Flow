import pytest
from AppKit import NSAppearance, NSBitmapImageRep, NSColor, NSGraphicsContext, NSRectFill

from conftest import FakeRecorder  # noqa: F401  (keeps conftest fakes importable here)
from mispr import onboarding as o
from mispr import settings as st
from mispr.onboarding import MODELS, PERMISSIONS, READY, WELCOME, SetupFlow, SetupWindow


# --- Test doubles --------------------------------------------------------------------------

class Perms:
    """Controllable permissions: `granted[key]` drives check(); requests are recorded."""

    def __init__(self, granted=None, prompt_available=True):
        self.granted = {"microphone": False, "accessibility": False, "screen_audio": False, "finder": False}
        self.granted.update(granted or {})
        self.requests = []
        self.prompt_available = prompt_available
        self.list = [
            o.Permission(p.key, p.title, p.detail, p.symbol, p.required,
                         (lambda k=p.key: self.granted[k]),
                         (lambda k=p.key: self.requests.append(k)),
                         p.pane, prompt_available=lambda: self.prompt_available)
            for p in o.default_permissions()
        ]

    def grant_required(self):
        self.granted.update(microphone=True, accessibility=True)


class Models:
    def __init__(self, ready=False, progress=0.0, error=None):
        self.ready, self.progress, self.error, self.retries = ready, progress, error, 0

    def retry(self):
        self.retries += 1


def make_flow(perms=None, models=None, onboarded=False):
    perms = perms or Perms()
    models = models or Models()
    flow = SetupFlow(perms.list, models_ready=lambda: models.ready, model_progress=lambda: models.progress,
                     model_error=lambda: models.error, retry_models=models.retry,
                     settings=st.Settings(onboarded=onboarded))
    return flow, perms, models


@pytest.fixture
def opened_panes(monkeypatch):
    panes = []
    monkeypatch.setattr(o, "open_pane", panes.append)
    return panes


# --- Permissions list --------------------------------------------------------------------------

class TestDefaultPermissions:
    def test_keys_and_requirements(self):
        perms = {p.key: p for p in o.default_permissions()}
        assert list(perms) == ["microphone", "accessibility", "screen_audio", "finder"]
        assert perms["microphone"].required and perms["accessibility"].required
        assert not perms["screen_audio"].required  # only for meeting notes

    def test_settings_panes(self):
        panes = {p.key: p.pane for p in o.default_permissions()}
        assert panes == {"microphone": "Privacy_Microphone", "accessibility": "Privacy_Accessibility",
                         "screen_audio": "Privacy_ScreenCapture", "finder": "Privacy_Automation"}

    def test_every_permission_explains_why(self):
        for p in o.default_permissions():
            assert p.title and len(p.detail) > 30 and p.symbol


class FakeAV:
    AVMediaTypeAudio = "soun"

    def __init__(self, status):
        self.status, self.requested = status, []
        av = self

        class Device:
            @staticmethod
            def authorizationStatusForMediaType_(kind):
                assert kind == "soun"
                return av.status

            @staticmethod
            def requestAccessForMediaType_completionHandler_(kind, handler):
                av.requested.append(kind)
                handler(True)

        self.AVCaptureDevice = Device


class TestPermissionWrappers:
    @pytest.mark.parametrize("status,granted,undecided", [(0, False, True), (1, False, False),
                                                          (2, False, False), (3, True, False)])
    def test_microphone_status(self, monkeypatch, status, granted, undecided):
        monkeypatch.setattr(o, "_av", lambda: FakeAV(status))
        assert o.microphone_granted() is granted and o.microphone_undecided() is undecided

    def test_microphone_request_asks_for_audio(self, monkeypatch):
        av = FakeAV(0)
        monkeypatch.setattr(o, "_av", lambda: av)
        o.request_microphone()
        assert av.requested == ["soun"]

    @pytest.mark.parametrize("value,expected", [(1, True), (0, False)])
    def test_screen_audio(self, monkeypatch, value, expected):
        monkeypatch.setattr(o.Quartz, "CGPreflightScreenCaptureAccess", lambda: value)
        monkeypatch.setattr(o.Quartz, "CGRequestScreenCaptureAccess", lambda: value)
        assert o.screen_audio_granted() is expected and o.request_screen_audio() is expected

    def test_open_pane_url(self, monkeypatch):
        opened = []

        class Workspace:
            @staticmethod
            def sharedWorkspace():
                return Workspace()

            def openURL_(self, url):
                opened.append(str(url.absoluteString()))

        monkeypatch.setattr(o, "NSWorkspace", Workspace)
        o.open_pane("Privacy_Microphone")
        assert opened == ["x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone"]


# --- Flow logic --------------------------------------------------------------------------------

class TestWhenToShow:
    def test_first_run_starts_at_welcome(self):
        flow, _, _ = make_flow(onboarded=False)
        assert flow.needed() and flow.step == WELCOME

    def test_revoked_required_permission_reopens_at_permissions(self):
        flow, _, _ = make_flow(Perms({"microphone": True}), Models(ready=True), onboarded=True)
        assert flow.needed() and flow.step == PERMISSIONS

    def test_missing_models_reopen_at_models(self):
        perms = Perms()
        perms.grant_required()
        flow, _, _ = make_flow(perms, Models(ready=False), onboarded=True)
        assert flow.needed() and flow.step == MODELS

    def test_complete_setup_is_not_shown(self):
        perms = Perms()
        perms.grant_required()
        flow, _, _ = make_flow(perms, Models(ready=True), onboarded=True)
        assert not flow.needed() and flow.step == WELCOME  # reopening from the menu starts at Welcome

    def test_missing_optional_permission_does_not_reopen(self):
        perms = Perms()
        perms.grant_required()  # screen audio still off
        flow, _, _ = make_flow(perms, Models(ready=True), onboarded=True)
        assert not flow.needed()


class TestNavigation:
    def test_welcome_can_always_continue(self):
        flow, _, _ = make_flow()
        assert flow.can_advance() and flow.advance() == PERMISSIONS

    def test_permissions_block_until_required_granted(self):
        flow, perms, _ = make_flow()
        flow.step = PERMISSIONS
        assert not flow.can_advance() and flow.advance() == PERMISSIONS
        perms.granted["microphone"] = True
        assert not flow.can_advance()
        perms.granted["accessibility"] = True
        assert flow.can_advance() and flow.advance() == MODELS

    def test_optional_permission_never_blocks(self):
        flow, perms, _ = make_flow()
        flow.step = PERMISSIONS
        perms.grant_required()
        assert perms.granted["screen_audio"] is False and flow.can_advance()

    def test_models_block_until_ready(self):
        flow, _, models = make_flow()
        flow.step = MODELS
        assert flow.advance() == MODELS
        models.ready = True
        assert flow.advance() == READY

    def test_ready_is_the_last_step(self):
        flow, _, _ = make_flow()
        flow.step = READY
        assert flow.can_advance() and flow.advance() == READY

    def test_back_stops_at_welcome(self):
        flow, _, _ = make_flow()
        flow.step = MODELS
        assert flow.back() == PERMISSIONS and flow.back() == WELCOME and flow.back() == WELCOME

    def test_missing_required_lists_keys_in_order(self):
        flow, perms, _ = make_flow()
        assert flow.missing_required() == ["microphone", "accessibility"]
        perms.granted["microphone"] = True
        assert flow.missing_required() == ["accessibility"]

    def test_granted_reports_every_permission(self):
        flow, perms, _ = make_flow(Perms({"screen_audio": True}))
        assert flow.granted() == {"microphone": False, "accessibility": False, "screen_audio": True, "finder": False}

    def test_finish_marks_onboarded_and_saves(self):
        flow, _, _ = make_flow()
        flow.finish()
        assert flow.settings.onboarded is True and st.load().onboarded is True


class TestAllow:
    def test_first_click_shows_system_prompt(self, opened_panes):
        flow, perms, _ = make_flow()
        assert flow.allow("accessibility") == "prompted"
        assert perms.requests == ["accessibility"] and opened_panes == []

    def test_second_click_opens_system_settings(self, opened_panes):
        flow, perms, _ = make_flow()
        flow.allow("accessibility")
        assert flow.allow("accessibility") == "opened settings"
        assert perms.requests == ["accessibility"] and opened_panes == ["Privacy_Accessibility"]

    def test_denied_microphone_goes_straight_to_settings(self, opened_panes):
        flow, perms, _ = make_flow(Perms(prompt_available=False))
        assert flow.allow("microphone") == "opened settings"
        assert perms.requests == [] and opened_panes == ["Privacy_Microphone"]

    def test_already_granted_does_nothing(self, opened_panes):
        flow, perms, _ = make_flow(Perms({"microphone": True}))
        assert flow.allow("microphone") == "granted" and perms.requests == [] and opened_panes == []

    def test_unknown_key_raises(self):
        flow, _, _ = make_flow()
        with pytest.raises(StopIteration):
            flow.allow("camera")


class TestModelStatus:
    def test_downloading(self):
        flow, _, _ = make_flow(models=Models(progress=0.42))
        assert flow.model_status() == ("downloading", 0.42, "42% · 1.3 of 3.1 GB")

    def test_error(self):
        flow, _, _ = make_flow(models=Models(progress=0.3, error="network unreachable"))
        assert flow.model_status() == ("error", 0.3, "Download failed: network unreachable")

    def test_ready_wins_over_stale_error(self):
        flow, _, _ = make_flow(models=Models(ready=True, error="old"))
        assert flow.model_status() == ("ready", 1.0, "Models installed and verified.")


# --- Window ------------------------------------------------------------------------------------

played = []


@pytest.fixture
def window():
    played.clear()
    flow, perms, models = make_flow()
    finished = []
    w = SetupWindow(flow, on_finish=lambda: finished.append(True), play=played.append)
    w.window.setAppearance_(NSAppearance.appearanceNamed_("NSAppearanceNameAqua"))
    yield w, flow, perms, models, finished
    w.window.orderOut_(None)


def go(w, step):
    w.flow.step = step
    w.render()


class TestWindow:
    def test_opens_on_the_active_space(self, window):
        behavior = window[0].window.collectionBehavior()
        assert behavior & o.NSWindowCollectionBehaviorMoveToActiveSpace
        assert behavior & o.NSWindowCollectionBehaviorFullScreenAuxiliary

    def test_title_and_size(self, window):
        w = window[0]
        f = w.window.contentView().frame()
        assert w.window.title() == "Mispr Flow Setup" and (f.size.width, f.size.height) == (560, 520)

    @pytest.mark.parametrize("step,label,has_back", [
        (WELCOME, "Get Started", False), (PERMISSIONS, "Continue", True),
        (MODELS, "Continue", True), (READY, "Start Dictating", False)])
    def test_footer_buttons(self, window, step, label, has_back):
        w = window[0]
        go(w, step)
        assert w.continue_button.title() == label and (w.back_button is not None) is has_back
        assert w.continue_button.keyEquivalent() == "\r"  # Return continues

    def test_permission_rows_track_grants_live(self, window):
        w, flow, perms, _, _ = window
        go(w, PERMISSIONS)
        status, button = w.rows["microphone"]
        assert status.isHidden() and not button.isHidden() and not w.continue_button.isEnabled()
        perms.grant_required()
        w.refresh()  # the 0.5 s timer does this in the app
        assert not status.isHidden() and button.isHidden() and w.continue_button.isEnabled()

    def test_allow_button_targets_its_permission(self, window, opened_panes):
        w, _, perms, _, _ = window
        go(w, PERMISSIONS)
        w.rows["accessibility"][1].performClick_(None)
        assert perms.requests == ["accessibility"]

    def test_continue_and_back_move_between_pages(self, window):
        w, flow, perms, _, _ = window
        w.continue_button.performClick_(None)
        assert flow.step == PERMISSIONS
        w.back_button.performClick_(None)
        assert flow.step == WELCOME

    def test_model_page_progress_and_retry(self, window):
        w, flow, _, models, _ = window
        go(w, MODELS)
        bar, status, retry = w.model_widgets
        models.progress = 0.5
        w.refresh()
        assert bar.doubleValue() == 0.5 and status.stringValue() == "50% · 1.6 of 3.1 GB" and retry.isHidden()
        models.error = "offline"
        w.refresh()
        assert not retry.isHidden() and "offline" in status.stringValue()
        retry.performClick_(None)
        assert models.retries == 1
        models.ready = True
        w.refresh()
        assert status.stringValue() == "✓ Models installed and verified." and w.continue_button.isEnabled()

    def test_start_dictating_finishes_and_closes(self, window):
        w, flow, _, _, finished = window
        go(w, READY)
        w.continue_button.performClick_(None)
        assert finished == [True] and flow.settings.onboarded is True and not w.window.isVisible()

    def test_granting_a_permission_plays_success_once(self, window):
        w, flow, perms, _, _ = window
        go(w, PERMISSIONS)
        w.refresh()
        assert played == []
        perms.grant_required()
        w.refresh()
        w.refresh()
        assert played == ["success"]

    def test_already_granted_permissions_are_silent(self, window):
        w, flow, perms, _, _ = window
        perms.grant_required()
        quiet = SetupWindow(flow, play=played.append)
        quiet.refresh()
        quiet.window.orderOut_(None)
        assert played == []

    def test_finishing_setup_plays_achievement(self, window):
        w = window[0]
        go(w, READY)
        w.continue_button.performClick_(None)
        assert played == ["achievement"]

    def test_close_stops_refresh_timer(self, window):
        w = window[0]

        class Timer:
            invalidated = False

            def invalidate(self):
                Timer.invalidated = True

        w.timer = Timer()
        w.close()
        assert Timer.invalidated and w.timer is None

    def test_refresh_selector_calls_owner(self, window):
        w = window[0]
        calls = []
        w.refresh = lambda: calls.append(1)
        w.actions.refresh_(None)
        assert calls == [1]


# --- Golden images ------------------------------------------------------------------------------

def snapshot(w, dark=False):
    """Render the window's content with its background (offscreen caching skips the window
    background, which would make dark-mode text invisible)."""
    name = "NSAppearanceNameDarkAqua" if dark else "NSAppearanceNameAqua"
    appearance = NSAppearance.appearanceNamed_(name)
    w.window.setAppearance_(appearance)
    w.refresh()
    view = w.window.contentView()
    view.layoutSubtreeIfNeeded()
    b = view.bounds()
    rep = view.bitmapImageRepForCachingDisplayInRect_(b)
    ctx = NSGraphicsContext.graphicsContextWithBitmapImageRep_(rep)
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.setCurrentContext_(ctx)
    previous = NSAppearance.currentDrawingAppearance()
    NSAppearance.setCurrentAppearance_(appearance)
    NSColor.windowBackgroundColor().set()
    NSRectFill(b)
    NSAppearance.setCurrentAppearance_(previous)
    NSGraphicsContext.restoreGraphicsState()
    view.cacheDisplayInRect_toBitmapImageRep_(b, rep)
    import numpy as np
    w_px, h_px = rep.pixelsWide(), rep.pixelsHigh()
    data = np.frombuffer(rep.bitmapData(), dtype=np.uint8, count=rep.bytesPerRow() * h_px)
    pixels = data.reshape(h_px, rep.bytesPerRow())[:, : w_px * rep.samplesPerPixel()].reshape(h_px, w_px, -1)
    return pixels.copy(), rep


PAGES = {
    "welcome": (WELCOME, {}, {}),
    "permissions_none": (PERMISSIONS, {}, {}),
    "permissions_required_done": (PERMISSIONS, {"microphone": True, "accessibility": True}, {}),
    "models_downloading": (MODELS, {}, {"progress": 0.42}),
    "models_error": (MODELS, {}, {"progress": 0.3, "error": "network unreachable"}),
    "models_ready": (MODELS, {}, {"ready": True}),
    "ready": (READY, {}, {}),
}


@pytest.mark.parametrize("name", PAGES)
def test_page_matches_golden_image(name, window, golden_image):
    w, flow, perms, models, _ = window
    step, grants, model = PAGES[name]
    perms.granted.update(grants)
    for k, v in model.items():
        setattr(models, k, v)
    go(w, step)
    pixels, rep = snapshot(w)
    golden_image(f"setup_{name}", pixels, rep)


def test_dark_mode_matches_golden_image(window, golden_image):
    w, _, perms, _, _ = window
    perms.granted.update(microphone=True)
    go(w, PERMISSIONS)
    pixels, rep = snapshot(w, dark=True)
    golden_image("setup_permissions_dark", pixels, rep)


def test_setup_offers_finder_control_as_optional():
    from mispr import onboarding
    finder = next(p for p in onboarding.default_permissions() if p.key == "finder")
    assert not finder.required and finder.pane == "Privacy_Automation" and finder.title == "Control Finder"
    assert finder.check() in (True, False)
