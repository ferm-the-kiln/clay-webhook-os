# Clay Webhook OS — VPS Setup Log

> Reference doc for everything we did to deploy the webhook server.
> Server: Hetzner CX22 | IP: 178.156.249.201 | Domain: clay.nomynoms.com

## 1. Hetzner Server Provisioned

- **Provider:** Hetzner Cloud
- **Plan:** CX22 (Cost-Optimized, x86) — 2 vCPU, 4GB RAM, 40GB SSD
- **Location:** Ashburn, VA (us-east)
- **OS:** Ubuntu 24.04 LTS
- **Cost:** $5.59/mo ($4.99 server + $0.60 IPv4)
- **IP:** 178.156.249.201

## 2. SSH Key Generated (on Mac)

```bash
ssh-keygen -t ed25519 -C "fermin@thekiln.com"
# Key saved at: ~/.ssh/id_ed25519
# Public key added to Hetzner during server creation
```

Connect: `ssh root@178.156.249.201`

## 3. System Packages Installed

```bash
apt-get update -qq
apt-get install -y python3 python3-venv python3-pip git curl
# nginx and certbot installed separately (initial paste got mangled):
apt install -y nginx
apt install -y certbot python3-certbot-nginx
```

## 4. Node.js + Claude CLI Installed

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs
npm install -g @anthropic-ai/claude-code
```

## 5. Claude Login

```bash
claude login
# Already authenticated via: fermin@thekiln.com / The Kiln / Team subscription
```

Verified: `echo "Say hello" | claude --print -`

## 6. Repo Cloned + App Installed

```bash
git clone https://github.com/ferm-the-kiln/clay-webhook-os.git /opt/clay-webhook-os
cd /opt/clay-webhook-os && python3 -m venv .venv && .venv/bin/pip install -e .
```

## 7. .env Configured

```bash
cp .env.example .env
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
# Generated key: Q3vejrm7VXmWtbZX9vcLYCTQVJIdfGvTzGpeI3iKW04
sed -i 's/change-me/Q3vejrm7VXmWtbZX9vcLYCTQVJIdfGvTzGpeI3iKW04/' /opt/clay-webhook-os/.env
```

## 8. Systemd Service Created

```bash
cat > /etc/systemd/system/clay-webhook-os.service << 'EOF'
[Unit]
Description=Clay Webhook OS
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/clay-webhook-os
ExecStart=/opt/clay-webhook-os/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
Environment=PATH=/usr/local/bin:/usr/bin:/bin

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload && systemctl enable clay-webhook-os && systemctl start clay-webhook-os
```

Verified: `curl http://localhost:8000/health` → 9 skills loaded, 10 workers

## 9. DNS Record Added

- **Provider:** Namecheap (nomynoms.com)
- **Type:** A Record
- **Host:** clay
- **Value:** 178.156.249.201
- **TTL:** Automatic
- **Result:** clay.nomynoms.com → 178.156.249.201

## 10. Nginx Reverse Proxy

```bash
mkdir -p /etc/nginx/sites-available /etc/nginx/sites-enabled

cat > /etc/nginx/sites-available/clay-webhook-os << 'EOF'
server {
    listen 80;
    server_name clay.nomynoms.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 120s;
    }
}
EOF

ln -s /etc/nginx/sites-available/clay-webhook-os /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
```

## 11. SSL Certificate (Let's Encrypt)

```bash
certbot --nginx -d clay.nomynoms.com
# Email: fermin@thekiln.com
# Certificate deployed to /etc/nginx/sites-enabled/clay-webhook-os
```

## 12. Live Verification (2026-03-05)

```bash
# Health check from internet:
curl https://clay.nomynoms.com/health
# → {"status":"ok","workers_available":10,"skills_loaded":[9 skills]}

# Full webhook test:
curl -X POST https://clay.nomynoms.com/webhook \
  -H "Content-Type: application/json" \
  -H "X-API-Key: Q3vejrm7VXmWtbZX9vcLYCTQVJIdfGvTzGpeI3iKW04" \
  -d '{"skill":"linkedin-note","data":{"first_name":"Sarah","title":"VP Engineering","company_name":"Lattice","signal_type":"funding","signal_detail":"Series D","client_slug":"twelve-labs"},"model":"sonnet"}'
# → Valid JSON response in ~5 seconds
```

## 13. Async Queue Architecture (2026-03-05)

- **Pattern:** POST /webhook with `callback_url` → enqueues job → returns 202 with `job_id` → workers process → POST result to callback_url
- **Workers:** `MAX_WORKERS=3` (down from 10 to avoid OOM on CX22 with Opus)
- **Semaphore:** WorkerPool uses `asyncio.Semaphore` to limit concurrent `claude --print` subprocesses
- **Callback guard:** `_send_callback()` skips when `callback_url` is empty (batch jobs)

## 14. New Endpoints (2026-03-05)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/stats` | Aggregate metrics: processed/completed/failed counts, active workers, queue depth, avg duration, success rate, cache entries |
| POST | `/batch` | Enqueue multiple rows at once: `{skill, rows: [...], model?, instructions?}` → returns `{batch_id, total_rows, job_ids}` |
| GET | `/jobs/{id}` | Now includes `result` field for dashboard display |

**CORS:** Enabled with `allow_origins=["*"]` for dashboard access. Tighten to Vercel domain after deploy.

## 15. Dashboard (2026-03-05)

- **Framework:** Next.js 15, React 19, Tailwind v4, TypeScript
- **Location:** `dashboard/` directory in repo
- **Pages:** Dashboard (stats + jobs), Playground (skill tester), Batch (CSV upload → process → download)
- **Deployment:** Vercel (connect GitHub repo, set root to `dashboard/`)
- **Env vars for Vercel:** `NEXT_PUBLIC_API_URL=https://clay.nomynoms.com`, `NEXT_PUBLIC_API_KEY=<key>`

## Key Info for Future Reference

| Item | Value |
|------|-------|
| Server IP | 178.156.249.201 |
| SSH | `ssh root@178.156.249.201` |
| Domain | clay.nomynoms.com |
| Webhook URL | https://clay.nomynoms.com/webhook |
| API Key | Q3vejrm7VXmWtbZX9vcLYCTQVJIdfGvTzGpeI3iKW04 |
| App path | /opt/clay-webhook-os |
| Service | `systemctl status clay-webhook-os` |
| Logs | `journalctl -u clay-webhook-os -f` |
| Deploy | `cd /opt/clay-webhook-os && git pull && systemctl restart clay-webhook-os` |
| Health check | `curl https://clay.nomynoms.com/health` |

## Clay HTTP Action Setup

- **URL:** `https://clay.nomynoms.com/webhook`
- **Method:** POST
- **Headers:**
  - `Content-Type: application/json`
  - `X-API-Key: Q3vejrm7VXmWtbZX9vcLYCTQVJIdfGvTzGpeI3iKW04`
- **Timeout:** 120000 ms
- **Body:**
```json
{
  "skill": "email-gen",
  "data": {
    "first_name": "/First Name",
    "company_name": "/Company Name",
    "title": "/Title",
    "industry": "/Industry",
    "signal_detail": "/Signal Details",
    "client_slug": "twelve-labs"
  },
  "model": "opus"
}
```
