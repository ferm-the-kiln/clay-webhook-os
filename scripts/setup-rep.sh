#!/bin/bash
# Setup script for new sales reps — installs everything needed to run
# Clay Webhook OS locally with their own Claude Code Max subscription.
#
# Usage: bash scripts/setup-rep.sh
#
# Prerequisites:
#   - macOS with Homebrew
#   - Claude Code installed and logged in (claude.ai/download)
#   - Claude Code Max subscription active

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON_PATH="/opt/homebrew/bin/python3.11"

echo ""
echo "=== Clay Webhook OS — Rep Setup ==="
echo ""

# ── 1. Check Claude Code ────────────────────────────────

echo "[1/6] Checking Claude Code..."

if ! command -v claude &> /dev/null; then
    echo "  ERROR: Claude Code CLI not found."
    echo "  Install it from: https://claude.ai/download"
    echo "  Then run: claude login"
    exit 1
fi

# Strip ANTHROPIC_API_KEY to get real subscription info
AUTH_JSON=$(env -u ANTHROPIC_API_KEY claude auth status 2>&1)
LOGGED_IN=$(echo "$AUTH_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('loggedIn', False))" 2>/dev/null || echo "False")
SUB_TYPE=$(echo "$AUTH_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('subscriptionType', 'none'))" 2>/dev/null || echo "none")
EMAIL=$(echo "$AUTH_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('email', 'unknown'))" 2>/dev/null || echo "unknown")

if [ "$LOGGED_IN" != "True" ]; then
    echo "  ERROR: Claude Code is not logged in."
    echo "  Run: claude login"
    exit 1
fi

if [ "$SUB_TYPE" != "max" ]; then
    echo "  WARNING: Subscription type is '$SUB_TYPE' (expected 'max')."
    echo "  Claude Code Max is recommended for best performance."
    echo "  Continuing anyway..."
fi

echo "  Claude Code: OK"
echo "  Account: $EMAIL"
echo "  Subscription: $SUB_TYPE"

# ── 2. Check Python ─────────────────────────────────────

echo ""
echo "[2/6] Checking Python..."

if [ ! -x "$PYTHON_PATH" ]; then
    echo "  Python 3.11 not found at $PYTHON_PATH"
    echo "  Installing via Homebrew..."
    brew install python@3.11
fi

echo "  Python: $($PYTHON_PATH --version)"

# ── 3. Install Python dependencies ──────────────────────

echo ""
echo "[3/6] Installing Python dependencies..."

cd "$REPO_ROOT"

if [ ! -d ".venv" ]; then
    $PYTHON_PATH -m venv .venv
    echo "  Created virtual environment"
fi

source .venv/bin/activate
pip install -q -e . 2>&1 | tail -1
pip install -q requests 2>&1 | tail -1
echo "  Dependencies installed"

# ── 4. Setup environment ────────────────────────────────

echo ""
echo "[4/6] Setting up environment..."

if [ ! -f ".env" ]; then
    cp .env.example .env
    # Generate a random API key for local use
    LOCAL_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s/change-me/$LOCAL_KEY/" .env
    else
        sed -i "s/change-me/$LOCAL_KEY/" .env
    fi
    echo "  Created .env with local API key"
else
    echo "  .env already exists — skipping"
fi

# Setup dashboard env
if [ ! -f "dashboard/.env.local" ]; then
    API_KEY=$(grep WEBHOOK_API_KEY .env | cut -d= -f2)
    cat > dashboard/.env.local << EOF
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_API_KEY=$API_KEY
EOF
    echo "  Created dashboard/.env.local (pointing to localhost)"
else
    echo "  dashboard/.env.local already exists — skipping"
    echo "  NOTE: Verify NEXT_PUBLIC_API_URL=http://localhost:8000"
fi

# ── 5. Install dashboard dependencies ───────────────────

echo ""
echo "[5/6] Installing dashboard dependencies..."

cd "$REPO_ROOT/dashboard"
if [ ! -d "node_modules" ]; then
    npm install --silent 2>&1 | tail -1
    echo "  Dashboard dependencies installed"
else
    echo "  node_modules exists — skipping (run 'npm install' to update)"
fi

# ── 6. Install clay-run daemon ──────────────────────────

echo ""
echo "[6/6] Installing clay-run daemon..."

cd "$REPO_ROOT"
bash scripts/install-clay-daemon.sh

# ── Done ────────────────────────────────────────────────

echo ""
echo "============================================"
echo "  Setup complete!"
echo "============================================"
echo ""
echo "  Account:      $EMAIL"
echo "  Subscription: $SUB_TYPE"
echo "  Backend:      http://localhost:8000"
echo "  Dashboard:    http://localhost:3000"
echo ""
echo "  To start:"
echo "    Terminal 1:  cd $REPO_ROOT && source .venv/bin/activate && uvicorn app.main:app --port 8000"
echo "    Terminal 2:  cd $REPO_ROOT/dashboard && npm run dev"
echo ""
echo "  Then open http://localhost:3000"
echo "  The 'Connected' badge will show your subscription info."
echo ""
