#!/usr/bin/env bash
set -euo pipefail

# Clay Webhook OS — Deploy Script
# Pulls latest code and restarts the service

PROJECT_DIR="/opt/clay-webhook-os"
cd "$PROJECT_DIR"

echo "=== Deploying Clay Webhook OS ==="

# Pull latest
echo "[1/3] Pulling latest code..."
git pull origin main

# Install any new dependencies
echo "[2/3] Installing dependencies..."
.venv/bin/pip install -q -e .

# Fix ownership (git pull creates files as root, service runs as clay)
echo "[3/4] Fixing file ownership..."
chown -R clay:clay "$PROJECT_DIR/functions" "$PROJECT_DIR/data" "$PROJECT_DIR/skills" "$PROJECT_DIR/pipelines" 2>/dev/null || true

# Restart service
echo "[4/4] Restarting service..."
systemctl restart clay-webhook-os

echo "=== Deploy complete ==="
systemctl status clay-webhook-os --no-pager
