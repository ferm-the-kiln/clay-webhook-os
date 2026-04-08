#!/bin/bash
# Uninstall clay-run daemon + local backend LaunchAgents.
#
# Usage: bash scripts/uninstall-clay-daemon.sh

set -e

PLIST_DIR="$HOME/Library/LaunchAgents"

for LABEL in "com.clay-webhook-os.clay-run" "com.clay-webhook-os.backend"; do
    PLIST_PATH="$PLIST_DIR/$LABEL.plist"
    if [ -f "$PLIST_PATH" ]; then
        echo "Stopping $LABEL..."
        launchctl unload "$PLIST_PATH" 2>/dev/null || true
        rm "$PLIST_PATH"
        echo "  Removed."
    else
        echo "No LaunchAgent found for $LABEL"
    fi
done

# Clean up PID and heartbeat files
rm -f "$HOME/.clay-run.pid" "$HOME/.clay-run-heartbeat"
echo "Cleanup complete."
