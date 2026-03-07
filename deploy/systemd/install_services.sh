#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./deploy/systemd/install_services.sh /absolute/path/to/repo [service_user]
#
# Example:
#   ./deploy/systemd/install_services.sh /opt/ai_trading_bot beau

WORKDIR="${1:-}"
SERVICE_USER="${2:-$(id -un)}"
TARGET_DIR="/etc/systemd/system"

if [[ -z "$WORKDIR" ]]; then
  echo "ERROR: missing repo path."
  echo "Usage: $0 /absolute/path/to/repo [service_user]"
  exit 1
fi

if [[ "$WORKDIR" != /* ]]; then
  echo "ERROR: use an absolute path for WORKDIR."
  exit 1
fi

if [[ ! -d "$WORKDIR" ]]; then
  echo "ERROR: directory not found: $WORKDIR"
  exit 1
fi

if [[ ! -f "$WORKDIR/tradingbot.py" || ! -f "$WORKDIR/monitor_app.py" ]]; then
  echo "ERROR: expected tradingbot.py and monitor_app.py in $WORKDIR"
  exit 1
fi

if [[ ! -x "$WORKDIR/.venv/bin/python" ]]; then
  echo "ERROR: expected python at $WORKDIR/.venv/bin/python"
  echo "Create venv in repo root as '.venv' or edit unit files manually."
  exit 1
fi

if [[ ! -x "$WORKDIR/.venv/bin/gunicorn" ]]; then
  echo "ERROR: expected gunicorn at $WORKDIR/.venv/bin/gunicorn"
  echo "Install it with: $WORKDIR/.venv/bin/pip install gunicorn"
  exit 1
fi

if [[ ! -f "$WORKDIR/.env" ]]; then
  echo "WARNING: $WORKDIR/.env not found."
  echo "Service will still install, but you should create .env before start."
fi

TMP_TRADING="$(mktemp)"
TMP_MONITOR="$(mktemp)"

sed \
  -e "s|REPLACE_USER|$SERVICE_USER|g" \
  -e "s|REPLACE_WORKDIR|$WORKDIR|g" \
  "$WORKDIR/deploy/systemd/tradingbot.service" > "$TMP_TRADING"

sed \
  -e "s|REPLACE_USER|$SERVICE_USER|g" \
  -e "s|REPLACE_WORKDIR|$WORKDIR|g" \
  "$WORKDIR/deploy/systemd/monitor.service" > "$TMP_MONITOR"

sudo cp "$TMP_TRADING" "$TARGET_DIR/tradingbot.service"
sudo cp "$TMP_MONITOR" "$TARGET_DIR/monitor.service"
rm -f "$TMP_TRADING" "$TMP_MONITOR"

sudo systemctl daemon-reload
sudo systemctl enable tradingbot.service monitor.service
sudo systemctl restart tradingbot.service monitor.service

echo "Installed and started:"
echo "  - tradingbot.service"
echo "  - monitor.service"
echo
echo "Check status:"
echo "  systemctl status tradingbot.service --no-pager"
echo "  systemctl status monitor.service --no-pager"
echo
echo "Tail logs:"
echo "  journalctl -u tradingbot.service -f"
echo "  journalctl -u monitor.service -f"
