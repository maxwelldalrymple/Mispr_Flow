#!/bin/bash
# Build dist/Mispr-Flow-<version>.dmg: a clean, self-contained app for Apple Silicon Macs.
#
#   tools/build_dmg.sh
#
# The app carries its own Python (a relocatable CPython 3.13 build) with the pinned
# requirements, and a copy of the mispr/ package, nothing else: no recordings, notes, contacts,
# settings or models. On first run the app creates its folders in ~/Library and setup
# downloads the models. The build fails if any personal data or path of this Mac is found in it.
#
# Signed ad-hoc (no Apple Developer ID): first open needs right-click > Open, see the README.
# Writes the DMG and its SHA-256 next to it in dist/.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(sed -n 's/^VERSION="\(.*\)"/\1/p' "$ROOT/tools/build_app.sh")"
STANDALONE="${MISPR_STANDALONE_PYTHON:-$HOME/.local/share/uv/python/cpython-3.13.15-macos-aarch64-none}"
PYCACHE="$ROOT/build/dmg-python"            # the bundled Python with requirements, reused between builds
STAGE="$ROOT/build/dmg-stage"
APP="$STAGE/Mispr Flow.app"
DMG="$ROOT/dist/Mispr-Flow-$VERSION.dmg"
export MACOSX_DEPLOYMENT_TARGET=14.0

[ -x "$STANDALONE/bin/python3" ] || { echo "missing standalone Python at $STANDALONE (set MISPR_STANDALONE_PYTHON)" >&2; exit 1; }

# 1. Python with the pinned requirements, built for macOS 14+. llama.cpp is compiled with Metal
#    and without curl/OpenSSL: it never downloads anything itself (models.py does, over HTTPS).
STAMP="$(cat "$ROOT/requirements.txt" "$0" | shasum -a 256 | cut -c1-16)"
if [ "$(cat "$PYCACHE/.stamp" 2>/dev/null)" != "$STAMP" ]; then
    echo "Building the bundled Python (compiles llama.cpp, takes a few minutes)…"
    rm -rf "$PYCACHE"
    cp -R "$STANDALONE" "$PYCACHE"
    rm -f "$PYCACHE/lib/python3.13/EXTERNALLY-MANAGED"  # our own copy, not the installed Python
    CMAKE_ARGS="-DGGML_METAL=on -DLLAMA_CURL=OFF -DLLAMA_OPENSSL=OFF -DCMAKE_OSX_DEPLOYMENT_TARGET=14.0" \
        "$PYCACHE/bin/python3" -m pip install --no-cache-dir --disable-pip-version-check -r "$ROOT/requirements.txt"
    "$PYCACHE/bin/python3" -m pip uninstall -y -q pip
    rm -rf "$PYCACHE"/lib/python3.13/{test,idlelib,tkinter,turtledemo,ensurepip} "$PYCACHE"/lib/{tcl,tk,itcl,thread}* \
           "$PYCACHE"/bin/{idle3*,pip*,pydoc3*,python3*-config} "$PYCACHE/share" "$PYCACHE/BUILD"
    echo "$STAMP" > "$PYCACHE/.stamp"
fi

# 2. The app: the normal build, then swap the checkout paths for the bundled Python and engine.
"$ROOT/tools/build_app.sh"
rm -rf "$STAGE" && mkdir -p "$STAGE"
ditto "$ROOT/build/Mispr Flow.app" "$APP"
ditto "$PYCACHE" "$APP/Contents/Resources/python"
rm -f "$APP/Contents/Resources/python/.stamp"
strip -S -x "$APP/Contents/MacOS/MisprFlow"  # debug symbols name this checkout's build paths
rsync -a --exclude __pycache__ --exclude '*.pyc' "$ROOT/mispr" "$APP/Contents/Resources/engine/"
PLIST="$APP/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Delete :MisprProjectRoot" -c "Delete :MisprPython" -c "Add :MisprBundled bool true" "$PLIST"
# uv wrote its install folder into the runtime: give libpython a relative name and sysconfig the
# standalone build's neutral prefix.
PYLIB="$APP/Contents/Resources/python/lib"
install_name_tool -id @rpath/libpython3.13.dylib "$PYLIB/libpython3.13.dylib" 2>/dev/null
sed -i '' "s#$STANDALONE#/install#g" "$PYLIB"/python3.13/_sysconfigdata_*.py
# Only the interpreter in bin/: the libraries' command-line launchers name the build folder.
find "$APP/Contents/Resources/python/bin" -mindepth 1 -not -name python3 -not -name python3.13 -delete
# Bytecode now, so Python never writes into the signed app. pip's caches name the build folder,
# so they're rebuilt with paths relative to the app.
find "$APP/Contents/Resources" -name __pycache__ -type d -prune -exec rm -rf {} +
"$APP/Contents/Resources/python/bin/python3" -m compileall -q -j 0 -s "$APP/Contents/Resources" -p "" \
    "$APP/Contents/Resources/engine" "$APP/Contents/Resources/python/lib" >/dev/null || true

# 3. Checks: only code in the app, nothing that points at or came from this Mac.
fail() { echo "DMG check failed: $*" >&2; exit 1; }
# The engine holds only files committed to git (no local or generated files).
untracked="$(cd "$APP/Contents/Resources/engine" && find mispr -type f -not -path '*/__pycache__/*' | sort \
    | comm -23 - <(git -C "$ROOT" ls-files mispr | sort))"
[ -z "$untracked" ] || fail "files not in git:"$'\n'"$untracked"
personal="$(find "$APP" -not -path '*/engine/mispr/assets/sounds/*' \( -iname '*.wav' -o -iname '*.m4a' -o -iname '*.mp3' -o -iname '*.gguf' -o -iname 'ggml-*.bin' \
    -o -iname '*.onnx' -o -name 'settings.json' -o -name 'people.json' -o -name 'prompts*.json' -o -name 'profile*.json' -o -name '*recordings*' \
    -o -name 'engine.log' -o -name '.env' \) -print)"
[ -z "$personal" ] || fail "data files in the app:"$'\n'"$personal"
leaks="$(grep -rlI -e "$HOME" -e "$(id -un)@" -e "maxbballpro" "$APP" 2>/dev/null || true)"
binleaks="$(grep -rl --binary-files=binary -e "$HOME/" "$APP" 2>/dev/null || true)"
[ -z "$leaks$binleaks" ] || fail "this Mac's paths or your name are inside:"$'\n'"$leaks$binleaks"
while IFS= read -r f; do
    deps="$(otool -L "$f" 2>/dev/null | grep $'^\t' | grep -E '/opt/homebrew|/usr/local|/Users/' || true)"
    [ -z "$deps" ] || fail "$f links outside the app: $deps"
    minos="$(otool -l "$f" | awk '/LC_BUILD_VERSION/{b=1} b&&/minos/{print $2; exit}')"
    [ -z "$minos" ] || [ "${minos%%.*}" -le 14 ] || fail "$f needs macOS $minos (want 14)"
done < <(find "$APP/Contents/Resources" -type f \( -name '*.so' -o -name '*.dylib' -o -perm +111 \) -exec sh -c 'file -b "$1" | grep -q Mach-O && echo "$1"' _ {} \;)

# 4. Sign (ad-hoc: inside out, then the app), and package with an Applications shortcut.
find "$APP/Contents/Resources" -type f \( -name '*.so' -o -name '*.dylib' -o -perm +111 \) \
    -exec sh -c 'file -b "$1" | grep -q Mach-O && codesign --force --sign - "$1"' _ {} \;
codesign --force --sign - --identifier "io.github.maxwelldalrymple.MisprFlow" "$APP"
codesign --verify --deep --strict "$APP"
ln -s /Applications "$STAGE/Applications"
mkdir -p "$ROOT/dist" && rm -f "$DMG"
hdiutil create -quiet -volname "Mispr Flow" -srcfolder "$STAGE" -fs HFS+ -format UDZO "$DMG"
(cd "$ROOT/dist" && shasum -a 256 "$(basename "$DMG")" > "$(basename "$DMG").sha256")
echo "Built $DMG ($(du -h "$DMG" | cut -f1))"
cat "$DMG.sha256"
