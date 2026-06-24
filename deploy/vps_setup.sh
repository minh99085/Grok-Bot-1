#!/usr/bin/env bash
# Run on Vultr VPS as root: bash deploy/vps_setup.sh
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

apt-get update -qq
apt-get install -y -qq git python3 python3-pip python3-venv docker.io docker-compose-plugin ufw

systemctl enable docker
systemctl start docker

INSTALL_DIR=/opt/grok-bot-1
if [[ ! -d "$INSTALL_DIR/.git" ]]; then
  git clone https://github.com/minh99085/Grok-Bot-1.git "$INSTALL_DIR"
else
  git -C "$INSTALL_DIR" pull --ff-only origin main
fi
cd "$INSTALL_DIR"

if [[ ! -f .env ]]; then
  cp .env.example .env
  SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")
  sed -i "s/^TRADINGVIEW_WEBHOOK_SECRET=.*/TRADINGVIEW_WEBHOOK_SECRET=${SECRET}/" .env
  sed -i 's/^TRADINGVIEW_HOST=.*/TRADINGVIEW_HOST=0.0.0.0/' .env
  echo ""
  echo "=== ACTION REQUIRED ==="
  echo "Edit $INSTALL_DIR/.env and set:"
  echo "  XAI_API_KEY=..."
  echo "  ANTHROPIC_API_KEY=..."
  echo "Then re-run: bash deploy/vps_setup.sh"
  echo "Webhook path will be: /tv/${SECRET}"
  exit 1
fi

if ! grep -q '^XAI_API_KEY=.\+' .env || ! grep -q '^ANTHROPIC_API_KEY=.\+' .env; then
  echo "ERROR: set XAI_API_KEY and ANTHROPIC_API_KEY in $INSTALL_DIR/.env"
  exit 1
fi

mkdir -p reports/loop_state reports

# TradingView webhook on 8799
ufw allow 22/tcp 2>/dev/null || true
ufw allow 8799/tcp 2>/dev/null || true
ufw allow 8800/tcp 2>/dev/null || true
ufw --force enable 2>/dev/null || true

docker compose build
docker compose up -d grok-bot
docker compose ps

SECRET=$(grep '^TRADINGVIEW_WEBHOOK_SECRET=' .env | cut -d= -f2-)
IP=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
echo ""
echo "Grok-Bot-1 running (paper-only profit discovery)."
echo "Logs: docker compose -f $INSTALL_DIR/docker-compose.yml logs -f grok-bot"
echo "TradingView webhook: http://${IP}:8799/tv/${SECRET}"
DASH_TOKEN=$(grep '^DASHBOARD_TOKEN=' .env | cut -d= -f2-)
if [[ -n "$DASH_TOKEN" ]]; then
  echo "Dashboard: http://${IP}:8800/dash/${DASH_TOKEN}"
else
  echo "Dashboard: http://${IP}:8800/"
fi
echo "Discovery status: docker compose exec grok-bot python -m grok_bot.main --discovery-status"