"""Render every widget state to PNGs for visual review: python tools/render_states.py OUT_DIR"""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from AppKit import NSImage, NSBitmapImageRep, NSPNGFileType, NSColor, NSMakeRect, NSRectFill, NSGraphicsContext
from whispr import widget as W
from whispr.draw import Rect

states = [
    (W.IDLE, None), (W.HOVER, "mic"), (W.HOVER, "note"), (W.HOLD, None),
    (W.HANDSFREE, "cancel"), (W.HANDSFREE, "finish"), (W.HANDSFREE, "wave"),
    (W.PROCESSING, None), (W.CANCELLED, None), (W.MEETING, None), (W.MISTAKE, "keep"),
    (W.SETUP, None), (W.SETUP, "retry"),
]
out = sys.argv[1]
SC = 2
for i, (st, hov) in enumerate(states):
    c = W.WidgetController()
    c.state = st
    c.state_since = time.monotonic() - 1.0
    c.shape = W.layout(st).bg.values()
    c.content_a = 1.0
    c.hovered = hov
    c.setup_progress = 0.42
    c.setup_error = "network unreachable" if (st == W.SETUP and hov == "retry") else None
    tip = W.TOOLTIPS.get((st, hov))
    if tip:
        c.tip = (tip, W.layout(st).elems[hov]); c.tip_a = 1.0
    for arr in c.bar_levels.values():
        mid = (len(arr)-1)/2
        for j in range(len(arr)):
            arr[j] = 0.9 * (1 - abs(j-mid)/(mid+1)) if st in W.RECORDING_STATES else 0
    rep = NSBitmapImageRep.alloc().initWithBitmapDataPlanes_pixelsWide_pixelsHigh_bitsPerSample_samplesPerPixel_hasAlpha_isPlanar_colorSpaceName_bytesPerRow_bitsPerPixel_(
        None, W.VIEW_W*SC, W.VIEW_H*SC, 8, 4, True, False, "NSCalibratedRGBColorSpace", 0, 0)
    rep.setSize_((W.VIEW_W, W.VIEW_H))
    ctx = NSGraphicsContext.graphicsContextWithBitmapImageRep_(rep)
    NSGraphicsContext.saveGraphicsState(); NSGraphicsContext.setCurrentContext_(ctx)
    NSColor.colorWithSRGBRed_green_blue_alpha_(0.23, 0.2, 0.12, 1).set()  # olive like the video
    NSRectFill(NSMakeRect(0, 0, W.VIEW_W, W.VIEW_H))
    c.draw()
    ctx.flushGraphics(); NSGraphicsContext.restoreGraphicsState()
    rep.representationUsingType_properties_(NSPNGFileType, {}).writeToFile_atomically_(f"{out}/state_{i:02d}_{st}_{hov}.png", True)
print("done")
