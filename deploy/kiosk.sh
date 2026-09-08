#!/usr/bin/env bash
# Launch Chromium in kiosk mode against the local dashboard.
set -euo pipefail

BROWSER="${BROWSER:-chromium}"
URL="${URL:-http://localhost:8000}"

exec "${BROWSER}" \
  --kiosk \
  --noerrdialogs \
  --disable-gpu \
  --no-sandbox \
  --disable-features=TranslateUI \
  --check-for-update-interval=31536000 \
  "${URL}"
