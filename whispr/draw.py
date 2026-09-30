"""Low-level drawing helpers for the widget (AppKit, unflipped coordinates)."""

import math
from dataclasses import dataclass

from AppKit import (
    NSAttributedString,
    NSCompositingOperationSourceOver,
    NSFontWeightMedium,
    NSImage,
    NSImageSymbolConfiguration,
    NSZeroRect,
    NSBezierPath,
    NSColor,
    NSFont,
    NSFontAttributeName,
    NSFontWeightRegular,
    NSFontWeightSemibold,
    NSForegroundColorAttributeName,
    NSMakePoint,
    NSMakeRect,
    NSMutableAttributedString,
    NSRoundLineCapStyle,
    NSRoundLineJoinStyle,
)


@dataclass(frozen=True)
class Rect:
    x: float
    y: float
    w: float
    h: float

    @classmethod
    def centered(cls, cx, cy, w, h):
        return cls(cx - w / 2, cy - h / 2, w, h)

    @property
    def cx(self):
        return self.x + self.w / 2

    @property
    def cy(self):
        return self.y + self.h / 2

    @property
    def top(self):
        return self.y + self.h

    @property
    def right(self):
        return self.x + self.w

    def contains(self, px, py):
        return self.x <= px <= self.right and self.y <= py <= self.top

    def inset(self, d):
        return Rect(self.x + d, self.y + d, self.w - 2 * d, self.h - 2 * d)

    def union(self, o):
        x, y = min(self.x, o.x), min(self.y, o.y)
        return Rect(x, y, max(self.right, o.right) - x, max(self.top, o.top) - y)

    def ns(self):
        return NSMakeRect(self.x, self.y, self.w, self.h)


def white(level, alpha):
    return NSColor.colorWithWhite_alpha_(level, max(0.0, min(1.0, alpha)))


def srgb(r, g, b, alpha):
    return NSColor.colorWithSRGBRed_green_blue_alpha_(r, g, b, max(0.0, min(1.0, alpha)))


def fill_round(rect, radius, color):
    color.set()
    NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(rect.ns(), radius, radius).fill()


def stroke_round(rect, radius, color, width=1.0):
    color.set()
    # Inset by half the line width so the stroke stays inside the shape.
    r = rect.inset(width / 2)
    path = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(r.ns(), radius, radius)
    path.setLineWidth_(width)
    path.stroke()


def fill_circle(cx, cy, r, color):
    color.set()
    NSBezierPath.bezierPathWithOvalInRect_(NSMakeRect(cx - r, cy - r, 2 * r, 2 * r)).fill()


def stroke_circle(cx, cy, r, color, width=1.0):
    color.set()
    path = NSBezierPath.bezierPathWithOvalInRect_(NSMakeRect(cx - r, cy - r, 2 * r, 2 * r))
    path.setLineWidth_(width)
    path.stroke()


def _stroke_lines(points_list, color, width):
    color.set()
    path = NSBezierPath.bezierPath()
    path.setLineWidth_(width)
    path.setLineCapStyle_(NSRoundLineCapStyle)
    path.setLineJoinStyle_(NSRoundLineJoinStyle)
    for points in points_list:
        path.moveToPoint_(NSMakePoint(*points[0]))
        for p in points[1:]:
            path.lineToPoint_(NSMakePoint(*p))
    path.stroke()


# --- Icons -----------------------------------------------------------------

_symbol_cache = {}


def symbol(name, cx, cy, size, rgb=(1.0, 1.0, 1.0), alpha=1.0, weight=NSFontWeightMedium):
    """Draw an SF Symbol centred at (cx, cy); `size` is the symbol point size."""
    key = (name, size, rgb, weight)
    img = _symbol_cache.get(key)
    if img is None:
        base = NSImage.imageWithSystemSymbolName_accessibilityDescription_(name, None)
        if base is None:
            return
        config = NSImageSymbolConfiguration.configurationWithPointSize_weight_(size, weight)
        config = config.configurationByApplyingConfiguration_(
            NSImageSymbolConfiguration.configurationWithPaletteColors_([srgb(*rgb, 1.0)])
        )
        img = base.imageWithSymbolConfiguration_(config)
        _symbol_cache[key] = img
    sz = img.size()
    rect = NSMakeRect(cx - sz.width / 2, cy - sz.height / 2, sz.width, sz.height)
    img.drawInRect_fromRect_operation_fraction_respectFlipped_hints_(
        rect, NSZeroRect, NSCompositingOperationSourceOver, max(0.0, min(1.0, alpha)), True, None
    )


def spinner(cx, cy, r, phase, alpha):
    spokes = 8
    step = int(phase * spokes) % spokes
    for i in range(spokes):
        a = 2 * math.pi * i / spokes
        fade = ((i - step) % spokes) / spokes
        c = white(1.0, alpha * (0.2 + 0.8 * fade))
        p1 = (cx + math.cos(a) * r * 0.45, cy + math.sin(a) * r * 0.45)
        p2 = (cx + math.cos(a) * r, cy + math.sin(a) * r)
        _stroke_lines([[p1, p2]], c, 1.5)


def bars(cx, cy, levels, pitch, width, max_h, color):
    """Centered waveform: each level in 0..1 becomes a rounded vertical bar; silence is a dot."""
    n = len(levels)
    x0 = cx - (n - 1) * pitch / 2
    for i, lvl in enumerate(levels):
        h = max(width, lvl * max_h)
        fill_round(Rect.centered(x0 + i * pitch, cy, width, h), width / 2, color)


# --- Text ------------------------------------------------------------------

def rich(parts, size, color, bold_weight=NSFontWeightSemibold, weight=NSFontWeightRegular):
    """Build an attributed string from [(text, is_bold), ...]."""
    s = NSMutableAttributedString.alloc().init()
    for text, bold in parts:
        font = NSFont.systemFontOfSize_weight_(size, bold_weight if bold else weight)
        s.appendAttributedString_(
            NSAttributedString.alloc().initWithString_attributes_(
                text, {NSFontAttributeName: font, NSForegroundColorAttributeName: color}
            )
        )
    return s


def draw_text_centered(attr, cx, cy):
    sz = attr.size()
    attr.drawAtPoint_(NSMakePoint(cx - sz.width / 2, cy - sz.height / 2))


def draw_text_left(attr, x, cy):
    sz = attr.size()
    attr.drawAtPoint_(NSMakePoint(x, cy - sz.height / 2))
