---
name: deploy-verify
description: Quy trình triển khai MarketFlow lên VPS kèm bước kiểm chứng bắt buộc. Use when deploying to the VPS, pulling new code to /opt/marketflow, restarting services, rotating config, or after any change to nginx/systemd on the production server. Triggers on "deploy", "triển khai", "push lên VPS", "restart", "cập nhật server", "production".
---

# Triển khai lên VPS kèm kiểm chứng

Máy chủ: `vn-hn.cloudcode.io.vn:30513`, key `~/.ssh/marketflow_vps_ed25519`.
Ứng dụng chạy bằng user `marketflow`, KHÔNG chạy root (trừ cloudflared).

```bash
ssh -i ~/.ssh/marketflow_vps_ed25519 -p 30513 root@vn-hn.cloudcode.io.vn
```

## Trình tự

### 1. Trước khi chạm vào server

- Test đã xanh **trên máy local**: `cd backend && python -m pytest -q`
- Đã commit và push. Không deploy thẳng từ cây chưa commit.
- Đã đọc `git log -1` trên máy local để biết commit nào đang được deploy.

### 2. Kéo code với đúng quyền

```bash
su - marketflow -s /bin/bash -c 'git -C /opt/marketflow pull --ff-only && git -C /opt/marketflow log --oneline -1'
```

`--ff-only` để không bao giờ tạo merge commit trên server. Dùng `su - marketflow`
vì repo thuộc user đó; chạy bằng root sẽ ra `dubious ownership`.

### 3. Khởi động lại và CHỜ

```bash
systemctl restart marketflow-api
sleep 16                      # 2 Uvicorn worker cần thời gian nạp
systemctl is-active marketflow-api
```

### 4. Kiểm chứng — bắt buộc, không bỏ qua

```bash
# Trong máy chủ, qua đúng đường mà Tunnel đi vào (nginx :8080)
curl -s http://127.0.0.1:8080/api/v1/health
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8080/

# Từ máy ngoài, qua domain thật
curl -s https://marketing.kienhieu.id.vn/api/v1/health
```

`is-active` chỉ nói tiến trình còn sống. **Không đủ.** Phải có HTTP 200 thật.

Nếu test AI: kiểm `is_fallback=false` và thời gian chạy hợp lý (56–120 giây với
OpenCode Zen). Dưới 5 giây là đang rơi vào fallback mô phỏng.

### 5. Đọc log nếu có bất thường

```bash
journalctl -u marketflow-api --since "2 min ago" --no-pager | tail -30
```

Dùng `--since "2 min ago"` **trong dấu nháy kép**. Không nháy đơn thì PowerShell
cắt chuỗi và `journalctl` báo lỗi parse timestamp.

## Lỗi đã gặp, không phải phát hiện lại

| Triệu chứng | Nguyên nhân | Cách xử lý |
|---|---|---|
| `fatal: dubious ownership` | chạy git bằng root cho repo của user khác | `su - marketflow -s /bin/bash -c '...'` |
| `Failed to parse timestamp: 10` | dấu nháy bị mất khi truyền qua PowerShell | bọc `--since "10 min ago"` trong nháy kép |
| `command not found` với `grep -E "a|b"` | `|` bị PowerShell tách thành pipe | tránh `\|` trong lệnh ssh từ PowerShell |
| App từ chối `SECRET_KEY` | `.env` đặt sai thư mục | phải ở `/opt/marketflow/backend/.env` |
| `error code: 1010` từ provider AI | thiếu `User-Agent` | đã sửa trong `ai_service.py` |
| 429 khi đăng nhập liên tục | rate limit theo IP thật, tự khoá mình | chờ hoặc restart service; không phải lỗi hệ thống |

## Quy tắc cứng

- **Không** `git push --force` lên `main`. Sửa thông điệp commit sai thì tạo commit
  mới, không amend rồi force.
- **Không** sửa config hệ thống mà không `cp` file gốc ra trước.
- **Không** để lại cấu hình tạm (probe location, log_format thử) trên production.
  Xoá và xác nhận đã xoá trong cùng lượt.
- **Không** báo "deploy xong" khi chỉ mới `git pull`. Phải qua bước 4.
- Kiểm tra R2/sao lưu ngoài VPS trước khi deploy thay đổi có rủi ro dữ liệu.