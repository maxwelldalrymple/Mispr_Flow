#!/bin/bash
# Build build/Mispr Flow.app from macos/ (SwiftUI) for this machine: tools/build_app.sh [--open]
#
# The app runs the Python engine from this checkout's .venv, so it's a development build
# (the DMG will bundle Python instead). Ad-hoc signed: macOS may ask for Microphone and
# Accessibility again after each rebuild.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="$ROOT/build/Mispr Flow.app"
PYTHON="$ROOT/.venv/bin/python"
VERSION="0.3.0"
BUNDLE_ID="io.github.maxwelldalrymple.MisprFlow"

[ -x "$PYTHON" ] || { echo "missing $PYTHON: set up the venv first (see README)" >&2; exit 1; }

echo "Compiling…"
swift build --package-path "$ROOT/macos" -c release
BIN="$(swift build --package-path "$ROOT/macos" -c release --show-bin-path)/MisprFlow"

rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp "$BIN" "$APP/Contents/MacOS/MisprFlow"
cp "$ROOT/mispr/assets/AppIcon.icns" "$APP/Contents/Resources/AppIcon.icns"
cp "$ROOT/mispr/assets/icon.png" "$APP/Contents/Resources/icon.png"

cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key><string>Mispr Flow</string>
    <key>CFBundleDisplayName</key><string>Mispr Flow</string>
    <key>CFBundleIdentifier</key><string>$BUNDLE_ID</string>
    <key>CFBundleExecutable</key><string>MisprFlow</string>
    <key>CFBundleIconFile</key><string>AppIcon</string>
    <key>CFBundlePackageType</key><string>APPL</string>
    <key>CFBundleShortVersionString</key><string>$VERSION</string>
    <key>CFBundleVersion</key><string>1</string>
    <key>LSMinimumSystemVersion</key><string>14.0</string>
    <key>NSHighResolutionCapable</key><true/>
    <key>NSMicrophoneUsageDescription</key><string>Mispr Flow listens while you hold fn and turns your speech into text, entirely on this Mac.</string>
    <key>MisprProjectRoot</key><string>$ROOT</string>
    <key>MisprPython</key><string>$PYTHON</string>
</dict>
</plist>
PLIST

codesign --force --sign - --identifier "$BUNDLE_ID" "$APP" >/dev/null
echo "Built $APP"

if [ "${1:-}" = "--open" ]; then
    open "$APP"
fi
