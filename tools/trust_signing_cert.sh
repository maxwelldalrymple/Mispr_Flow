#!/bin/bash
# One-time, after tools/make_signing_cert.sh: trust "Mispr Flow Local Signing" for code signing.
#
# Why: for Screen & System Audio, macOS only stores a lasting grant ("this app from this
# signer") when the signing certificate is trusted; for an untrusted one it pins the grant to
# that exact build, so every rebuild silently loses it. Accessibility doesn't have this issue.
#
# This marks the certificate as trusted for code signing only, in your login keychain. macOS
# asks for your password. Undo anytime in Keychain Access (certificate > Trust > Use System Defaults).
set -euo pipefail

NAME="Mispr Flow Local Signing"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
security find-certificate -c "$NAME" -p > "$TMP/cert.pem" || { echo "Run tools/make_signing_cert.sh first." >&2; exit 1; }
security add-trusted-cert -r trustRoot -p codeSign -k "$HOME/Library/Keychains/login.keychain-db" "$TMP/cert.pem"
echo "Trusted \"$NAME\" for code signing."
echo "Now reset the old grant, then allow Mispr Flow once more and restart it:"
echo "  tccutil reset ScreenCapture io.github.maxwelldalrymple.MisprFlow"
