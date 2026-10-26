#!/bin/bash
# MarketFlow v2: sao lưu PostgreSQL hằng ngày (cron 03:00), giữ 7 bản mới nhất.
# Cài đặt: deploy_v2.sh sao chép file này tới /usr/local/bin/marketflow-backup
set -euo pipefail
DB="${MARKETFLOW_DB:-marketflow_v2}"
TS=$(date +%Y%m%d-%H%M%S)
DIR=/var/backups/marketflow
DEST="$DIR/${DB}-$TS.sql.gz"
mkdir -p "$DIR"
su - postgres -c "pg_dump -d $DB --clean --if-exists --no-owner --no-privileges" | gzip -6 > "$DEST"
# kiểm tra bản sao lưu không rỗng và giải nén được
gzip -t "$DEST"
[ "$(stat -c %s "$DEST")" -gt 1024 ] || { echo "Backup quá nhỏ: $DEST" >&2; exit 1; }
ls -1t "$DIR/${DB}"-*.sql.gz | tail -n +8 | xargs -r rm -f
echo "$(date -Is) OK $DEST $(stat -c %s "$DEST") bytes"
