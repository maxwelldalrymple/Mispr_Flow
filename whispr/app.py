"""App entry point: menu bar item + floating widget, no Dock icon."""

from AppKit import (
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSImage,
    NSMenu,
    NSStatusBar,
    NSVariableStatusItemLength,
)
from PyObjCTools import AppHelper

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
    _keepalive.extend([_status_item(), widget])
    widget.start()
    AppHelper.runEventLoop()
