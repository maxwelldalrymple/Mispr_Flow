"""Low-level drawing helpers for the widget (AppKit, unflipped coordinates)."""

import math
from dataclasses import dataclass

from AppKit import (
    NSAttributedString,
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

def icon_mic(cx, cy, color):
    fill_round(Rect.centered(cx, cy + 2.5, 6, 10), 3, color)
    color.set()
    arc = NSBezierPath.bezierPath()
    arc.setLineWidth_(1.4)
    arc.setLineCapStyle_(NSRoundLineCapStyle)
    arc.appendBezierPathWithArcWithCenter_radius_startAngle_endAngle_clockwise_(
        NSMakePoint(cx, cy + 2.5), 5.5, 180, 360, False
    )
    arc.moveToPoint_(NSMakePoint(cx, cy - 3))
    arc.lineToPoint_(NSMakePoint(cx, cy - 6))
    arc.stroke()


def icon_record(cx, cy, color):
    stroke_circle(cx, cy, 6.5, color, 1.4)
    fill_circle(cx, cy, 3, color)


def icon_x(cx, cy, s, color, width=1.5):
    _stroke_lines([[(cx - s, cy - s), (cx + s, cy + s)], [(cx - s, cy + s), (cx + s, cy - s)]], color, width)


def icon_check(cx, cy, color):
    _stroke_lines([[(cx - 4, cy), (cx - 1.2, cy - 2.8), (cx + 4, cy + 3)]], color, 1.8)


def icon_stop(cx, cy, color):
    fill_round(Rect.centered(cx, cy, 6, 6), 1.5, color)


def icon_warning(cx, cy, color):
    _stroke_lines([[(cx, cy + 7), (cx - 8, cy - 6), (cx + 8, cy - 6), (cx, cy + 7)]], color, 1.6)
    _stroke_lines([[(cx, cy + 2), (cx, cy - 1.5)]], color, 1.6)
    fill_circle(cx, cy - 3.8, 0.9, color)


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
