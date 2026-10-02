#!/bin/bash
# Screenshot every window and state into docs/screenshots/ (made-up sample data, nothing of yours):
#   tools/screenshots.sh
# The SwiftUI app's windows come from macos/Tests/MisprFlowTests/ScreenshotTests.swift; the setup
# window and the floating widget are the Python golden images in tests/golden/.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/docs/screenshots"
rm -rf "$OUT"/*/  # the image folders; README.md stays
MISPR_SCREENSHOTS="$OUT" swift test --package-path "$ROOT/macos" --filter ScreenshotTests
# The Python renders, renamed the same way: <window>_<page>_<state>_<theme>-<light|dark>.png.
mkdir -p "$OUT/setup-window" "$OUT/floating-widget"
for f in "$ROOT"/tests/golden/setup_*.png; do
    name="$(basename "$f" .png)"; mode=light
    case "$name" in *_dark) mode=dark; name="${name%_dark}";; esac
    cp "$f" "$OUT/setup-window/setup-window_${name#setup_}_system-$mode.png"
done
for f in "$ROOT"/tests/golden/widget_*.png; do
    cp "$f" "$OUT/floating-widget/floating-widget_$(basename "${f#*widget_}")"
done
echo "$(find "$OUT" -name '*.png' | wc -l | tr -d ' ') screenshots in $OUT"
