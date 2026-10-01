#!/bin/bash
# One-time: create a local code-signing certificate, "Mispr Flow Local Signing", in your
# login keychain. tools/build_app.sh signs with it, so every build has the same signature
# and macOS keeps Mispr Flow's Microphone and Accessibility permissions across rebuilds.
# (With ad-hoc signing, each build looks like a new app and the permissions are dropped.)
#
# The certificate is self-signed, stays on this Mac, and is only used to sign Mispr Flow.
# Remove it anytime in Keychain Access (login keychain, "My Certificates").
set -euo pipefail

NAME="Mispr Flow Local Signing"
if security find-certificate -c "$NAME" >/dev/null 2>&1; then
    echo "\"$NAME\" already exists."
    exit 0
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
cat > "$TMP/cert.cnf" <<EOF
[ req ]
distinguished_name = dn
x509_extensions = ext
prompt = no
[ dn ]
CN = $NAME
[ ext ]
basicConstraints = critical,CA:false
keyUsage = critical,digitalSignature
extendedKeyUsage = critical,codeSigning
EOF
openssl req -x509 -newkey rsa:2048 -nodes -keyout "$TMP/key.pem" -out "$TMP/cert.pem" \
    -days 3650 -config "$TMP/cert.cnf" 2>/dev/null
PASS="$(openssl rand -hex 12)"
openssl pkcs12 -export -legacy -inkey "$TMP/key.pem" -in "$TMP/cert.pem" -name "$NAME" \
    -out "$TMP/id.p12" -passout "pass:$PASS"
security import "$TMP/id.p12" -k "$HOME/Library/Keychains/login.keychain-db" -P "$PASS" -T /usr/bin/codesign
echo "Created \"$NAME\". Rebuild with tools/build_app.sh --open, then allow Mispr Flow's permissions one last time."
