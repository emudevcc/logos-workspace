#!/usr/bin/env bash
# Open the dashboard in a standalone app-mode Chrome window (no tabs/address bar).
set -euo pipefail

URL="${COCKPIT_URL:-https://localhost:8000}"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

if [ -x "$CHROME" ]; then
  "$CHROME" --app="$URL" --new-window &
else
  echo "Chrome not found; opening in the default browser." >&2
  open "$URL"
fi
