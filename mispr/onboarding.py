"""First-run setup: a 4-step native window (Welcome → Permissions → Models → Ready).

`SetupFlow` holds the logic (which step, what's missing, when to show) and has no AppKit
code, so it is fully unit-testable. `SetupWindow` is the humble view that draws it.

Permissions:
- Microphone (required): hear the user while dictating.
- Accessibility (required): capture fn, paste text, read the browser page.
- Screen & System Audio Recording (optional): the upcoming meeting notetaker, so users
  set everything up once.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import Quartz
from AppKit import (
    NSBackingStoreBuffered,
    NSButton,
    NSColor,
    NSFont,
    NSFontWeightBold,
    NSFontWeightRegular,
    NSFontWeightSemibold,
    NSImage,
    NSImageSymbolConfiguration,
    NSImageView,
    NSMakeRect,
    NSProgressIndicator,
    NSStackView,
    NSTextAlignmentCenter,
    NSTextField,
    NSURL,
    NSView,
    NSWindow,
    NSWindowCollectionBehaviorFullScreenAuxiliary,
    NSWindowCollectionBehaviorMoveToActiveSpace,
    NSWindowStyleMaskClosable,
    NSWindowStyleMaskTitled,
    NSWorkspace,
)
from Foundation import NSObject

from . import apps, hotkey, settings as settings_mod, sounds

WELCOME, PERMISSIONS, EXTRAS, MODELS, READY = range(5)
STEP_NAMES = ("Welcome", "Permissions", "Optional", "Models", "Ready")

_PANE = "x-apple.systempreferences:com.apple.preference.security?"
ASSETS = Path(__file__).resolve().parent / "assets"

# AVAuthorizationStatus values
_AV_NOT_DETERMINED, _AV_RESTRICTED, _AV_DENIED, _AV_AUTHORIZED = 0, 1, 2, 3


# --- Permission checks and requests (thin OS wrappers) -----------------------------------------

def _av():
    import AVFoundation
    return AVFoundation


def microphone_granted():
    av = _av()
    return av.AVCaptureDevice.authorizationStatusForMediaType_(av.AVMediaTypeAudio) == _AV_AUTHORIZED


def microphone_undecided():
    av = _av()
    return av.AVCaptureDevice.authorizationStatusForMediaType_(av.AVMediaTypeAudio) == _AV_NOT_DETERMINED


def request_microphone():
    av = _av()
    av.AVCaptureDevice.requestAccessForMediaType_completionHandler_(av.AVMediaTypeAudio, lambda granted: None)


def screen_audio_granted():
    return bool(Quartz.CGPreflightScreenCaptureAccess())


def request_screen_audio():
    return bool(Quartz.CGRequestScreenCaptureAccess())


def open_pane(anchor):
    NSWorkspace.sharedWorkspace().openURL_(NSURL.URLWithString_(_PANE + anchor))


@dataclass(frozen=True)
class Permission:
    key: str
    title: str
    detail: str
    symbol: str  # SF Symbol name
    required: bool
    check: Callable[[], bool]
    request: Callable[[], object]  # shows the system prompt (first time only)
    pane: str  # System Settings > Privacy & Security anchor
    prompt_available: Callable[[], bool] = lambda: True  # False once the one-time prompt was used


def default_permissions():
    return [
        Permission(
            "microphone", "Microphone",
            "Hears you while you hold fn. The mic is only on while you're dictating.",
            "mic.fill", True, microphone_granted, request_microphone, "Privacy_Microphone",
            prompt_available=microphone_undecided,
        ),
        Permission(
            "accessibility", "Accessibility",
            "Lets Mispr Flow use the fn key and paste text into the app you're typing in.",
            "accessibility", True, hotkey.has_accessibility, hotkey.request_accessibility,
            "Privacy_Accessibility",
        ),
        Permission(
            "screen_audio", "Screen & System Audio",
            "For meeting notes: hears the other people on a call. You may need to reopen Mispr Flow after allowing it.",
            "waveform.badge.mic", False, screen_audio_granted, request_screen_audio, "Privacy_ScreenCapture",
        ),
        Permission(
            "files", "Full Disk Access",
            "For “open folder …”: find folders anywhere. Switch on Mispr Flow in the list.",
            "internaldrive", False, apps.full_disk_access, lambda: open_pane("Privacy_AllFiles"),
            "Privacy_AllFiles", prompt_available=lambda: False,
        ),
        Permission(
            "finder", "Control Finder",
            "For “open …” in Finder: opens folders in the same window.",
            "folder", False, lambda: apps.finder_control() is True, lambda: apps.finder_control(ask=True),
            "Privacy_Automation",
            prompt_available=lambda: apps.finder_control() is None,
        ),
    ]


# --- Logic ----------------------------------------------------------------------------------

class SetupFlow:
    """Which step is showing and whether the user may continue. No AppKit."""

    def __init__(self, permissions, models_ready, model_progress=lambda: 0.0,
                 model_error=lambda: None, retry_models=lambda: None, settings=None):
        self.permissions = list(permissions)
        self.models_ready = models_ready
        self.model_progress = model_progress
        self.model_error = model_error
        self.retry_models = retry_models
        self.settings = settings if settings is not None else settings_mod.load()
        self.requested = set()  # permission keys whose Allow button was already clicked
        self.step = self.start_step()

    # What's missing
    def granted(self):
        return {p.key: bool(p.check()) for p in self.permissions}

    def missing_required(self):
        return [p.key for p in self.permissions if p.required and not p.check()]

    def needed(self):
        """Show the window on first run, or whenever a required piece is missing."""
        return not self.settings.onboarded or bool(self.missing_required()) or not self.models_ready()

    def start_step(self):
        if not self.settings.onboarded:
            return WELCOME
        if self.missing_required():
            return PERMISSIONS
        if not self.models_ready():
            return MODELS
        return WELCOME  # reopened from the menu with nothing missing

    # Navigation
    def can_advance(self):
        if self.step == PERMISSIONS:
            return not self.missing_required()
        if self.step == MODELS:
            return bool(self.models_ready())
        return True

    def advance(self):
        if self.step < READY and self.can_advance():
            self.step += 1
        return self.step

    def back(self):
        if self.step > WELCOME:
            self.step -= 1
        return self.step

    def finish(self):
        self.settings.onboarded = True
        settings_mod.save(self.settings)

    # Actions
    def allow(self, key):
        """First click shows the system prompt; later clicks (or if macOS won't prompt again)
        open the right System Settings pane."""
        perm = next(p for p in self.permissions if p.key == key)
        if perm.check():
            return "granted"
        if key not in self.requested and perm.prompt_available():
            self.requested.add(key)
            perm.request()
            return "prompted"
        open_pane(perm.pane)
        return "opened settings"

    def model_status(self):
        """('ready' | 'error' | 'downloading', fraction, message)."""
        if self.models_ready():
            return "ready", 1.0, "Models installed and verified."
        error = self.model_error()
        if error:
            return "error", self.model_progress(), f"Download failed: {error}"
        fraction = self.model_progress()
        total_gb = 3.1
        return "downloading", fraction, f"{int(fraction * 100)}% · {fraction * total_gb:.1f} of {total_gb} GB"


# --- View -----------------------------------------------------------------------------------

def _label(text, size=13, weight=NSFontWeightRegular, color=None, wrap=False, width=None):
    field = NSTextField.wrappingLabelWithString_(text) if wrap else NSTextField.labelWithString_(text)
    field.setFont_(NSFont.systemFontOfSize_weight_(size, weight))
    if color is not None:
        field.setTextColor_(color)
    if width is not None:
        field.setPreferredMaxLayoutWidth_(width)
        _pin(field, width=width)
    field.setSelectable_(False)
    return field


def _symbol(name, size, color=None):
    img = NSImage.imageWithSystemSymbolName_accessibilityDescription_(name, None)
    config = NSImageSymbolConfiguration.configurationWithPointSize_weight_(size, NSFontWeightRegular)
    view = NSImageView.imageViewWithImage_(img.imageWithSymbolConfiguration_(config) if img else NSImage.alloc().init())
    if color is not None:
        view.setContentTintColor_(color)
    return view


def _stack(views, vertical=True, spacing=8, align=None):
    s = NSStackView.stackViewWithViews_(views)
    s.setOrientation_(1 if vertical else 0)
    s.setSpacing_(spacing)
    if align is not None:
        s.setAlignment_(align)
    return s


def _pin(view, width=None, height=None):
    view.setTranslatesAutoresizingMaskIntoConstraints_(False)
    if width is not None:
        view.widthAnchor().constraintEqualToConstant_(width).setActive_(True)
    if height is not None:
        view.heightAnchor().constraintEqualToConstant_(height).setActive_(True)


ALIGN_LEADING, ALIGN_CENTER_X, ALIGN_CENTER_Y = 5, 9, 12


class _Actions(NSObject):
    """Button target: forwards clicks to the Python window controller."""

    def continue_(self, sender):
        self.owner.on_continue()

    def back_(self, sender):
        self.owner.on_back()

    def allow_(self, sender):
        self.owner.on_allow(sender.identifier())

    def retry_(self, sender):
        self.owner.on_retry()

    def refresh_(self, timer):
        self.owner.refresh()


class SetupWindow:
    WIDTH, HEIGHT = 560, 520
    CONTENT_W = 480

    def __init__(self, flow, on_finish=lambda: None, play=lambda name: None):
        self.flow = flow
        self.on_finish = on_finish
        self.play = play  # sound cue player (sounds.Sounds.play)
        self.was_granted = flow.granted()
        self.actions = _Actions.alloc().init()
        self.actions.owner = self
        self.timer = None
        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, self.WIDTH, self.HEIGHT),
            NSWindowStyleMaskTitled | NSWindowStyleMaskClosable, NSBackingStoreBuffered, False,
        )
        self.window.setTitle_("Mispr Flow Setup")
        # Open on the Space the user is looking at (and over fullscreen apps), not wherever
        # this menu-bar app happens to live.
        self.window.setCollectionBehavior_(
            NSWindowCollectionBehaviorMoveToActiveSpace | NSWindowCollectionBehaviorFullScreenAuxiliary)
        self.window.setReleasedWhenClosed_(False)
        self.window.center()
        self.rows = {}  # permission key -> (status label, allow button)
        self.render()

    # Lifecycle
    def show(self):
        from AppKit import NSApp, NSRunLoop, NSRunLoopCommonModes, NSTimer
        self.window.makeKeyAndOrderFront_(None)
        NSApp().activateIgnoringOtherApps_(True)  # menu-bar apps must bring their window forward
        if self.timer is None:
            self.timer = NSTimer.timerWithTimeInterval_target_selector_userInfo_repeats_(
                0.5, self.actions, "refresh:", None, True)
            NSRunLoop.currentRunLoop().addTimer_forMode_(self.timer, NSRunLoopCommonModes)

    def close(self):
        if self.timer is not None:
            self.timer.invalidate()
            self.timer = None
        self.window.orderOut_(None)

    # Events
    def on_continue(self):
        if self.flow.step == READY:
            self.play(sounds.ACHIEVEMENT)
            self.flow.finish()
            self.close()
            self.on_finish()
            return
        self.flow.advance()
        self.render()

    def on_back(self):
        self.flow.back()
        self.render()

    def on_allow(self, key):
        self.flow.allow(key)
        self.refresh()

    def on_retry(self):
        self.flow.retry_models()
        self.refresh()

    # Drawing
    def render(self):
        self.rows = {}
        self.model_widgets = None
        builders = (self._welcome, self._permissions, self._extras, self._models, self._ready)
        page = builders[self.flow.step]()
        content = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, self.WIDTH, self.HEIGHT))
        footer = self._footer()
        for v in (page, footer):
            _pin(v)
            content.addSubview_(v)
        page.topAnchor().constraintEqualToAnchor_constant_(content.topAnchor(), 36).setActive_(True)
        page.centerXAnchor().constraintEqualToAnchor_(content.centerXAnchor()).setActive_(True)
        footer.bottomAnchor().constraintEqualToAnchor_constant_(content.bottomAnchor(), -24).setActive_(True)
        footer.leadingAnchor().constraintEqualToAnchor_constant_(content.leadingAnchor(), 40).setActive_(True)
        footer.trailingAnchor().constraintEqualToAnchor_constant_(content.trailingAnchor(), -40).setActive_(True)
        self.window.setContentView_(content)
        self.refresh()

    def _header(self, symbol_or_logo, title, subtitle):
        if symbol_or_logo == "logo":
            top = NSImageView.imageViewWithImage_(NSImage.alloc().initWithContentsOfFile_(str(ASSETS / "icon.png")))
            _pin(top, width=96, height=96)
            top.setWantsLayer_(True)  # rounded like a macOS app icon
            top.layer().setCornerRadius_(22)
            top.layer().setMasksToBounds_(True)
        else:
            top = _symbol(symbol_or_logo, 44, NSColor.controlAccentColor())
        t = _label(title, 24, NSFontWeightBold)
        s = _label(subtitle, 13, color=NSColor.secondaryLabelColor(), wrap=True, width=self.CONTENT_W)
        s.setAlignment_(NSTextAlignmentCenter)
        return [top, t, s]

    def _feature(self, symbol, title, detail):
        icon = _symbol(symbol, 20, NSColor.controlAccentColor())
        _pin(icon, width=28)
        text = _stack([_label(title, 13, NSFontWeightSemibold),
                       _label(detail, 12, color=NSColor.secondaryLabelColor(), wrap=True, width=self.CONTENT_W - 60)],
                      spacing=2, align=ALIGN_LEADING)
        return _stack([icon, text], vertical=False, spacing=12, align=ALIGN_CENTER_Y)

    def _welcome(self):
        views = self._header("logo", "Welcome to Mispr Flow",
                             "Private dictation for your Mac. Hold fn, speak, and your words appear wherever you're typing.")
        features = _stack([
            self._feature("lock.shield", "100% on your Mac", "Your voice is never sent to a server."),
            self._feature("keyboard", "Works in any app", "Hold fn to talk, release to paste."),
            self._feature("heart", "Free and open source", "MIT licensed. Setup takes about two minutes."),
        ], spacing=14, align=ALIGN_LEADING)
        return _stack(views + [features], spacing=12, align=ALIGN_CENTER_X)

    def _permissions(self):
        return self._permission_page(
            True, "checkmark.shield", "Allow access",
            "Mispr Flow needs these to hear you and type for you. Nothing ever leaves your Mac.")

    def _extras(self):
        return self._permission_page(
            False, "sparkles", "Optional features",
            "Turn on what you'll use. You can skip these and allow them later from Setup Guide…")

    def _permission_page(self, required, symbol, title_text, subtitle):
        views = self._header(symbol, title_text, subtitle)
        rows = []
        for p in self.flow.permissions:
            if p.required != required:
                continue
            icon = _symbol(p.symbol, 20, NSColor.controlAccentColor())
            _pin(icon, width=28)
            title = _label(p.title, 13, NSFontWeightSemibold)
            head = _stack([title] + ([_label("Optional", 11, color=NSColor.tertiaryLabelColor())] if not p.required else []),
                          vertical=False, spacing=6, align=ALIGN_CENTER_Y)
            text = _stack([head, _label(p.detail, 12, color=NSColor.secondaryLabelColor(), wrap=True, width=300)],
                          spacing=2, align=ALIGN_LEADING)
            status = _label("✓ Allowed", 13, NSFontWeightSemibold, NSColor.systemGreenColor())
            button = NSButton.buttonWithTitle_target_action_("Allow…", self.actions, "allow:")
            button.setIdentifier_(p.key)
            right = _stack([status, button], vertical=False, spacing=0, align=ALIGN_CENTER_Y)
            _pin(right, width=96)
            row = _stack([icon, text, right], vertical=False, spacing=12, align=ALIGN_CENTER_Y)
            _pin(row, width=self.CONTENT_W)
            self.rows[p.key] = (status, button)
            rows.append(row)
        return _stack(views + [_stack(rows, spacing=16, align=ALIGN_LEADING)], spacing=12, align=ALIGN_CENTER_X)

    def _models(self):
        views = self._header("arrow.down.circle", "Download speech models",
                             "Two models run on your Mac: Whisper for speech (0.57 GB) and Gemma for cleanup "
                             "(2.5 GB). They're downloaded once and checked for integrity.")
        bar = NSProgressIndicator.alloc().init()
        bar.setIndeterminate_(False)
        bar.setMinValue_(0.0)
        bar.setMaxValue_(1.0)
        _pin(bar, width=self.CONTENT_W)
        status = _label("", 13, color=NSColor.secondaryLabelColor())
        retry = NSButton.buttonWithTitle_target_action_("Retry", self.actions, "retry:")
        self.model_widgets = (bar, status, retry)
        return _stack(views + [bar, _stack([status, retry], vertical=False, spacing=10, align=ALIGN_CENTER_Y)],
                      spacing=12, align=ALIGN_CENTER_X)

    def _ready(self):
        views = self._header("checkmark.circle.fill", "You're all set",
                             "Mispr Flow lives in your menu bar. Here's how to use it:")
        tips = _stack([
            self._feature("hand.point.up.left", "Hold fn", "Talk, then let go. Your words are pasted where you're typing."),
            self._feature("hand.tap", "Double-tap fn", "Hands-free: press space or return to paste, delete to cancel."),
            self._feature("capsule", "The pill above the Dock", "Hover it for the mic and meeting-note buttons."),
        ], spacing=14, align=ALIGN_LEADING)
        return _stack(views + [tips], spacing=12, align=ALIGN_CENTER_X)

    def _footer(self):
        step = _label(f"Step {self.flow.step + 1} of {len(STEP_NAMES)} · {STEP_NAMES[self.flow.step]}", 12,
                      color=NSColor.tertiaryLabelColor())
        spacer = NSView.alloc().init()
        buttons = [step, spacer]
        self.back_button = None
        if self.flow.step not in (WELCOME, READY):
            self.back_button = NSButton.buttonWithTitle_target_action_("Back", self.actions, "back:")
            buttons.append(self.back_button)
        title = {WELCOME: "Get Started", READY: "Start Dictating"}.get(self.flow.step, "Continue")
        self.continue_button = NSButton.buttonWithTitle_target_action_(title, self.actions, "continue:")
        self.continue_button.setKeyEquivalent_("\r")  # default (blue) button, activated by Return
        buttons.append(self.continue_button)
        footer = _stack(buttons, vertical=False, spacing=8, align=ALIGN_CENTER_Y)
        spacer.setContentHuggingPriority_forOrientation_(1, 0)
        return footer

    def refresh(self):
        """Poll permissions and model progress; update checkmarks, progress, and Continue."""
        granted = self.flow.granted()
        if any(granted[k] and not self.was_granted.get(k) for k in granted):
            self.play(sounds.SUCCESS)  # a checkmark just turned on
        self.was_granted = granted
        for key, (status, button) in self.rows.items():
            status.setHidden_(not granted[key])
            button.setHidden_(granted[key])
        if self.model_widgets is not None:
            bar, status, retry = self.model_widgets
            state, fraction, message = self.flow.model_status()
            bar.setDoubleValue_(fraction)
            status.setStringValue_(("✓ " if state == "ready" else "") + message)
            status.setTextColor_(NSColor.systemRedColor() if state == "error"
                                 else NSColor.systemGreenColor() if state == "ready"
                                 else NSColor.secondaryLabelColor())
            retry.setHidden_(state != "error")
        self.continue_button.setEnabled_(self.flow.can_advance())
