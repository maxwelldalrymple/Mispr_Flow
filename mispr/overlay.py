"""The numbers overlay: "show numbers" (or a "click" that matches several things) puts a small
numbered badge on each target; say the number to click it. A see-through window above
everything that clicks pass through, gone after OVERLAY_SECONDS or once a number is picked."""

import objc
from AppKit import (
    NSBackingStoreBuffered,
    NSBezierPath,
    NSColor,
    NSFont,
    NSFontAttributeName,
    NSForegroundColorAttributeName,
    NSMakeRect,
    NSScreen,
    NSScreenSaverWindowLevel,
    NSString,
    NSView,
    NSWindow,
    NSWindowCollectionBehaviorCanJoinAllSpaces,
    NSWindowCollectionBehaviorStationary,
    NSWindowStyleMaskBorderless,
)

OVERLAY_SECONDS = 12
BADGE_FONT = 12
ACCENT = (0.12, 0.47, 0.95)  # a clear blue that reads on light and dark pages


def badge_rects(frames, screen_height, font_size=BADGE_FONT):
    """Where each badge goes, in window coordinates (bottom-left origin): the target's top-left
    corner, nudged inside it. `frames` are screen points from the top-left (Accessibility)."""
    out = []
    for i, (x, y, w, h) in enumerate(frames, 1):
        width = 10 + 7.5 * len(str(i))
        height = font_size + 7
        out.append((x + 1, screen_height - y - height - 1, width, height))
    return out


class _BadgeView(NSView):
    def initWithFrame_(self, frame):
        self = objc.super(_BadgeView, self).initWithFrame_(frame)
        if self is not None:
            self.badges = []
        return self

    def isFlipped(self):
        return False

    def drawRect_(self, rect):
        font = NSFont.boldSystemFontOfSize_(BADGE_FONT)
        attrs = {NSFontAttributeName: font, NSForegroundColorAttributeName: NSColor.whiteColor()}
        for i, (x, y, w, h) in enumerate(self.badges, 1):
            NSColor.colorWithCalibratedWhite_alpha_(0, 0.25).set()
            NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(NSMakeRect(x + 0.5, y - 1, w, h), h / 2, h / 2).fill()
            NSColor.colorWithCalibratedRed_green_blue_alpha_(*ACCENT, 0.95).set()
            NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(NSMakeRect(x, y, w, h), h / 2, h / 2).fill()
            NSColor.whiteColor().set()
            outline = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(NSMakeRect(x, y, w, h), h / 2, h / 2)
            outline.setLineWidth_(1.0)
            outline.stroke()
            label = NSString.stringWithString_(str(i))
            size = label.sizeWithAttributes_(attrs)
            label.drawAtPoint_withAttributes_((x + (w - size.width) / 2, y + (h - size.height) / 2), attrs)


class NumberOverlay:
    """Shows numbered badges over the main screen; `targets` keeps what each number means."""

    def __init__(self):
        self.window = None
        self.view = None
        self.targets = []

    @property
    def showing(self):
        return bool(self.targets)

    def _make(self):
        screen = NSScreen.screens()[0].frame()
        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            screen, NSWindowStyleMaskBorderless, NSBackingStoreBuffered, False)
        self.window.setOpaque_(False)
        self.window.setBackgroundColor_(NSColor.clearColor())
        self.window.setIgnoresMouseEvents_(True)  # clicks go through to the page
        self.window.setLevel_(NSScreenSaverWindowLevel)
        self.window.setHasShadow_(False)
        self.window.setCollectionBehavior_(NSWindowCollectionBehaviorCanJoinAllSpaces | NSWindowCollectionBehaviorStationary)
        self.view = _BadgeView.alloc().initWithFrame_(((0, 0), screen.size))
        self.window.setContentView_(self.view)

    def show(self, targets):
        if self.window is None:
            self._make()
        self.targets = list(targets)
        height = NSScreen.screens()[0].frame().size.height
        self.view.badges = badge_rects([t.frame for t in self.targets], height)
        self.view.setNeedsDisplay_(True)
        self.window.orderFrontRegardless()

    def hide(self):
        self.targets = []
        if self.window is not None:
            self.window.orderOut_(None)

    def pick(self, number):
        """The target numbered `number` (1-based), or None."""
        return self.targets[number - 1] if 1 <= number <= len(self.targets) else None
