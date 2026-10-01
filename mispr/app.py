"""App entry point: Dock icon, menu bar item, and the floating widget."""

import fcntl
import signal
import sys
import tempfile
from pathlib import Path

from AppKit import (
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSApplicationActivationPolicyRegular,
    NSApplicationWillTerminateNotification,
    NSImage,
    NSBundle,
    NSMenu,
    NSMenuItem,
    NSNotificationCenter,
    NSStatusBar,
    NSTimer,
    NSVariableStatusItemLength,
)
from PyObjCTools import AppHelper

from Foundation import NSObject

from . import host, hotkey, onboarding, prompts, settings, setup, storage, threads
from .widget import Ticker, WidgetController

APP_NAME = "Mispr Flow"  # shown to the user
APP_ID = "Mispr_Flow"  # used in file names
ASSETS = Path(__file__).resolve().parent / "assets"


def _menubar_icon():
    """The logo as an 18 pt template image (macOS tints it for light/dark menu bars).
    Falls back to the SF Symbol waveform if the asset is missing."""
    icon = NSImage.alloc().initWithContentsOfFile_(str(ASSETS / "menubar.png"))
    if icon is None:
        icon = NSImage.imageWithSystemSymbolName_accessibilityDescription_("waveform", APP_NAME)
    else:
        retina = NSImage.alloc().initWithContentsOfFile_(str(ASSETS / "menubar@2x.png"))
        if retina is not None:
            for rep in retina.representations():
                icon.addRepresentation_(rep)
        icon.setSize_((18, 18))
    icon.setTemplate_(True)
    icon.setAccessibilityDescription_(APP_NAME)
    return icon


def _app_icon():
    return NSImage.alloc().initWithContentsOfFile_(str(ASSETS / "AppIcon.icns"))


def _brand_process():
    """Running from source, the process is Python's; name it Mispr Flow so the menu bar,
    About box, and ⌘-Tab say so. (A packaged .app gets this from its Info.plist.)"""
    info = NSBundle.mainBundle().infoDictionary()
    info["CFBundleName"] = APP_NAME
    info["CFBundleDisplayName"] = APP_NAME


def _main_menu(actions):
    """The menu bar's app menu (shown while Mispr Flow is the active app)."""
    menubar = NSMenu.alloc().init()
    app_item = NSMenuItem.alloc().init()
    menubar.addItem_(app_item)
    menu = NSMenu.alloc().initWithTitle_(APP_NAME)
    menu.addItemWithTitle_action_keyEquivalent_(f"About {APP_NAME}", "orderFrontStandardAboutPanel:", "")
    menu.addItem_(NSMenuItem.separatorItem())
    menu.addItemWithTitle_action_keyEquivalent_("Setup Guide…", "openSetup:", ",").setTarget_(actions)
    menu.addItem_(NSMenuItem.separatorItem())
    menu.addItemWithTitle_action_keyEquivalent_(f"Hide {APP_NAME}", "hide:", "h")
    menu.addItemWithTitle_action_keyEquivalent_(f"Quit {APP_NAME}", "terminate:", "q")
    app_item.setSubmenu_(menu)
    return menubar


def _status_item():
    item = NSStatusBar.systemStatusBar().statusItemWithLength_(NSVariableStatusItemLength)
    item.button().setImage_(_menubar_icon())
    menu = NSMenu.alloc().init()
    menu.addItemWithTitle_action_keyEquivalent_(f"Quit {APP_NAME}", "terminate:", "q")
    item.setMenu_(menu)
    return item


_keepalive = []  # strong references for the lifetime of the app


LOCK_PATH = Path(tempfile.gettempdir()) / f"{APP_ID}.lock"


def _single_instance_lock(path=LOCK_PATH):
    """Exit if another copy is already running (two copies = two widgets, two fn handlers)."""
    lock = open(path, "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock.close()
        print("mispr: already running", file=sys.stderr)
        sys.exit(1)
    return lock  # the lock is held until the process exits


def _install_shutdown(status_item, widget):
    """Clean up on Quit and on kill/Ctrl-C: wipe audio, free the models (llama.cpp crashes at
    exit otherwise), and remove the menu bar icon (macOS otherwise leaves a ghost)."""

    def release():
        widget.recorder.stop()
        widget.recorder.buffer.close()
        widget.cleaner.close()

    def on_signal(signum, frame):
        release()
        NSStatusBar.systemStatusBar().removeStatusItem_(status_item)
        AppHelper.stopEventLoop()

    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(sig, on_signal)
    # Quit from the menu goes through -terminate:, which exits without returning to Python.
    NSNotificationCenter.defaultCenter().addObserverForName_object_queue_usingBlock_(
        NSApplicationWillTerminateNotification, None, None, lambda note: release()
    )


class _MenuActions(NSObject):
    """Target for menu items (needs to be an Objective-C object)."""

    def openSetup_(self, sender):
        self.open_setup()


class _AppDelegate(NSObject):
    """Clicking the Dock icon opens our window (the setup guide until the main window exists)."""

    def applicationShouldHandleReopen_hasVisibleWindows_(self, app, has_visible):
        self.on_reopen()
        return True


def _connect_host(app, widget, open_setup, fn=None):
    """Wire the engine to the Swift app: announce where data lives, report each saved
    dictation, and follow its commands. Quitting the app (stdin closes) quits the engine."""
    quit_app = lambda: app.terminate_(None)
    widget.on_saved = lambda path: host.send("saved", path=str(path))
    widget.on_note_requested = lambda: host.send("open_note")
    widget.on_meeting_changed = lambda active: host.send("meeting", active=active)
    def reload_settings():
        widget.reload_settings()
        if fn is not None:
            fn.set_trigger(widget.settings.hotkey)  # a new dictation key applies right away

    host.listen({"open_setup": open_setup, "reload_settings": reload_settings, "quit": quit_app,
                 "start_meeting": widget.begin_meeting, "stop_meeting": widget.stop_meeting,
                 "try_prompt": lambda **draft: try_prompt(widget.cleaner, **draft)},
                on_eof=quit_app)
    host.send("hello", recordings_dir=str(storage.RECORDINGS_DIR), settings_path=str(settings.SETTINGS_PATH),
              prompts_path=str(prompts.PROMPTS_PATH), default_prompts=prompts.defaults_payload())


def try_prompt(cleaner, text="", system="", extra="", examples="", guard=True, start=threads.start_daemon):
    """The Prompts page's Try it box: clean `text` with a draft prompt (not saved) on a worker
    thread, and send back what the model wrote."""
    def run():
        draft = prompts.Prompts(system=system or prompts.Prompts().system, extra=extra,
                                examples=prompts.parse_examples(examples), guard=bool(guard))
        output, info = cleaner.clean(text, system=draft.full_system(), examples=draft.examples, guard=draft.guard)
        host.send("tried", output=output, applied=info["applied"], rejected=info["rejected"], ms=info["ms"])
    start(run, "try-prompt")


def maintain_hotkey(fn):
    """Called every second: install the fn tap as soon as a permission allows it, and swap
    a listen-only tap for the active one once Accessibility is granted (no restart needed).
    Returns what changed, for logging."""
    if fn._tap is None:
        return "started" if fn.start() else None
    if not fn.active and fn.upgrade():
        return "upgraded"
    return None


def add_setup_menu_item(status_item, open_setup):
    """Put "Setup Guide…" at the top of the menu-bar menu; returns the target to keep alive."""
    actions = _MenuActions.alloc().init()
    actions.open_setup = open_setup
    item = status_item.menu().insertItemWithTitle_action_keyEquivalent_atIndex_("Setup Guide…", "openSetup:", "", 0)
    item.setTarget_(actions)
    return actions


def _setup_flow(widget):
    return onboarding.SetupFlow(
        onboarding.default_permissions(),
        models_ready=lambda: not setup.missing(),
        model_progress=lambda: widget.setup_progress,
        model_error=lambda: widget.setup_error,
        retry_models=widget._retry_setup,
        settings=widget.settings,
    )


def main():
    lock = _single_instance_lock()
    hosted = host.hosted()  # run by the Swift app, which owns the Dock icon and main window
    if hosted:
        host.open_channel()  # before WidgetController starts loading the models
    _brand_process()
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory if hosted
                             else NSApplicationActivationPolicyRegular)  # a Dock icon, like Wispr Flow
    icon = _app_icon()
    if icon is not None:
        app.setApplicationIconImage_(icon)  # the Dock tile, alerts, and About
    widget = WidgetController()
    fn = hotkey.FnMonitor(widget.fn_down, widget.fn_up, widget.fn_combo, widget.handle_key,
                          trigger=widget.settings.hotkey)
    status_item = _status_item()
    _keepalive.extend([lock, status_item, widget, fn])
    _install_shutdown(status_item, widget)
    widget.start()

    # First-run setup window: shown on first launch or whenever something required is
    # missing; also reopenable from the menu. Permissions are requested from there (with an
    # explanation) instead of prompting on launch.
    setup_window = {}

    def open_setup():
        window = setup_window.get("w")
        if window is None or not window.window.isVisible():
            window = onboarding.SetupWindow(_setup_flow(widget), play=widget.sounds.play)
            setup_window["w"] = window
        window.show()

    _keepalive.append(add_setup_menu_item(status_item, open_setup))
    if hosted:
        _connect_host(app, widget, open_setup, fn)
    else:
        menu_actions = _MenuActions.alloc().init()
        menu_actions.open_setup = open_setup
        app.setMainMenu_(_main_menu(menu_actions))
        delegate = _AppDelegate.alloc().init()
        delegate.on_reopen = open_setup
        app.setDelegate_(delegate)
        _keepalive.extend([menu_actions, delegate])
    if _setup_flow(widget).needed():
        open_setup()

    # Keep fn working as permissions change.
    if maintain_hotkey(fn) is None and fn._tap is None:
        print("mispr: fn is off until Accessibility is allowed (see the setup window).", file=sys.stderr)

    def keep_fn_working():
        change = maintain_hotkey(fn)
        if change:
            print(f"mispr: fn tap {change} ({'active' if fn.active else 'listen-only'})", file=sys.stderr)

    ticker = Ticker.alloc().init()
    ticker.callback = keep_fn_working
    timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(1.0, ticker, "tick:", None, True)
    _keepalive.extend([ticker, timer])
    AppHelper.runEventLoop(installInterrupt=False)  # our own signal handlers clean up
