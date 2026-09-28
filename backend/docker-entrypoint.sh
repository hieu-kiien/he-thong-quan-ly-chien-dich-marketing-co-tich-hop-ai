#!/bin/sh
# Entrypoint chạy non-root nhưng vẫn tạo được file DB trong volume được mount.
#
# VÌ SAO CẦN FILE NÀY:
# Container chạy với user `appuser` (uid hệ thống, thường ~999). Khi host bind-mount
# ./backend/data vào /app/data, quyền sở hữu thư mục là của user trên HOST (root:root 0755
# nếu Docker phải tự tạo). appuser vì thế KHÔNG tạo được marketing_campaigns.db và app
# chết với PermissionError. Trên Windows/macOS (Docker Desktop) quyền permissive nên
# che giấu lỗi này cho tới khi deploy lên Linux.
#
# Cách đúng chuẩn (giống image postgres/redis): khởi động với quyền root chỉ để chuẩn hoá
# quyền sở hữu thư mục dữ liệu, sau đó drop xuống user không phải quyền root.
#
# Dùng `runuser` (util-linux) chứ không dùng `su`: `su` cần PAM và làm hỏng argv khi
# truyền nhiều tham số -- `uvicorn app.main:app` bị hiểu thành một lệnh duy nhất và
# container restart với exit 127.
set -eu

DATA_DIR="${MARKETFLOW_DATA_DIR:-/app/data}"
APP_USER="${MARKETFLOW_APP_USER:-appuser}"
APP_GROUP="${MARKETFLOW_APP_GROUP:-appgroup}"

mkdir -p "$DATA_DIR"

if [ "$(id -u)" = "0" ]; then
    chown -R "$APP_USER:$APP_GROUP" "$DATA_DIR" 2>/dev/null || \
        echo "[entrypoint] Khong chown duoc $DATA_DIR (bo qua)" >&2
    exec runuser -u "$APP_USER" -- "$@"
fi

echo "[entrypoint] Chay voi uid $(id -u) (khong phai root) - bo qua chown" >&2
exec "$@"
