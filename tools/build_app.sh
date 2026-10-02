#!/bin/bash
# Build build/Mispr Flow.app from macos/ (SwiftUI) for this machine: tools/build_app.sh [--open]
#
# The app runs the Python engine from this checkout's .venv, so it's a development build
# (the DMG will bundle Python instead). Signed with the local certificate from
# tools/make_signing_cert.sh if you've made one, else ad-hoc.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="$ROOT/build/Mispr Flow.app"
PYTHON="$ROOT/.venv/bin/python"
VERSION="1.1.0"
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
    <key>NSAppleEventsUsageDescription</key><string>Mispr Flow opens the folders you name by voice in Finder, and changes the volume when you ask. Only when you hold your voice command key.</string>
    <key>NSMicrophoneUsageDescription</key><string>Mispr Flow listens while you hold fn and turns your speech into text, entirely on this Mac.</string>
    <key>MisprProjectRoot</key><string>$ROOT</string>
    <key>MisprPython</key><string>$PYTHON</string>
</dict>
</plist>
PLIST

# Sign with the local certificate when it exists (tools/make_signing_cert.sh), so the
# signature, and with it macOS's permission grants, stays the same across rebuilds.
SIGN_ID="Mispr Flow Local Signing"
if security find-certificate -c "$SIGN_ID" >/dev/null 2>&1; then
    codesign --force --sign "$SIGN_ID" --identifier "$BUNDLE_ID" "$APP"
else
    codesign --force --sign - --identifier "$BUNDLE_ID" "$APP"
    echo "note: ad-hoc signed; macOS forgets permissions when the app changes. Run tools/make_signing_cert.sh once to fix that." >&2
fi
echo "Built $APP"

if [ "${1:-}" = "--open" ]; then
    open "$APP"
fi
