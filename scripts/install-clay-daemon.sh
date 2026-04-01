#!/bin/bash
# Install clay-run as a macOS LaunchAgent (background daemon).
# Runs automatically on login, picks up dashboard "Run" jobs, executes locally.
#
# Usage: bash scripts/install-clay-daemon.sh
# Remove: bash scripts/uninstall-clay-daemon.sh

set -e

LABEL="com.clay-webhook-os.clay-run"
PLIST_DIR="$HOME/Library/LaunchAgents"
PLIST_PATH="$PLIST_DIR/$LABEL.plist"
LOG_PATH="$HOME/Library/Logs/clay-run.log"

# Detect paths
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPT_PATH="$REPO_ROOT/scripts/clay-run.py"
PYTHON_PATH="/opt/homebrew/bin/python3.11"

if [ ! -f "$SCRIPT_PATH" ]; then
    echo "Error: clay-run.py not found at $SCRIPT_PATH"
    exit 1
fi

if [ ! -x "$PYTHON_PATH" ]; then
    echo "Error: Python not found at $PYTHON_PATH"
    exit 1
fi

# Check clay-run config exists
if [ ! -f "$HOME/.clay-run.json" ]; then
    echo "No ~/.clay-run.json found. Running setup first..."
    "$PYTHON_PATH" "$SCRIPT_PATH" --setup
fi

# Unload existing if present
if launchctl list 2>/dev/null | grep -q "$LABEL"; then
    echo "Stopping existing daemon..."
    launchctl unload "$PLIST_PATH" 2>/dev/null || true
fi

# Create log directory
mkdir -p "$(dirname "$LOG_PATH")"

# Create LaunchAgent plist
mkdir -p "$PLIST_DIR"
cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$LABEL</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON_PATH</string>
        <string>$SCRIPT_PATH</string>
        <string>--daemon</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>
    <key>StandardOutPath</key>
    <string>$LOG_PATH</string>
    <key>StandardErrorPath</key>
    <string>$LOG_PATH</string>
    <key>ThrottleInterval</key>
    <integer>10</integer>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>
EOF

# Load the daemon
launchctl load "$PLIST_PATH"

# Verify
sleep 2
if launchctl list 2>/dev/null | grep -q "$LABEL"; then
    echo ""
    echo "clay-run daemon installed and running."
    echo "  Plist: $PLIST_PATH"
    echo "  Logs:  $LOG_PATH"
    echo "  PID:   $(cat ~/.clay-run.pid 2>/dev/null || echo 'starting...')"
    echo ""
    echo "The daemon auto-starts on login and picks up dashboard Run jobs."
    echo "To remove: bash $REPO_ROOT/scripts/uninstall-clay-daemon.sh"
else
    echo "Warning: daemon may not have started. Check: launchctl list | grep clay"
fi
