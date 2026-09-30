"""App entry point: menu bar item + floating widget, no Dock icon."""

import fcntl
import signal
import sys
import tempfile
from pathlib import Path

from AppKit import (
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSApplicationWillTerminateNotification,
    NSImage,
    NSMenu,
    NSNotificationCenter,
    NSStatusBar,
    NSTimer,
    NSVariableStatusItemLength,
)
from PyObjCTools import AppHelper

from . import hotkey
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


def main():
    lock = _single_instance_lock()
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    icon = _app_icon()
    if icon is not None:
        app.setApplicationIconImage_(icon)  # alerts and About; the .app bundle uses AppIcon.icns
    widget = WidgetController()
    fn = hotkey.FnMonitor(widget.fn_down, widget.fn_up, widget.fn_combo, widget.handle_key)
    status_item = _status_item()
    _keepalive.extend([lock, status_item, widget, fn])
    _install_shutdown(status_item, widget)
    widget.start()

    if not hotkey.has_accessibility():
        hotkey.request_accessibility()
    if not hotkey.has_input_monitoring():
        hotkey.request_input_monitoring()
    if not fn.start():
        print(
            "mispr: fn dictation is off. Allow this app in System Settings > Privacy & Security >"
            " Input Monitoring, then restart. Clicking the widget still works.",
            file=sys.stderr,
        )
    elif not fn.active:
        if not hotkey.fn_key_does_nothing():
            print(
                "mispr: fn works, but macOS will also open the emoji picker until this app is allowed"
                " in System Settings > Privacy & Security > Accessibility (no restart needed).",
                file=sys.stderr,
            )
        # Swap to swallowing fn as soon as Accessibility is granted.
        def try_upgrade():
            if fn.upgrade():
                print("mispr: Accessibility granted; fn no longer triggers the emoji picker", file=sys.stderr)
                upgrade_timer.invalidate()

        ticker = Ticker.alloc().init()
        ticker.callback = try_upgrade
        upgrade_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            2.0, ticker, "tick:", None, True
        )
        _keepalive.append(ticker)
    AppHelper.runEventLoop(installInterrupt=False)  # our own signal handlers clean up
