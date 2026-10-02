#!/bin/bash
# Build, sign and publish a release that installed copies pick up by themselves:
#   tools/release.sh 1.2.0            a stable release: installed automatically (when idle)
#   tools/release.sh 1.3.0-beta.1 --beta   a beta: GitHub "pre-release", only offered in Settings
#
# Sets VERSION in tools/build_app.sh, builds dist/Mispr-Flow-<version>.dmg (+ .sha256, .sig) with
# tools/build_dmg.sh, and creates the GitHub release with all three. Notes come from
# dist/notes-<version>.md if it exists. Run it from main, with the changes merged.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="${1:?usage: tools/release.sh <version> [--beta]}"
BETA="${2:-}"
[[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-beta\.[0-9]+)?$ ]] || { echo "version must look like 1.2.0 or 1.3.0-beta.1" >&2; exit 1; }
[[ "$VERSION" == *-beta.* && "$BETA" != "--beta" ]] && { echo "a -beta version needs --beta" >&2; exit 1; }

sed -i '' "s/^VERSION=\".*\"/VERSION=\"$VERSION\"/" "$ROOT/tools/build_app.sh"
"$ROOT/tools/build_dmg.sh"
DMG="$ROOT/dist/Mispr-Flow-$VERSION.dmg"
NOTES="$ROOT/dist/notes-$VERSION.md"
[ -f "$NOTES" ] || printf 'Mispr Flow %s. See CHANGELOG.md.\n' "$VERSION" > "$NOTES"
gh release create "v$VERSION" "$DMG" "$DMG.sha256" "$DMG.sig" --target main --title "Mispr Flow $VERSION" \
    --notes-file "$NOTES" ${BETA:+--prerelease}
echo "Published v$VERSION$([ -n "$BETA" ] && echo ' (beta)')"
