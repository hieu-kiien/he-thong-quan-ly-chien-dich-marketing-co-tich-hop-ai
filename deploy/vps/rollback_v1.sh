#!/usr/bin/env bash
# ==============================================================================
# MarketFlow — Rollback to v1 Script (VPS)
# Restores previous v1 backend, frontend, systemd unit, and nginx config.
#
# Usage (run as root on VPS):
#   sudo bash deploy/vps/rollback_v1.sh
# ==============================================================================

set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR: Script nay phai duoc chay bang quyen root." >&2
    exit 1
fi

echo "=== BAT DAU ROLLBACK VE MARKETFLOW V1 ==="

# 1. Kiem tra ban sao luu v1
if [ ! -d "/opt/marketflow/backend.v1.bak" ]; then
    echo "ERROR: Khong tim thay ban sao luu /opt/marketflow/backend.v1.bak!" >&2
    exit 1
fi

if [ ! -d "/var/www/marketflow.v1.bak" ]; then
    echo "ERROR: Khong tim thay ban sao luu /var/www/marketflow.v1.bak!" >&2
    exit 1
fi

echo "==> [1/5] Dung service marketflow-api..."
systemctl stop marketflow-api || true

echo "==> [2/5] Khoi phuc thu muc backend & frontend..."
# Khoi phuc backend
rm -rf /opt/marketflow/backend
cp -a /opt/marketflow/backend.v1.bak /opt/marketflow/backend

# Khoi phuc venv neu co ban luu python 3.11
if [ -d "/opt/marketflow/.venv.v1.bak" ]; then
    rm -rf /opt/marketflow/.venv
    cp -a /opt/marketflow/.venv.v1.bak /opt/marketflow/.venv
    echo "    Da khoi phuc .venv v1"
fi

# Khoi phuc frontend
rm -rf /var/www/marketflow
cp -a /var/www/marketflow.v1.bak /var/www/marketflow

# Phan quyen lai
chown -R marketflow:marketflow /opt/marketflow/backend /opt/marketflow/.venv
chown -R www-data:www-data /var/www/marketflow
find /var/www/marketflow -type d -exec chmod 755 {} +
find /var/www/marketflow -type f -exec chmod 644 {} +

echo "==> [3/5] Khoi phuc systemd unit & Nginx config..."
if [ -f "/etc/systemd/system/marketflow-api.service.v1.bak" ]; then
    cp -a /etc/systemd/system/marketflow-api.service.v1.bak /etc/systemd/system/marketflow-api.service
fi

if [ -f "/etc/nginx/sites-available/marketflow.v1.bak" ]; then
    cp -a /etc/nginx/sites-available/marketflow.v1.bak /etc/nginx/sites-available/marketflow
fi

systemctl daemon-reload
nginx -t
systemctl reload nginx

echo "==> [4/5] Khoi dong lai marketflow-api v1..."
systemctl start marketflow-api
sleep 3

if ! systemctl is-active --quiet marketflow-api; then
    echo "ERROR: Service marketflow-api khong khoi dong duoc sau khi rollback!" >&2
    journalctl -u marketflow-api -n 40 --no-pager
    exit 1
fi

echo "==> [5/5] Kiem tra smoke test v1..."
HEALTH_RESP=$(curl -s http://127.0.0.1:8080/health || curl -s http://127.0.0.1:8080/api/v1/health || true)
echo "    Phan hoi health: $HEALTH_RESP"

echo ""
echo "=========================================================================="
echo " ROLLBACK VE MARKETFLOW V1 THANH CONG!"
echo " CSDL 'marketflow' goc duoc giu nguyen ven toan bo du lieu cu."
echo "=========================================================================="
