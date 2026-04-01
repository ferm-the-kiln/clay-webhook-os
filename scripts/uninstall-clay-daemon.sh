#!/bin/bash
# Uninstall the clay-run LaunchAgent daemon.
#
# Usage: bash scripts/uninstall-clay-daemon.sh

set -e

LABEL="com.clay-webhook-os.clay-run"
PLIST_PATH="$HOME/Library/LaunchAgents/$LABEL.plist"

if [ -f "$PLIST_PATH" ]; then
    echo "Stopping daemon..."
    launchctl unload "$PLIST_PATH" 2>/dev/null || true
    rm "$PLIST_PATH"
    echo "LaunchAgent removed."
else
    echo "No LaunchAgent found at $PLIST_PATH"
fi

# Clean up PID and heartbeat files
rm -f "$HOME/.clay-run.pid" "$HOME/.clay-run-heartbeat"
echo "Cleanup complete."
