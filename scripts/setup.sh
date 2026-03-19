#!/usr/bin/env bash
set -euo pipefail

# Clay Webhook OS — VPS Setup Script
# Run on a fresh Ubuntu 22.04+ server

echo "=== Clay Webhook OS — Setup ==="

# 1. System packages
echo "[1/6] Installing system packages..."
apt-get update -qq
apt-get install -y -qq python3.12 python3.12-venv python3-pip nginx certbot python3-certbot-nginx git curl

# 2. Node.js (for Claude CLI)
echo "[2/6] Installing Node.js..."
if ! command -v node &>/dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y -qq nodejs
fi

# 3. Claude Code CLI
echo "[3/6] Installing Claude Code CLI..."
if ! command -v claude &>/dev/null; then
    npm install -g @anthropic-ai/claude-code
    echo ">>> Run 'claude login' and authenticate via browser <<<"
    echo ">>> Then verify: echo 'Say hello' | claude --print - <<<"
fi

# 4. Project setup
echo "[4/6] Setting up project..."
PROJECT_DIR="/opt/clay-webhook-os"
if [ ! -d "$PROJECT_DIR" ]; then
    git clone https://github.com/ferm-the-kiln/clay-webhook-os.git "$PROJECT_DIR"
fi
cd "$PROJECT_DIR"
python3.12 -m venv .venv
.venv/bin/pip install -q -e .

# 5. Environment file
echo "[5/6] Setting up environment..."
if [ ! -f .env ]; then
    cp .env.example .env
    API_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    sed -i "s/change-me/$API_KEY/" .env
    echo ">>> Generated API key: $API_KEY <<<"
    echo ">>> Save this — you'll need it for Clay HTTP Actions <<<"
fi

# 6. Systemd service
echo "[6/6] Installing systemd service..."
cat > /etc/systemd/system/clay-webhook-os.service << 'EOF'
[Unit]
Description=Clay Webhook OS
After=network.target

[Service]
Type=simple
User=clay
# NOTE: Create the 'clay' user on VPS before deploying:
#   useradd -r -s /bin/bash -d /opt/clay-webhook-os clay
#   chown -R clay:clay /opt/clay-webhook-os
WorkingDirectory=/opt/clay-webhook-os
ExecStart=/opt/clay-webhook-os/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
Environment=PATH=/usr/local/bin:/usr/bin:/bin

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable clay-webhook-os
systemctl start clay-webhook-os

echo ""
echo "=== Setup Complete ==="
echo "Service running on port 8000"
echo "Next steps:"
echo "  1. Run 'claude login' if not already authenticated"
echo "  2. Set up nginx + SSL: certbot --nginx -d your-domain.com"
echo "  3. Test: curl http://localhost:8000/health"
