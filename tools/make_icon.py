"""Build mispr/assets/AppIcon.icns from mispr/assets/icon.png: python tools/make_icon.py

The logo is laid on Apple's macOS icon grid (an 824 px rounded square centered on a
1024 px canvas, with a soft drop shadow), so it sits at the same size as other Dock icons.
"""
import subprocess, sys, tempfile
from pathlib import Path
from AppKit import (NSImage, NSBitmapImageRep, NSPNGFileType, NSGraphicsContext, NSColor,
                    NSBezierPath, NSShadow, NSMakeRect, NSMakeSize, NSCompositingOperationSourceOver)

ASSETS = Path(__file__).resolve().parent.parent / "mispr" / "assets"
CANVAS, TILE, RADIUS = 1024, 824, 185  # Apple's macOS app-icon template
CROP = 0.86  # trim the logo's empty black margin so the ring fills the tile


def render(src, px):
    rep = NSBitmapImageRep.alloc().initWithBitmapDataPlanes_pixelsWide_pixelsHigh_bitsPerSample_samplesPerPixel_hasAlpha_isPlanar_colorSpaceName_bytesPerRow_bitsPerPixel_(
        None, px, px, 8, 4, True, False, "NSCalibratedRGBColorSpace", 0, 0)
    rep.setSize_(NSMakeSize(CANVAS, CANVAS))  # draw in 1024-pt units at any pixel size
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.setCurrentContext_(NSGraphicsContext.graphicsContextWithBitmapImageRep_(rep))
    NSGraphicsContext.currentContext().setImageInterpolation_(3)  # high
    inset = (CANVAS - TILE) / 2
    tile = NSMakeRect(inset, inset + 6, TILE, TILE)  # a touch high, leaving room for the shadow
    path = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(tile, RADIUS, RADIUS)

    NSGraphicsContext.saveGraphicsState()
    shadow = NSShadow.alloc().init()
    shadow.setShadowOffset_(NSMakeSize(0, -10))
    shadow.setShadowBlurRadius_(24)
    shadow.setShadowColor_(NSColor.colorWithWhite_alpha_(0, 0.35))
    shadow.set()
    NSColor.blackColor().setFill()
    path.fill()
    NSGraphicsContext.restoreGraphicsState()

    NSGraphicsContext.saveGraphicsState()
    path.addClip()
    w = src.size().width
    side = w * CROP
    src.drawInRect_fromRect_operation_fraction_(tile, NSMakeRect((w - side) / 2, (w - side) / 2, side, side),
                                                NSCompositingOperationSourceOver, 1.0)
    NSGraphicsContext.restoreGraphicsState()
    NSGraphicsContext.restoreGraphicsState()
    return rep.representationUsingType_properties_(NSPNGFileType, None)


def main():
    src = NSImage.alloc().initWithContentsOfFile_(str(ASSETS / "icon.png"))
    if src is None:
        sys.exit("can't read mispr/assets/icon.png")
    with tempfile.TemporaryDirectory() as tmp:
        iconset = Path(tmp) / "AppIcon.iconset"
        iconset.mkdir()
        for pt in (16, 32, 128, 256, 512):
            for scale in (1, 2):
                name = f"icon_{pt}x{pt}{'@2x' if scale == 2 else ''}.png"
                render(src, pt * scale).writeToFile_atomically_(str(iconset / name), True)
        subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(ASSETS / "AppIcon.icns")], check=True)
    print(f"wrote {ASSETS / 'AppIcon.icns'}")


if __name__ == "__main__":
    main()
