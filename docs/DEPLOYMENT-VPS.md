# Hướng Dẫn Triển Khai Production — MarketFlow (Ubuntu VPS)

Tài liệu này là **nguồn sự thật duy nhất** về kiến trúc vận hành, cấu hình dịch vụ, quy trình triển khai, sao lưu và xử lý sự cố cho hệ thống **MarketFlow** trên máy chủ CloudCode VPS (Ubuntu 24.04 LTS, 2 vCPU, 2 GiB RAM, 40 GiB NVMe).

---

## 1. Sơ Đồ Kiến Trúc & Cổng Dịch Vụ

```
[ Internet / Người dùng ]
           │
           ▼
[ Cloudflare Edge ] (Tên miền: https://marketing.kienhieu.id.vn/)
           │
           │ (Cloudflare Tunnel: cloudflared-tunnel.service)
           ▼
[ Nginx Reverse Proxy ] (127.0.0.1:8080)
   ├── Phục vụ Frontend SPA tĩnh: /var/www/marketflow
   ├── Chặn truy cập từ ngoài vào /mcp -> HTTP 404
   ├── Proxy /api/v1/assistant/ (SSE streaming: no-buffering, timeout 300s)
   └── Proxy /api/ -> FastAPI Backend (127.0.0.1:8000)
           │
           ▼
[ FastAPI Backend ] (marketflow-api.service — User: marketflow, 127.0.0.1:8000)
   ├── CSDL: PostgreSQL 16 (127.0.0.1:5432, Database: marketflow_v2)
   ├── Streamable-HTTP FastMCP server mount tại /mcp
   └── Gọi AI Runner qua HTTP nội bộ: 127.0.0.1:8100 (Header: X-Runner-Token)
           │
           ▼
[ AI Runner Service ] (marketflow-ai-runner.service — User: mfai, 127.0.0.1:8100)
   ├── Hàng đợi tuần tự (Concurrency = 1, MemoryMax = 896M)
   ├── Khởi tạo tiến trình con: opencode run --agent marketflow
   │     └── Gọi ngược lại MCP Backend (127.0.0.1:8000/mcp/) bằng Bearer run-token
   └── Kết nối ra ngoài tới OpenCode Zen (Model: big-pickle / glm-5.3-flash)
```

### Bảng Danh Mục Dịch Vụ & Cổng

| Dịch vụ | Tên Systemd Service | Cổng / Socket | Tài khoản | Thư mục làm việc | Giới hạn bộ nhớ |
|---|---|---|---|---|---|
| **Nginx** | `nginx.service` | `127.0.0.1:8080` | `www-data` | `/var/www/marketflow` | Hệ thống |
| **Cloudflare Tunnel** | `cloudflared-tunnel.service` | Outbound | `root` | `/etc/cloudflared` | Hệ thống |
| **FastAPI Backend** | `marketflow-api.service` | `127.0.0.1:8000` | `marketflow` | `/opt/marketflow/backend` | `MemoryMax=768M` |
| **AI Runner** | `marketflow-ai-runner.service` | `127.0.0.1:8100` | `mfai` | `/opt/marketflow/ai-runner/sandbox` | `MemoryMax=896M` |
| **PostgreSQL 16** | `postgresql@16-main.service` | `127.0.0.1:5432` | `postgres` | `/var/lib/postgresql/16/main` | ~256M |

---

## 2. Tệp Biến Môi Trường (Environment Files)

### 2.1. Backend FastAPI: `/opt/marketflow/backend/.env`
- Phân quyền bắt buộc: `chmod 600`, sở hữu bởi `marketflow:marketflow`.
- Cấu hình:
```dotenv
APP_NAME=MarketFlow
APP_ENV=production
API_V1_PREFIX=/api/v1
DATABASE_URL=postgresql://marketflow:<MAT_KHAU_HEX>@127.0.0.1:5432/marketflow_v2
JWT_SECRET=<CHUOI_RANDOM_HEX_64_KY_TU>
ACCESS_TOKEN_EXPIRE_MINUTES=480
CORS_ORIGINS=https://marketing.kienhieu.id.vn,http://127.0.0.1:8080
AI_RUNNER_URL=http://127.0.0.1:8100
AI_RUNNER_TOKEN=<RUNNER_TOKEN_TU_RUNNER_ENV>
```

> **Lưu ý**: `settings.validate_for_runtime()` tự động kiểm tra khi khởi động ở `APP_ENV=production`. Nếu `JWT_SECRET` dưới 32 ký tự, dùng SQLite hoặc thiếu `AI_RUNNER_TOKEN`, tiến trình sẽ dừng ngay lập tức.

### 2.2. AI Runner: `/etc/marketflow/ai-runner.env`
- Phân quyền bắt buộc: `chmod 600`, sở hữu bởi `root:root`.
- Cấu hình:
```dotenv
RUNNER_TOKEN=<CHUOI_SECRET_X_RUNNER_TOKEN>
OPENCODE_BIN=/usr/local/bin/opencode
RUNNER_SANDBOX_DIR=/opt/marketflow/ai-runner/sandbox
OPENCODE_AGENT=marketflow
OPENCODE_MODEL=opencode/big-pickle
OPENCODE_FALLBACK_MODELS=opencode/glm-5.3-flash-free,opencode/deepseek-v4.1-flash-free
RUNNER_TIMEOUT_S=120
RUNNER_CONCURRENCY=1
RUNNER_MAX_QUEUE=8
RUNNER_HOST=127.0.0.1
RUNNER_PORT=8100
```

---

## 3. Quy Trình Cài Đặt & Triển Khai (Deployment Procedure)

Script triển khai tự động `deploy/vps/deploy_v2.sh` có tính chất **idempotent**: sao lưu trước khi thay đổi và không ghi đè CSDL v1 (v2 dùng CSDL riêng `marketflow_v2`).

### Các bước thực hiện:

1. **Chuẩn bị bản phát hành (Release Artifacts)**:
   - Build frontend trên máy phát triển hoặc CI:
     ```powershell
     npm --prefix frontend ci
     npm --prefix frontend run build
     ```
   - Đảm bảo mã nguồn `backend/` và thư mục `frontend/dist/` đã sẵn sàng.

2. **Tải lên máy chủ & Chạy script chuyển đổi**:
   ```bash
   # Chạy trực tiếp trên VPS với quyền root (từ thư mục release hoặc git repo):
   sudo bash deploy/vps/deploy_v2.sh
   ```

### Cơ chế hoạt động của `deploy_v2.sh`:
- **Bước 1**: Tạo bản sao lưu đầy đủ `pg_dump` của CSDL cũ sang `/var/backups/marketflow/pre_v2_<ts>.sql.gz`.
- **Bước 2**: Sao lưu toàn bộ thư mục `/opt/marketflow/backend`, `/var/www/marketflow` và `.venv` cũ để sẵn sàng rollback.
- **Bước 3**: Khởi tạo CSDL mới `marketflow_v2` (CSDL cũ `marketflow` được giữ nguyên vẹn 100%).
- **Bước 4**: Khởi tạo Virtualenv Python 3.12 tại `/opt/marketflow/.venv`, cài đặt `requirements.txt`, thiết lập `/opt/marketflow/backend/.env` với JWT Secret ngẫu nhiên an toàn, chạy `alembic upgrade head` và nạp dữ liệu mẫu ban đầu (seed demo chỉ chạy 1 lần duy nhất nhờ cờ `.seed_v2_done`).
- **Bước 5**: Cập nhật systemd unit `marketflow-api.service` và nạp lại daemon.
- **Bước 6**: Triển khai frontend `dist/` vào `/var/www/marketflow` theo cơ chế hoán đổi nguyên tử (atomic directory swap) kèm chuẩn phân quyền `755` cho thư mục và `644` cho tệp.
- **Bước 7**: Cập nhật cấu hình Nginx (hỗ trợ SSE streaming, gzip, brotli và chặn `/mcp`), kiểm tra `nginx -t` trước khi reload.
- **Bước 8**: Khởi động lại service `marketflow-api` và thực hiện 4 bước kiểm thử tự động (smoke checks: `/api/v1/health`, đăng nhập Manager, chặn `/mcp`, tải giao diện SPA).

---

## 4. Quy Trình Sao Lưu & Khôi Phục (Backup & Restore)

### 4.1. Sao lưu tự động hằng ngày
Hệ thống tự động sao lưu CSDL vào **03:00 sáng hằng ngày** thông qua cron job tại `/etc/cron.d/marketflow-backup`:
```cron
0 3 * * * root /usr/local/bin/marketflow-backup >> /var/log/backup.log 2>&1
```
Tệp sao lưu được nén `gzip -6` và lưu trữ tại `/var/backups/marketflow/marketflow-YYYYMMDD-HHMMSS.sql.gz`. Script tự động dọn dẹp và duy trì 7 bản sao lưu gần nhất.

### 4.2. Sao lưu thủ công trước khi bảo trì
```bash
sudo -u postgres pg_dump -d marketflow_v2 --clean --if-exists --no-owner --no-privileges | gzip -6 > /var/backups/marketflow/marketflow_v2_manual_$(date +%Y%m%d_%H%M%S).sql.gz
```

### 4.3. Lệnh khôi phục CSDL đã qua kiểm nghiệm thực tế (Tested Restore Command)
Khi cần khôi phục CSDL từ bản sao lưu:
```bash
# 1. Tạm dừng dịch vụ API để tránh ghi dữ liệu trong lúc khôi phục
sudo systemctl stop marketflow-api

# 2. Khôi phục dữ liệu từ tệp nén vào CSDL marketflow_v2
zcat /var/backups/marketflow/<ten_file_sao_luu>.sql.gz | sudo -u postgres psql -d marketflow_v2

# 3. Khởi động lại dịch vụ API
sudo systemctl start marketflow-api

# 4. Kiểm tra sức khỏe dịch vụ
curl -s http://127.0.0.1:8080/api/v1/health
```

---

## 5. Quy Trình Rollback Về v1 (Emergency Rollback)

Nếu quá trình chuyển đổi gặp sự cố nghiêm trọng, toàn bộ hệ thống có thể quay về phiên bản v1 trong vòng **10 giây** nhờ script rollback tự động:

```bash
sudo bash deploy/vps/rollback_v1.sh
```

### Nguyên lý an toàn:
- CSDL `marketflow` cũ **không bị chỉnh sửa hay xóa bỏ** trong suốt quá trình cài đặt v2.
- Script tự động khôi phục thư mục backend v1, môi trường virtualenv Python 3.11, giao diện frontend v1 và cấu hình systemd/nginx cũ.
- Khởi động lại dịch vụ và xác nhận endpoint `/health` hoạt động bình thường.

---

## 6. Vận Hành, Giám Sát & Nhật Ký Lỗi (Troubleshooting)

### 6.1. Xem log thời gian thực qua `journalctl`
- **Backend FastAPI**:
  ```bash
  journalctl -u marketflow-api -f
  ```
- **AI Runner Service**:
  ```bash
  journalctl -u marketflow-ai-runner -f
  ```
- **Nginx Web Server**:
  ```bash
  journalctl -u nginx -f
  tail -f /var/log/nginx/error.log
  ```
- **Cloudflare Tunnel**:
  ```bash
  journalctl -u cloudflared-tunnel -f
  ```

### 6.2. Kiểm tra nhanh trạng thái toàn bộ dịch vụ
```bash
systemctl status nginx postgresql marketflow-api marketflow-ai-runner cloudflared-tunnel --no-pager
```

### 6.3. Kiểm tra kết nối & Sức khỏe hệ thống
- Kiểm tra endpoint tổng thể (DB + AI Runner):
  ```bash
  curl -s http://127.0.0.1:8080/api/v1/health
  # Kết quả mong đợi: {"status":"ok","db":"ok","ai_runner":"ok"}
  ```
- Kiểm tra AI Runner độc lập:
  ```bash
  curl -s http://127.0.0.1:8100/health
  # Kết quả mong đợi: {"ok":true,"opencode_version":"1.19.4","model":"opencode/big-pickle",...}
  ```

---

## 7. Ghi Chú Đặc Thù Về AI Runner & OpenCode

1. **Bộ nhớ & Mức tiêu thụ RAM**:
   - Tiến trình AI Runner (Uvicorn): ~50 MB RAM RSS.
   - Tiến trình OpenCode CLI khi sinh nội dung và gọi MCP tool: ~490 MB RAM RSS.
   - Giới hạn systemd: `MemoryHigh=768M`, `MemoryMax=896M` bảo vệ VPS 2 GiB khỏi nguy cơ OOM killer.
2. **Giới hạn đồng thời (Concurrency = 1)**:
   - Hệ thống áp dụng hàng đợi tuần tự FIFO với `concurrency = 1`. Tuyệt đối **không tăng concurrency** trên VPS 2 GiB vì 2 tiến trình OpenCode chạy song song sẽ tiêu thụ gần 1 GB RAM, dẫn đến tràn bộ nhớ.
3. **Mô hình miễn phí (OpenCode Zen Free Tier) & Rate Limits**:
   - Mô hình chính được chọn qua thực nghiệm P0 Spike: `opencode/big-pickle` (tuân thủ nguyên tắc đề xuất, tiếng Việt tự nhiên, tỷ lệ gọi MCP tool chính xác 100%).
   - Danh sách dự phòng: `glm-5.3-flash-free`, `deepseek-v4.1-flash-free`.
   - Khi Zen đạt giới hạn tần suất (FreeTierError / 429), AI Runner tự động chuẩn hóa thành mã lỗi `AI_RATE_LIMITED` để hiển thị thông báo thân thiện tới người dùng.
4. **Timeout cứng**:
   - `RUNNER_TIMEOUT_S=120`. Nếu một lượt tương tác kéo dài quá 120 giây (do mạng hoặc chờ model), tiến trình con sẽ bị chấm dứt (`SIGKILL` toàn bộ process group) để giải phóng RAM cho yêu cầu tiếp theo.

---

## 8. Nguyên Tắc Bảo Mật Cốt Lõi (Security Guidelines)

1. **Chặn cổng `/mcp` từ Internet**:
   - Giao thức MCP Streamable-HTTP (`/mcp`) chỉ được dùng nội bộ giữa OpenCode CLI và FastAPI Backend qua `127.0.0.1:8000/mcp`.
   - Nginx cấu hình khối `location ^~ /mcp { return 404; }` đảm bảo người dùng bên ngoài không thể thăm dò hoặc tấn công giao diện công cụ.
2. **Xác thực Run-Token JWT ngắn hạn**:
   - Mọi lượt gọi MCP bắt buộc phải mang Bearer JWT có thời hạn 10 phút, chứa đúng các claim `uid`, `thread_id`, `message_id`. OpenCode không thể giả mạo phiên của người dùng khác.
3. **Tách biệt tài khoản hệ thống (Privilege Separation)**:
   - Backend chạy bằng user `marketflow` (`ProtectHome=true`, không có login shell).
   - AI Runner chạy bằng user riêng biệt `mfai` (`HOME=/var/lib/mfai`).
   - Sandbox của OpenCode bị khóa chặt bằng phân quyền nghiêm ngặt trong `deploy/opencode/agent/marketflow.md`: chặn toàn bộ quyền đọc/ghi file hệ thống (`read`, `glob`, `grep`, `list`, `bash`, `external_directory`), chỉ cho phép các tool nghiệp vụ mang tiền tố `marketflow_*`.
4. **Bảo mật bí mật (Secret Zero-Leakage)**:
   - Không commit bất kỳ secret, mật khẩu PostgreSQL, JWT Secret hay token nào vào Git repository.
