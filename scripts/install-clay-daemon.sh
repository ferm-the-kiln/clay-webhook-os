#!/bin/bash
# Install clay-run daemon + local backend as macOS LaunchAgents.
# Both auto-start on login. The daemon picks up dashboard "Run" jobs,
# the backend serves the API locally on port 8000.
#
# Usage: bash scripts/install-clay-daemon.sh
# Remove: bash scripts/uninstall-clay-daemon.sh

set -e

DAEMON_LABEL="com.clay-webhook-os.clay-run"
BACKEND_LABEL="com.clay-webhook-os.backend"
PLIST_DIR="$HOME/Library/LaunchAgents"
DAEMON_PLIST="$PLIST_DIR/$DAEMON_LABEL.plist"
BACKEND_PLIST="$PLIST_DIR/$BACKEND_LABEL.plist"
DAEMON_LOG="$HOME/Library/Logs/clay-run.log"
BACKEND_LOG="$HOME/Library/Logs/clay-backend.log"

# Detect paths
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPT_PATH="$REPO_ROOT/scripts/clay-run.py"
PYTHON_PATH="/opt/homebrew/bin/python3.11"
VENV_PYTHON="$REPO_ROOT/.venv/bin/python"

if [ ! -f "$SCRIPT_PATH" ]; then
    echo "Error: clay-run.py not found at $SCRIPT_PATH"
    exit 1
fi

if [ ! -x "$PYTHON_PATH" ]; then
    echo "Error: Python not found at $PYTHON_PATH"
    exit 1
fi

if [ ! -x "$VENV_PYTHON" ]; then
    echo "Error: venv not found at $REPO_ROOT/.venv — run: python3.11 -m venv .venv && pip install -e ."
    exit 1
fi

# Check clay-run config exists — default to localhost
if [ ! -f "$HOME/.clay-run.json" ]; then
    echo "No ~/.clay-run.json found. Running setup first..."
    "$PYTHON_PATH" "$SCRIPT_PATH" --setup
fi

# --- Backend LaunchAgent ---

if launchctl list 2>/dev/null | grep -q "$BACKEND_LABEL"; then
    echo "Stopping existing backend..."
    launchctl unload "$BACKEND_PLIST" 2>/dev/null || true
fi

mkdir -p "$PLIST_DIR" "$(dirname "$BACKEND_LOG")"
cat > "$BACKEND_PLIST" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$BACKEND_LABEL</string>
    <key>ProgramArguments</key>
    <array>
        <string>$VENV_PYTHON</string>
        <string>-m</string>
        <string>uvicorn</string>
        <string>app.main:app</string>
        <string>--host</string>
        <string>0.0.0.0</string>
        <string>--port</string>
        <string>8000</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$REPO_ROOT</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>
    <key>StandardOutPath</key>
    <string>$BACKEND_LOG</string>
    <key>StandardErrorPath</key>
    <string>$BACKEND_LOG</string>
    <key>ThrottleInterval</key>
    <integer>10</integer>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>$REPO_ROOT/.venv/bin:$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
        <key>HOME</key>
        <string>$HOME</string>
    </dict>
</dict>
</plist>
EOF

launchctl load "$BACKEND_PLIST"

# --- Daemon LaunchAgent ---

if launchctl list 2>/dev/null | grep -q "$DAEMON_LABEL"; then
    echo "Stopping existing daemon..."
    launchctl unload "$DAEMON_PLIST" 2>/dev/null || true
fi

cat > "$DAEMON_PLIST" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$DAEMON_LABEL</string>
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
    <string>$DAEMON_LOG</string>
    <key>StandardErrorPath</key>
    <string>$DAEMON_LOG</string>
    <key>ThrottleInterval</key>
    <integer>10</integer>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>$HOME/.superset/bin:$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
        <key>HOME</key>
        <string>$HOME</string>
    </dict>
</dict>
</plist>
EOF

launchctl load "$DAEMON_PLIST"

# --- Verify ---
sleep 2
echo ""

if launchctl list 2>/dev/null | grep -q "$BACKEND_LABEL"; then
    echo "Backend installed and running."
    echo "  Plist: $BACKEND_PLIST"
    echo "  Logs:  $BACKEND_LOG"
    echo "  URL:   http://localhost:8000"
else
    echo "Warning: backend may not have started. Check: launchctl list | grep clay"
fi

echo ""

if launchctl list 2>/dev/null | grep -q "$DAEMON_LABEL"; then
    echo "clay-run daemon installed and running."
    echo "  Plist: $DAEMON_PLIST"
    echo "  Logs:  $DAEMON_LOG"
    echo "  PID:   $(cat ~/.clay-run.pid 2>/dev/null || echo 'starting...')"
else
    echo "Warning: daemon may not have started. Check: launchctl list | grep clay"
fi

echo ""
echo "Both auto-start on login. To remove: bash $REPO_ROOT/scripts/uninstall-clay-daemon.sh"
