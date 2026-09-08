#!/usr/bin/env bash
# Install a macOS LaunchAgent for Logos Workspace (label com.logosworkspace.os)
# on https://127.0.0.1:8090. The legacy English Cockpit OS agent
# (com.englishcockpit.os, port 8000) is left untouched.
#
# Override the port with: PORT=8081 ./deploy/macos/install-logos-agent.sh
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
PYTHON="$APP_DIR/.venv/bin/python"
LABEL="com.logosworkspace.os"
PORT="${PORT:-8090}"
HOST="${HOST:-127.0.0.1}"
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
    <key>EnvironmentVariables</key>
    <dict>
        <key>HOST</key>
        <string>$HOST</string>
        <key>PORT</key>
        <string>$PORT</string>
    </dict>
    <key>WorkingDirectory</key>
    <string>$APP_DIR</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$APP_DIR/data/logos-agent.log</string>
    <key>StandardErrorPath</key>
    <string>$APP_DIR/data/logos-agent.log</string>
</dict>
</plist>
EOF

launchctl bootout "gui/$(id -u)" "$PLIST" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"

echo "Installed and started $LABEL on https://$HOST:$PORT"
echo "Logs: $APP_DIR/data/logos-agent.log"
