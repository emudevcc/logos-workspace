#!/usr/bin/env bash
# Generate a locally-trusted HTTPS certificate for the macOS target.
#
# Requires mkcert:  brew install mkcert
# Run once. Writes deploy/certs/localhost.{pem,key} (gitignored).
set -euo pipefail

CERT_DIR="${CERT_DIR:-deploy/certs}"
mkdir -p "$CERT_DIR"

HOSTNAME="$(scutil --get LocalHostName 2>/dev/null || echo localhost)"
LAN_IP="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || true)"

HOSTS=(localhost 127.0.0.1 ::1)
[ -n "$LAN_IP" ] && HOSTS+=("$LAN_IP")
HOSTS+=("${HOSTNAME}.local")

echo "Generating a certificate for: ${HOSTS[*]}"
mkcert -key-file "$CERT_DIR/localhost-key.pem" -cert-file "$CERT_DIR/localhost.pem" "${HOSTS[@]}"

# Trust the local CA (asks for your password once). Not fatal if run without a terminal.
mkcert -install || echo "NOTE: run 'mkcert -install' in a terminal to trust the certificate."

cat <<EOF

Done. Add these lines to your .env to serve over HTTPS:

  HOST=0.0.0.0
  PORT=8000
  TLS_CERTFILE=$CERT_DIR/localhost.pem
  TLS_KEYFILE=$CERT_DIR/localhost-key.pem

Then open https://localhost:8000 (or https://${LAN_IP:-<lan-ip>}:8000 from another device).
EOF
