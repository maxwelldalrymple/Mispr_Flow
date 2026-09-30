"""App entry point: menu bar item + floating widget, no Dock icon."""

import sys

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


def main():
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    widget = WidgetController()
    fn = hotkey.FnMonitor(widget.fn_down, widget.fn_up, widget.fn_combo)
    _keepalive.extend([_status_item(), widget, fn])
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
    AppHelper.runEventLoop()
