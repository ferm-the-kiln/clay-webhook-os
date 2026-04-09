#!/bin/bash
# install-daemon.sh — Install clay-run as a macOS LaunchAgent (auto-starts on login)
#
# Usage:
#   bash scripts/install-daemon.sh          # install + start
#   bash scripts/install-daemon.sh --remove # uninstall + stop
#
# What it does:
#   - Creates a LaunchAgent plist at ~/Library/LaunchAgents/com.clay-webhook-os.runner.plist
#   - Configures it to run `python3.11 scripts/clay-run.py --daemon` on login
#   - Logs to ~/Library/Logs/clay-run-agent.log
#   - Auto-restarts if it crashes (KeepAlive = true)

set -e

LABEL="com.clay-webhook-os.runner"
PLIST_PATH="$HOME/Library/LaunchAgents/${LABEL}.plist"
LOG_PATH="$HOME/Library/Logs/clay-run-agent.log"

# Find the project root (relative to this script)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Find python3.11
PYTHON="/opt/homebrew/bin/python3.11"
if [ ! -f "$PYTHON" ]; then
    PYTHON="$(which python3.11 2>/dev/null || echo "")"
fi
if [ -z "$PYTHON" ] || [ ! -f "$PYTHON" ]; then
    echo "Error: python3.11 not found. Install it with: brew install python@3.11"
    exit 1
fi

CLAY_RUN="$PROJECT_DIR/scripts/clay-run.py"
if [ ! -f "$CLAY_RUN" ]; then
    echo "Error: clay-run.py not found at $CLAY_RUN"
    exit 1
fi

# ── Uninstall ──────────────────────────────────────────

if [ "$1" = "--remove" ] || [ "$1" = "--uninstall" ]; then
    echo "Removing clay-run daemon..."
    if launchctl list "$LABEL" &>/dev/null; then
        launchctl unload "$PLIST_PATH" 2>/dev/null || true
        echo "  Stopped daemon"
    fi
    if [ -f "$PLIST_PATH" ]; then
        rm "$PLIST_PATH"
        echo "  Removed $PLIST_PATH"
    fi
    # Clean up PID file
    rm -f "$HOME/.clay-run.pid"
    echo "Done. Daemon removed."
    exit 0
fi

# ── Install ────────────────────────────────────────────

echo "Installing clay-run daemon..."
echo "  Project: $PROJECT_DIR"
echo "  Python:  $PYTHON"
echo "  Script:  $CLAY_RUN"
echo "  Log:     $LOG_PATH"

# Stop existing if running
if launchctl list "$LABEL" &>/dev/null; then
    launchctl unload "$PLIST_PATH" 2>/dev/null || true
    echo "  Stopped existing daemon"
fi

# Create LaunchAgents dir if needed
mkdir -p "$HOME/Library/LaunchAgents"

# Write plist
cat > "$PLIST_PATH" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${LABEL}</string>

    <key>ProgramArguments</key>
    <array>
        <string>${PYTHON}</string>
        <string>${CLAY_RUN}</string>
        <string>--daemon</string>
    </array>

    <key>WorkingDirectory</key>
    <string>${PROJECT_DIR}</string>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>${LOG_PATH}</string>

    <key>StandardErrorPath</key>
    <string>${LOG_PATH}</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>${HOME}/.superset/bin:${HOME}/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
        <key>HOME</key>
        <string>${HOME}</string>
    </dict>

    <key>ThrottleInterval</key>
    <integer>10</integer>
</dict>
</plist>
PLIST

echo "  Created $PLIST_PATH"

# Load it
launchctl load "$PLIST_PATH"
echo "  Daemon started"

# Verify
sleep 2
if launchctl list "$LABEL" &>/dev/null; then
    PID=$(launchctl list "$LABEL" | awk 'NR==2{print $1}')
    echo ""
    echo "clay-run daemon is running (PID: $PID)"
    echo "  Logs: tail -f $LOG_PATH"
    echo "  Stop: launchctl unload $PLIST_PATH"
    echo "  Remove: bash $SCRIPT_DIR/install-daemon.sh --remove"
else
    echo ""
    echo "Warning: daemon may not have started. Check: launchctl list | grep clay"
    echo "  Logs: cat $LOG_PATH"
fi
