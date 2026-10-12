#!/bin/bash
set -e
CONF=/etc/postgresql/16/main/postgresql.conf
cp "$CONF" "${CONF}.bak-$(date +%Y%m%d)"
sed -i 's/^shared_buffers = 384MB/shared_buffers = 128MB/' "$CONF"
sed -i 's/^work_mem = 8MB/work_mem = 4MB/' "$CONF"
sed -i 's/^max_connections = 40/max_connections = 30/' "$CONF"
grep -E '^(shared_buffers|work_mem|max_connections)' "$CONF"
systemctl reload postgresql
echo POSTGRES_RELOADED
systemctl disable --now fwupd 2>/dev/null || true
systemctl disable --now fwupd-refresh 2>/dev/null || true
echo '===AFTER==='
free -h | head -2
psql -U postgres -c 'SHOW shared_buffers;' marketflow 2>/dev/null || true
