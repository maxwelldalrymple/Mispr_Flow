"""App entry point: menu bar item + floating widget, no Dock icon."""

import fcntl
import signal
import sys
import tempfile
from pathlib import Path

from AppKit import (
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSImage,
    NSMenu,
    NSStatusBar,
    NSVariableStatusItemLength,
)
from PyObjCTools import AppHelper

from . import hotkey
from .widget import WidgetController


def _status_item():
    item = NSStatusBar.systemStatusBar().statusItemWithLength_(NSVariableStatusItemLength)
    icon = NSImage.imageWithSystemSymbolName_accessibilityDescription_("waveform", "Whispr Clone")
    icon.setTemplate_(True)
    item.button().setImage_(icon)
    menu = NSMenu.alloc().init()
    menu.addItemWithTitle_action_keyEquivalent_("Quit Whispr Clone", "terminate:", "q")
    item.setMenu_(menu)
    return item


_keepalive = []  # strong references for the lifetime of the app


def _single_instance_lock():
    """Exit if another copy is already running (two copies = two widgets, two fn handlers)."""
    lock = open(Path(tempfile.gettempdir()) / "whispr-clone.lock", "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("whispr: already running", file=sys.stderr)
        sys.exit(1)
    return lock  # the lock is held until the process exits


def _install_shutdown(status_item, widget):
    """On kill/Ctrl-C, remove the menu bar icon (macOS otherwise leaves a ghost) and wipe audio."""

    def shutdown(signum, frame):
        NSStatusBar.systemStatusBar().removeStatusItem_(status_item)
        widget.recorder.stop()
        widget.recorder.buffer.close()
        AppHelper.stopEventLoop()

    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(sig, shutdown)


def main():
    lock = _single_instance_lock()
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    widget = WidgetController()
    fn = hotkey.FnMonitor(widget.fn_down, widget.fn_up, widget.fn_combo)
    status_item = _status_item()
    _keepalive.extend([lock, status_item, widget, fn])
    _install_shutdown(status_item, widget)
    widget.start()

    if not hotkey.has_permission():
        hotkey.request_permission()
    if not fn.start():
        print(
            "whispr: fn dictation is off. Allow this app in System Settings > Privacy & Security >"
            " Input Monitoring, then restart. Clicking the widget still works.",
            file=sys.stderr,
        )
    if not hotkey.fn_key_does_nothing():
        print(
            'whispr: set System Settings > Keyboard > "Press 🌐 key to" > Do Nothing,'
            " otherwise macOS also opens its own fn action (emoji picker / dictation).",
            file=sys.stderr,
        )
    AppHelper.runEventLoop(installInterrupt=False)  # our own signal handlers clean up
