#!/usr/bin/env bash
# Install a macOS LaunchAgent so English Cockpit OS starts on login and
# restarts automatically if it crashes.
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
PYTHON="$APP_DIR/.venv/bin/python"
LABEL="com.englishcockpit.os"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

if [ ! -x "$PYTHON" ]; then
  echo "Missing venv: $PYTHON" >&2
  echo "Create it first: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi

mkdir -p "$HOME/Library/LaunchAgents" "$APP_DIR/data"

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$LABEL</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON</string>
        <string>-m</string>
        <string>app</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$APP_DIR</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$APP_DIR/data/agent.log</string>
    <key>StandardErrorPath</key>
    <string>$APP_DIR/data/agent.log</string>
</dict>
</plist>
EOF

launchctl bootout "gui/$(id -u)" "$PLIST" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"

echo "Installed and started $LABEL."
echo "Logs: $APP_DIR/data/agent.log"
