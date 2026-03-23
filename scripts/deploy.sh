#!/usr/bin/env bash
set -euo pipefail

# Clay Webhook OS — Deploy Script
# Pulls latest code, installs deps, restarts service, verifies health.
# Rolls back to previous commit on health check failure.

PROJECT_DIR="/opt/clay-webhook-os"
HEALTH_URL="http://localhost:8000/health"
HEALTH_RETRIES=3
HEALTH_DELAY=3

cd "$PROJECT_DIR"

log() { echo "[$(date '+%H:%M:%S')] $*"; }

# --- Pre-flight checks ---
log "=== Deploying Clay Webhook OS ==="

PREV_COMMIT=$(git rev-parse HEAD)
log "Current commit: $PREV_COMMIT"

DISK_FREE=$(df -m "$PROJECT_DIR" | awk 'NR==2 {print $4}')
if [ "$DISK_FREE" -lt 100 ]; then
    log "ERROR: Only ${DISK_FREE}MB free disk space. Aborting."
    exit 1
fi

# --- Pull latest ---
log "[1/5] Pulling latest code..."
git pull origin main
NEW_COMMIT=$(git rev-parse HEAD)
log "New commit: $NEW_COMMIT"

if [ "$PREV_COMMIT" = "$NEW_COMMIT" ]; then
    log "Already up to date. No deploy needed."
    exit 0
fi

# --- Install dependencies ---
log "[2/5] Installing dependencies..."
.venv/bin/pip install -q -e .

# --- Fix ownership ---
log "[3/5] Fixing file ownership..."
chown -R clay:clay "$PROJECT_DIR/functions" "$PROJECT_DIR/data" "$PROJECT_DIR/skills" "$PROJECT_DIR/pipelines" "$PROJECT_DIR/knowledge_base" "$PROJECT_DIR/clients" 2>/dev/null || true

# --- Restart service ---
log "[4/5] Restarting service..."
systemctl restart clay-webhook-os

# --- Health check with retries ---
log "[5/5] Verifying health..."
HEALTHY=false
for i in $(seq 1 $HEALTH_RETRIES); do
    sleep $HEALTH_DELAY
    if curl -sf "$HEALTH_URL" > /dev/null 2>&1; then
        HEALTHY=true
        log "Health check passed (attempt $i/$HEALTH_RETRIES)"
        break
    fi
    log "Health check failed (attempt $i/$HEALTH_RETRIES)"
done

if [ "$HEALTHY" = true ]; then
    # Restart channel server if active
    if systemctl is-active clay-chat-channel >/dev/null 2>&1; then
        log "Restarting channel server..."
        if [ -f "$PROJECT_DIR/channel-server/package.json" ]; then
            cd "$PROJECT_DIR/channel-server" && bun install --frozen-lockfile 2>/dev/null || true
            cd "$PROJECT_DIR"
        fi
        systemctl restart clay-chat-channel
        log "Channel server restarted"
    fi
    log "=== Deploy successful ==="
    systemctl status clay-webhook-os --no-pager
else
    log "ERROR: Health check failed after $HEALTH_RETRIES attempts. Rolling back..."
    git checkout "$PREV_COMMIT"
    .venv/bin/pip install -q -e .
    chown -R clay:clay "$PROJECT_DIR/functions" "$PROJECT_DIR/data" "$PROJECT_DIR/skills" "$PROJECT_DIR/pipelines" "$PROJECT_DIR/knowledge_base" "$PROJECT_DIR/clients" 2>/dev/null || true
    systemctl restart clay-webhook-os
    sleep $HEALTH_DELAY
    if curl -sf "$HEALTH_URL" > /dev/null 2>&1; then
        log "Rollback successful. Service restored to $PREV_COMMIT"
    else
        log "CRITICAL: Rollback also failed. Manual intervention required."
    fi
    exit 1
fi
