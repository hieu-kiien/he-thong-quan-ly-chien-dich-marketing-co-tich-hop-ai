#!/usr/bin/env bash
# ==============================================================================
# MarketFlow v2 — Production Deployment Script (VPS)
# Idempotent cutover script for MarketFlow v2 (FastAPI + React SPA + OpenCode)
#
# Usage (run as root on VPS):
#   bash deploy/vps/deploy_v2.sh [RELEASE_ROOT]
# ==============================================================================

set -euo pipefail

# 0. Check root permissions
if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR: Script nay phai duoc chay bang quyen root." >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_ROOT="${1:-$(cd "$SCRIPT_DIR/../.." && pwd)}"

# Resolve source directories
SRC_BACKEND="$SOURCE_ROOT/backend"
if [ ! -d "$SRC_BACKEND" ]; then
    echo "ERROR: Khong tim thay thu muc backend tai $SRC_BACKEND" >&2
    exit 1
fi

if [ -d "$SOURCE_ROOT/frontend/dist" ]; then
    SRC_FRONTEND_DIST="$SOURCE_ROOT/frontend/dist"
elif [ -d "$SOURCE_ROOT/dist" ]; then
    SRC_FRONTEND_DIST="$SOURCE_ROOT/dist"
else
    echo "ERROR: Khong tim thay thu muc frontend dist tai $SOURCE_ROOT/frontend/dist hoac $SOURCE_ROOT/dist" >&2
    exit 1
fi

TS=$(date +%Y%m%d_%H%M%S)
echo "=== BAT DAU TRIEN KHAI MARKETFLOW V2 [$TS] ==="
echo "Source root: $SOURCE_ROOT"
echo "Backend src: $SRC_BACKEND"
echo "Frontend dist src: $SRC_FRONTEND_DIST"

# ------------------------------------------------------------------------------
# 1. Backup CSDL va thu muc hien tai (v1)
# ------------------------------------------------------------------------------
echo "==> [1/8] Sao luu CSDL hien tai sang /var/backups/marketflow/..."
BACKUP_DIR="/var/backups/marketflow"
mkdir -p "$BACKUP_DIR"

if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw marketflow; then
    PRE_V2_BACKUP="${BACKUP_DIR}/pre_v2_${TS}.sql.gz"
    sudo -u postgres pg_dump -d marketflow --clean --if-exists --no-owner --no-privileges | gzip -6 > "$PRE_V2_BACKUP"
    echo "    Da sao luu DB marketflow -> $PRE_V2_BACKUP ($(stat -c%s "$PRE_V2_BACKUP") bytes)"
else
    echo "    CSDL marketflow chua ton tai, bo qua pg_dump"
fi

echo "==> [2/8] Sao luu thu muc backend, frontend, venv hien tai cho rollback..."
if [ -d "/opt/marketflow/backend" ] && [ ! -d "/opt/marketflow/backend.v1.bak" ]; then
    cp -a /opt/marketflow/backend /opt/marketflow/backend.v1.bak
    echo "    Da sao luu /opt/marketflow/backend -> /opt/marketflow/backend.v1.bak"
fi

if [ -d "/var/www/marketflow" ] && [ ! -d "/var/www/marketflow.v1.bak" ]; then
    cp -a /var/www/marketflow /var/www/marketflow.v1.bak
    echo "    Da sao luu /var/www/marketflow -> /var/www/marketflow.v1.bak"
fi

if [ -d "/opt/marketflow/.venv" ] && [ ! -d "/opt/marketflow/.venv.v1.bak" ]; then
    if /opt/marketflow/.venv/bin/python --version 2>&1 | grep -q "3.11"; then
        cp -a /opt/marketflow/.venv /opt/marketflow/.venv.v1.bak
        echo "    Da sao luu Python 3.11 venv -> /opt/marketflow/.venv.v1.bak"
    fi
fi

if [ -f "/etc/systemd/system/marketflow-api.service" ] && [ ! -f "/etc/systemd/system/marketflow-api.service.v1.bak" ]; then
    cp -a /etc/systemd/system/marketflow-api.service /etc/systemd/system/marketflow-api.service.v1.bak
fi

if [ -f "/etc/nginx/sites-available/marketflow" ] && [ ! -f "/etc/nginx/sites-available/marketflow.v1.bak" ]; then
    cp -a /etc/nginx/sites-available/marketflow /etc/nginx/sites-available/marketflow.v1.bak
fi

# ------------------------------------------------------------------------------
# 2. Tao Database marketflow_v2 moi
# ------------------------------------------------------------------------------
echo "==> [3/8] Khoi tao CSDL marketflow_v2 moi (giu nguyen DB marketflow cu de rollback)..."
if ! sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw marketflow_v2; then
    sudo -u postgres createdb -O marketflow marketflow_v2
    echo "    Da tao database marketflow_v2 (owner: marketflow)"
else
    echo "    Database marketflow_v2 da ton tai, tiep tuc su dung"
fi

# ------------------------------------------------------------------------------
# 3. Cai dat Backend v2 & Virtualenv Python 3.12
# ------------------------------------------------------------------------------
echo "==> [4/8] Cai dat Backend v2 va moi truong Python 3.12..."
if [ ! -x "/usr/bin/python3.12" ]; then
    echo "ERROR: /usr/bin/python3.12 khong ton tai tren VPS!" >&2
    exit 1
fi

NEED_VENV=0
if [ ! -x "/opt/marketflow/.venv/bin/python" ]; then
    NEED_VENV=1
elif ! /opt/marketflow/.venv/bin/python --version 2>&1 | grep -q "3.12"; then
    NEED_VENV=1
fi

if [ "$NEED_VENV" -eq 1 ]; then
    echo "    Tao venv moi voi Python 3.12 tai /opt/marketflow/.venv..."
    rm -rf /opt/marketflow/.venv
    /usr/bin/python3.12 -m venv /opt/marketflow/.venv
fi

# Dong bo code backend sang /opt/marketflow/backend
mkdir -p /opt/marketflow/backend
SRC_B_REAL="$(cd "$SRC_BACKEND" && pwd)"
DST_B_REAL="$(cd "/opt/marketflow/backend" && pwd)"
if [ "$SRC_B_REAL" != "$DST_B_REAL" ]; then
    echo "    Dong bo ma nguon backend tu $SRC_BACKEND vao /opt/marketflow/backend..."
    find /opt/marketflow/backend -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
    rsync -a --delete \
        --exclude '.env' \
        --exclude '.seed_v2_done' \
        "$SRC_BACKEND/" /opt/marketflow/backend/
fi

echo "    Cai dat cac goi thu vien Python vao /opt/marketflow/.venv..."
/opt/marketflow/.venv/bin/pip install --quiet --upgrade pip
/opt/marketflow/.venv/bin/pip install --quiet -r /opt/marketflow/backend/requirements.txt

# Cau hinh .env cho v2
echo "    Thiet lap file /opt/marketflow/backend/.env..."
AI_RUNNER_ENV="/etc/marketflow/ai-runner.env"
if [ ! -f "$AI_RUNNER_ENV" ]; then
    echo "ERROR: Khong tim thay file cau hinh runner tai $AI_RUNNER_ENV" >&2
    exit 1
fi

AI_TOKEN=$(grep -E '^(RUNNER_TOKEN|AI_RUNNER_TOKEN)=' "$AI_RUNNER_ENV" | head -1 | cut -d= -f2- | tr -d '"'\'' \r')
if [ -z "$AI_TOKEN" ]; then
    echo "ERROR: RUNNER_TOKEN trong $AI_RUNNER_ENV bi rong!" >&2
    exit 1
fi

# Lay mat khau role marketflow tu .env cu
DB_PASS=""
for env_candidate in /opt/marketflow/backend.v1.bak/.env /opt/marketflow/backend/.env; do
    if [ -f "$env_candidate" ]; then
        OLD_URL=$(grep '^DATABASE_URL=' "$env_candidate" | cut -d= -f2- | tr -d '"'\'' \r')
        EXTRACTED=$(echo "$OLD_URL" | sed -nE 's/.*:\/\/marketflow:([^@]+)@.*/\1/p')
        if [ -n "$EXTRACTED" ]; then
            DB_PASS="$EXTRACTED"
            break
        fi
    fi
done

if [ -z "$DB_PASS" ]; then
    echo "ERROR: Khong the trich xuat mat khau PostgreSQL cua user marketflow tu .env cu!" >&2
    exit 1
fi

# Tao JWT_SECRET duy nhat va bao toan neu da tao truoc do
EXISTING_JWT=""
if [ -f "/opt/marketflow/backend/.env" ]; then
    EXISTING_JWT=$(grep '^JWT_SECRET=' /opt/marketflow/backend/.env 2>/dev/null | cut -d= -f2- | tr -d '"'\'' \r' || true)
fi

if [ -n "$EXISTING_JWT" ] && [ "${#EXISTING_JWT}" -ge 32 ] && [ "$EXISTING_JWT" != "dev-only-insecure-secret-change-me" ]; then
    JWT_SECRET="$EXISTING_JWT"
else
    JWT_SECRET=$(openssl rand -hex 32)
fi

cat <<EOF > /opt/marketflow/backend/.env
APP_NAME=MarketFlow
APP_ENV=production
API_V1_PREFIX=/api/v1
DATABASE_URL=postgresql://marketflow:${DB_PASS}@127.0.0.1:5432/marketflow_v2
JWT_SECRET=${JWT_SECRET}
ACCESS_TOKEN_EXPIRE_MINUTES=480
CORS_ORIGINS=https://marketing.kienhieu.id.vn,http://127.0.0.1:8080
AI_RUNNER_URL=http://127.0.0.1:8100
AI_RUNNER_TOKEN=${AI_TOKEN}
EOF

chmod 600 /opt/marketflow/backend/.env
chown -R marketflow:marketflow /opt/marketflow/backend /opt/marketflow/.venv

# Migration Alembic
echo "    Chay Alembic migration tren marketflow_v2..."
sudo -u marketflow bash -c "cd /opt/marketflow/backend && /opt/marketflow/.venv/bin/alembic upgrade head"

# Seed demo chi chay lan dau
SEED_FLAG="/opt/marketflow/backend/.seed_v2_done"
if [ ! -f "$SEED_FLAG" ]; then
    echo "    Lan dau cai dat v2: nap du lieu mau (seed demo)..."
    sudo -u marketflow bash -c "cd /opt/marketflow/backend && /opt/marketflow/.venv/bin/python seed/seed_demo.py --force"
    touch "$SEED_FLAG"
    chown marketflow:marketflow "$SEED_FLAG"
    echo "    Da nap du lieu mau thanh cong!"
else
    echo "    Flag $SEED_FLAG da ton tai -> bo qua seed de tranh ghi de du lieu."
fi

# ------------------------------------------------------------------------------
# 4. Cap nhat Systemd Service
# ------------------------------------------------------------------------------
echo "==> [5/8] Cap nhat cau hinh marketflow-api.service..."
cp "${SOURCE_ROOT}/deploy/vps/marketflow-api.service" /etc/systemd/system/marketflow-api.service
systemctl daemon-reload
# Sao luu hang ngay phai tro vao CSDL v2 (cron /etc/cron.d/marketflow-backup goi script nay)
install -m 755 "${SOURCE_ROOT}/deploy/vps/marketflow-backup.sh" /usr/local/bin/marketflow-backup

# ------------------------------------------------------------------------------
# 5. Trien khai Frontend Atomic
# ------------------------------------------------------------------------------
echo "==> [6/8] Trien khai frontend dist/ vao /var/www/marketflow (atomic swap)..."
STAGE_DIR="/var/www/marketflow_stage_${TS}"
rm -rf "$STAGE_DIR"
mkdir -p "$STAGE_DIR"
cp -a "$SRC_FRONTEND_DIST/." "$STAGE_DIR/"

chown -R www-data:www-data "$STAGE_DIR"
find "$STAGE_DIR" -type d -exec chmod 755 {} +
find "$STAGE_DIR" -type f -exec chmod 644 {} +

if [ -d "/var/www/marketflow" ]; then
    mv /var/www/marketflow "/var/www/marketflow_prev_${TS}"
fi
mv "$STAGE_DIR" /var/www/marketflow
rm -rf "/var/www/marketflow_prev_${TS}"
echo "    Frontend dist da duoc cap nhat vao /var/www/marketflow"

# ------------------------------------------------------------------------------
# 6. Cap nhat Nginx
# ------------------------------------------------------------------------------
echo "==> [7/8] Cap nhat cau hinh Nginx..."
cp "${SOURCE_ROOT}/deploy/vps/nginx-marketflow.conf" /etc/nginx/sites-available/marketflow
nginx -t
systemctl reload nginx

# ------------------------------------------------------------------------------
# 7. Cap nhat Runner Sandbox & Khoi dong lai Services
# ------------------------------------------------------------------------------
echo "==> [8/8] Cap nhat Runner Sandbox, khoi dong lai services va smoke checks..."

# Cap nhat runner sandbox neu co file opencode trong release
if [ -f "$SOURCE_ROOT/deploy/opencode/agent/marketflow.md" ]; then
    echo "    Cap nhat runner sandbox agent va opencode.json..."
    mkdir -p /opt/marketflow/ai-runner/sandbox/.opencode/agent
    cp "$SOURCE_ROOT/deploy/opencode/agent/marketflow.md" /opt/marketflow/ai-runner/sandbox/.opencode/agent/marketflow.md
    cp "$SOURCE_ROOT/deploy/opencode/opencode.json" /opt/marketflow/ai-runner/sandbox/opencode.json
    chmod -R a+rX /opt/marketflow/ai-runner/sandbox
    chown -R root:root /opt/marketflow/ai-runner/sandbox/opencode.json
    chown -R root:root /opt/marketflow/ai-runner/sandbox/.opencode/agent/marketflow.md
    systemctl restart marketflow-ai-runner
    sleep 2
    if ! systemctl is-active --quiet marketflow-ai-runner; then
        echo "ERROR: marketflow-ai-runner khong khoi dong duoc!" >&2
        journalctl -u marketflow-ai-runner -n 30 --no-pager
        exit 1
    fi
    echo "    marketflow-ai-runner da duoc khoi dong lai voi sandbox moi."
fi

systemctl restart marketflow-api
sleep 6

if ! systemctl is-active --quiet marketflow-api; then
    echo "ERROR: marketflow-api service khong chay duoc sau khi restart!" >&2
    journalctl -u marketflow-api -n 40 --no-pager
    exit 1
fi

echo "    [Smoke 1] Kiem tra GET /api/v1/health qua Nginx..."
HEALTH_RESP=$(curl -s http://127.0.0.1:8080/api/v1/health || true)
echo "    Phan hoi health: $HEALTH_RESP"
if ! echo "$HEALTH_RESP" | grep -q '"status":"ok"'; then
    echo "ERROR: Health check that bai hoac bi degraded!" >&2
    exit 1
fi

echo "    [Smoke 2] Kiem tra dang nhap manager@marketflow.vn..."
LOGIN_RESP=$(curl -s -X POST http://127.0.0.1:8080/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"manager@marketflow.vn","password":"Manager@123"}' || true)
if echo "$LOGIN_RESP" | grep -q '"access_token"'; then
    echo "    Dang nhap Manager thanh cong!"
else
    echo "ERROR: Dang nhap that bai! Phan hoi: $LOGIN_RESP" >&2
    exit 1
fi

echo "    [Smoke 3] Kiem tra Nginx chan truy cap ngoai vao /mcp..."
MCP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8080/mcp || true)
if [ "$MCP_CODE" -eq 404 ]; then
    echo "    Chinh xac: Nginx chan /mcp voi ma 404."
else
    echo "WARNING: /mcp tra ve HTTP $MCP_CODE (mong doi 404)"
fi

echo "    [Smoke 4] Kiem tra Frontend index.html..."
SPA_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8080/ || true)
if [ "$SPA_CODE" -eq 200 ]; then
    echo "    Frontend SPA san sang (HTTP 200)."
else
    echo "ERROR: Frontend tra ve HTTP $SPA_CODE!" >&2
    exit 1
fi

echo ""
echo "=========================================================================="
echo " TRIEN KHAI MARKETFLOW V2 HOAN TAT VA HOAT DONG TOAN DIEN!"
echo " URL: https://marketing.kienhieu.id.vn/"
echo "=========================================================================="
echo "Lenh rollback tuc thi ve v1 neu can:"
echo "  sudo bash ${SOURCE_ROOT}/deploy/vps/rollback_v1.sh"
echo "=========================================================================="
