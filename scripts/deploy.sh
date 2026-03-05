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

# Restart service
echo "[3/3] Restarting service..."
systemctl restart clay-webhook-os

echo "=== Deploy complete ==="
systemctl status clay-webhook-os --no-pager
