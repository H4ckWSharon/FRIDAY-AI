# FRIDAY AI — Complete Public Deployment Guide (100% Free, Secure & Isolated)

This guide walks you through deploying FRIDAY AI so anyone on the internet can access and use it 24/7.

```mermaid
graph LR
    User["Any Web Browser (Public)"] -->|HTTPS| Frontend["Frontend (Vercel CDN)\nhttps://friday-ai.vercel.app"]
    Frontend -->|HTTPS API Requests| CFTunnel["Cloudflare Tunnel\n(Free HTTPS Gateway)"]
    CFTunnel -->|Localhost Port 8008| Backend["FastAPI Backend (/opt/friday)\n(Isolated Systemd Service)"]
    Backend -->|Localhost Port 11434 (0ms)| Ollama["Ollama Neural Engine\n(Huihui-Qwen3 & BaronLLM)"]
    
    subgraph Ubuntu VPS 213.133.97.141
        Backend
        Ollama
        Jeeni["Jeeni & Other Services\n(100% UNTOUCHED)"]
    end
```

---

## Architecture Highlights
- **Frontend**: Hosted on **Vercel** (Free, instant global CDN, automatic SSL certificate, auto-redeploys on `git push`).
- **Backend (FastAPI)**: Runs directly on the **Ubuntu VPS (`213.133.97.141`)** on isolated port `8008`, right next to Ollama (`127.0.0.1:11434`) for **0ms internal network latency**.
- **Public Tunnel**: **Cloudflare Tunnel (`cloudflared`)** provides a free, encrypted HTTPS URL for the backend without opening VPS firewall ports, without touching Jeeni, and without needing a purchased custom domain.

---

## Step 1: Deploy the Frontend on Vercel (2 Minutes)

1. Open [vercel.com](https://vercel.com) and log in (or sign up with your GitHub account).
2. Click **"Add New..."** -> **"Project"**.
3. Select your GitHub repository: **`H4ckWSharon/FRIDAY-AI`**.
4. In the configuration screen:
   - **Framework Preset**: `Other` (or static HTML)
   - **Root Directory**: `./` (leave default)
   - **Build & Output Settings**: Leave default
5. Click **"Deploy"**.
6. Within 30 seconds, Vercel gives you your live public website URL:  
   👉 `https://friday-ai-<yourname>.vercel.app`

---

## Step 2: Deploy the Backend on the VPS (Strict Jeeni Isolation)

SSH into your Ubuntu VPS:
```bash
ssh root@213.133.97.141
```

Run the automated, isolated deployment script:
```bash
curl -fsSL https://raw.githubusercontent.com/H4ckWSharon/FRIDAY-AI/main/deploy_vps.sh | bash
```

### What this script does automatically:
1. Verifies that port `8008` is free and does not interfere with Jeeni.
2. Clones FRIDAY into an isolated directory: `/opt/friday`.
3. Sets up a dedicated Python virtual environment.
4. Generates `.env` configured to use local Ollama (`http://127.0.0.1:11434`).
5. Creates and starts the systemd background service `friday.service`.
6. Validates the `/health` endpoint.

---

## Step 3: Expose the Backend with a Free Cloudflare HTTPS URL

On your VPS, install `cloudflared` (official Cloudflare client):
```bash
# 1. Download official Cloudflare package
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
dpkg -i cloudflared.deb

# 2. Start free quick tunnel to FRIDAY backend (Port 8008)
cloudflared tunnel --url http://127.0.0.1:8008
```

You will see output similar to:
```
+--------------------------------------------------------------------------------------------+
|  Your quick Tunnel has been created! Visit it at:                                          |
|  https://friday-intel-gateway.trycloudflare.com                                            |
+--------------------------------------------------------------------------------------------+
```

*(Optional: To run Cloudflare tunnel permanently in the background as a systemd service, see the Persistent Tunnel section below).*

---

## Step 4: Connect Frontend to Backend

Now simply open your Vercel URL in any browser with the `backend` parameter:
```
https://friday-ai-<yourname>.vercel.app/?backend=https://friday-intel-gateway.trycloudflare.com
```

FRIDAY will automatically connect, save the backend endpoint in your browser, and begin serving chat requests to everyone worldwide!

---

## Step 5: (Optional) Make Cloudflare Tunnel Persistent 24/7

To keep the Cloudflare tunnel running 24/7 on the VPS even after you close your terminal:

```bash
# Create background service for Cloudflare Tunnel
cat <<EOF > /etc/systemd/system/friday-tunnel.service
[Unit]
Description=Cloudflare Tunnel for FRIDAY AI
After=network.target friday.service

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/cloudflared tunnel --url http://127.0.0.1:8008
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now friday-tunnel.service
```

To view your persistent tunnel URL at any time:
```bash
journalctl -u friday-tunnel.service -n 25 | grep "trycloudflare.com"
```

---

## Useful Operational Commands

| Action | Command |
|:---|:---|
| Check FRIDAY Status | `systemctl status friday.service` |
| View Live Logs | `journalctl -u friday.service -f` |
| Restart FRIDAY | `systemctl restart friday.service` |
| Health Check | `curl http://127.0.0.1:8008/health` |
| Verify Jeeni Isolation | `ss -tlpn` (confirms FRIDAY is only on 8008) |
