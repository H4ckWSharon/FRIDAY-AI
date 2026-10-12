#!/usr/bin/env bash
# ==============================================================================
# FRIDAY AI — Safe Production VPS Deployment Script
# ------------------------------------------------------------------------------
# Strictly Isolated Deployment:
# - Target directory: /opt/friday
# - Target port: 8008 (customizable via FRIDAY_PORT)
# - Target Ollama endpoint: http://127.0.0.1:11434 (local to VPS)
# - GUARANTEE: Does NOT touch Jeeni, ports 80/443, docker, or any existing services.
# ==============================================================================

set -euo pipefail

FRIDAY_DIR="/opt/friday"
FRIDAY_PORT="${FRIDAY_PORT:-8008}"
REPO_URL="https://github.com/H4ckWSharon/FRIDAY-AI.git"

echo "=========================================================="
echo "  FRIDAY AI — Safe Isolated Deployment on Ubuntu VPS"
echo "=========================================================="

# 1. Check Root Privileges
if [ "$EUID" -ne 0 ]; then
  echo "[ERROR] Please run this script as root or with sudo:"
  echo "  sudo bash deploy_vps.sh"
  exit 1
fi

# 2. Check Port Safety (Strict Jeeni Isolation)
echo "[1/7] Checking port availability for FRIDAY ($FRIDAY_PORT)..."
if ss -tlpn | grep -q ":$FRIDAY_PORT "; then
  echo "[WARNING] Port $FRIDAY_PORT is already in use by another process:"
  ss -tlpn | grep ":$FRIDAY_PORT "
  echo "Please specify a different port: FRIDAY_PORT=8009 sudo bash deploy_vps.sh"
  exit 1
fi
echo "  -> Port $FRIDAY_PORT is free. No conflict with existing services."

# 3. Check Local Ollama Engine
echo "[2/7] Verifying local Ollama neural engine on 127.0.0.1:11434..."
if curl -s http://127.0.0.1:11434/api/tags > /dev/null; then
  echo "  -> Ollama is running locally and reachable!"
else
  echo "[WARNING] Ollama is not responding on http://127.0.0.1:11434."
  echo "Make sure Ollama service is active: systemctl status ollama"
fi

# 4. Clone or Update Repository
echo "[3/7] Setting up FRIDAY files in $FRIDAY_DIR..."
if [ -d "$FRIDAY_DIR/.git" ]; then
  echo "  -> Repository exists. Pulling latest updates from main..."
  cd "$FRIDAY_DIR"
  git fetch origin main
  git reset --hard origin/main
else
  echo "  -> Cloning repository into $FRIDAY_DIR..."
  mkdir -p "$FRIDAY_DIR"
  git clone "$REPO_URL" "$FRIDAY_DIR"
  cd "$FRIDAY_DIR"
fi

# 5. Set Up Python Virtual Environment
echo "[4/7] Setting up Python virtual environment..."
apt-get update -qq && apt-get install -y -qq python3 python3-venv python3-pip curl

if [ ! -d "$FRIDAY_DIR/backend/.venv" ]; then
  python3 -m venv "$FRIDAY_DIR/backend/.venv"
fi

"$FRIDAY_DIR/backend/.venv/bin/pip" install --upgrade pip -q
"$FRIDAY_DIR/backend/.venv/bin/pip" install -r "$FRIDAY_DIR/backend/requirements.txt" -q
echo "  -> Python dependencies installed successfully."

# 6. Configure Environment File (.env)
echo "[5/7] Configuring environment variables in $FRIDAY_DIR/backend/.env..."
if [ ! -f "$FRIDAY_DIR/backend/.env" ]; then
  cp "$FRIDAY_DIR/backend/.env.example" "$FRIDAY_DIR/backend/.env"
  # Set production defaults for VPS
  sed -i "s|OLLAMA_BASE_URL=.*|OLLAMA_BASE_URL=http://127.0.0.1:11434|g" "$FRIDAY_DIR/backend/.env"
  sed -i "s|BACKEND_PORT=.*|BACKEND_PORT=$FRIDAY_PORT|g" "$FRIDAY_DIR/backend/.env"
  sed -i "s|BACKEND_HOST=.*|BACKEND_HOST=127.0.0.1|g" "$FRIDAY_DIR/backend/.env"
  sed -i "s|APP_ENV=.*|APP_ENV=production|g" "$FRIDAY_DIR/backend/.env"
  echo "  -> Created new .env file with VPS localhost Ollama binding."
else
  echo "  -> Existing .env preserved."
fi

# 7. Create & Start Isolated Systemd Service
echo "[6/7] Creating systemd service: friday.service..."
cat <<EOF > /etc/systemd/system/friday.service
[Unit]
Description=FRIDAY AI Backend Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$FRIDAY_DIR/backend
ExecStart=$FRIDAY_DIR/backend/.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port $FRIDAY_PORT --workers 1 --proxy-headers
Restart=always
RestartSec=5
EnvironmentFile=$FRIDAY_DIR/backend/.env

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable friday.service
systemctl restart friday.service
echo "  -> friday.service started and enabled on boot."

# 8. Verify Local Health
echo "[7/7] Testing FRIDAY health check..."
sleep 2
if curl -s "http://127.0.0.1:$FRIDAY_PORT/health" | grep -q '"status":"ok"'; then
  echo "  -> [SUCCESS] FRIDAY backend is healthy and running on 127.0.0.1:$FRIDAY_PORT!"
else
  echo "[WARNING] Health check did not return status:ok. Check logs with:"
  echo "  journalctl -u friday.service -n 50"
fi

echo ""
echo "=========================================================="
echo "  FRIDAY Deployment Complete!"
echo "=========================================================="
echo "To expose FRIDAY publicly with a FREE HTTPS URL without"
echo "touching any existing VPS reverse proxy or Jeeni configs,"
echo "run Cloudflare Quick Tunnel:"
echo ""
echo "  curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb"
echo "  dpkg -i cloudflared.deb"
echo "  cloudflared tunnel --url http://127.0.0.1:$FRIDAY_PORT"
echo ""
echo "This will instantly output a public HTTPS link (e.g. https://xxx.trycloudflare.com)"
echo "which you can connect to your frontend on Vercel!"
echo "=========================================================="
