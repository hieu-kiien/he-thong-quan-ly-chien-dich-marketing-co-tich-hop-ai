# Triển khai native trên CloudCode VPS

## Đánh giá hiện tại

VPS có 2 vCPU, 2 GiB RAM và 30 GB đĩa. Số liệu lần kiểm tra gần nhất là khoảng
393 MiB RAM khi máy gần rảnh. Cơ sở dữ liệu production khoảng 34 MB. Cấu hình này
đủ cho ứng dụng hiện tại ở mức tải thấp đến vừa, miễn là giới hạn tác vụ AI đồng
thời và không chạy mô hình AI tại VPS.

Ứng dụng có frontend React/Vite, API FastAPI, PostgreSQL và hàng đợi AI được lưu
trong PostgreSQL. Worker AI cùng scheduler được khởi động trong vòng đời FastAPI;
không cần Redis hay Celery. Tác vụ AI gọi nhà cung cấp bên ngoài, vì vậy thời
gian chờ mô hình chiếm ưu thế hơn CPU của VPS.

## Bố trí runtime

- PostgreSQL 16.15 chỉ nghe trên loopback; không mở cổng 5432 ra Internet.
- FastAPI chạy dưới tài khoản hệ thống `marketflow`, nghe tại `127.0.0.1:8000`
  và chỉ có một Uvicorn worker.
- Nginx phục vụ frontend tĩnh và proxy `/api/` tới FastAPI; Nginx chỉ nghe trên
  `127.0.0.1:8080`.
- Cloudflare Tunnel được quản lý trong Cloudflare Dashboard và trỏ
  `marketing.kienhieu.id.vn` tới Nginx tại `http://127.0.0.1:8080`. Frontend và
  API dùng chung hostname, nên không cần cấu hình CORS cho API hostname riêng.
- Frontend được build thành file tĩnh. Node không cần chạy sau khi build.

File API service mẫu ở `deploy/vps/`. Nó giả định source ở `/opt/marketflow`,
frontend đã build ở `/srv/marketflow/frontend`, và env production ở
`/etc/marketflow/api.env` với quyền chỉ root đọc.

## Giới hạn tài nguyên

Đặt các biến sau trong env production:

```dotenv
APP_ENV=production
DATABASE_URL=postgresql://marketflow:<mat-khau-hex>@127.0.0.1:5432/marketflow
SCHEDULER_ENABLED=true
AI_JOB_WORKER_ENABLED=true
AI_JOB_CONCURRENCY=1
AI_JOB_TIMEOUT_SECONDS=300
AI_JOB_POLL_INTERVAL_SECONDS=2
AI_JOB_RETENTION_DAYS=7
```

Tạo mật khẩu PostgreSQL chỉ gồm ký tự hex để tránh phải URL-encode trong
`DATABASE_URL`. `SECRET_KEY`, `JWT_SECRET_KEY` và `BYOK_ENCRYPTION_KEY` phải là
secret production mạnh. Cần giữ nguyên `BYOK_ENCRYPTION_KEY` hiện dùng để đọc
các API key đã mã hóa trong DB. Không đưa secret vào repo hoặc log.

PostgreSQL nên giữ `shared_buffers` khoảng 128 MB, `work_mem` 4 MB và
`max_connections` khoảng 30. Chỉ tăng `AI_JOB_CONCURRENCY` khi đã theo dõi RAM
thực tế và có nhu cầu xử lý song song. Không chạy nhiều Uvicorn worker vì mỗi
tiến trình sẽ khởi động worker AI và scheduler riêng.

## Kế hoạch chuyển đổi an toàn

1. Cài PostgreSQL, Nginx, Python virtualenv và `cloudflared`; tạo user hệ thống
   không có quyền đăng nhập tương tác. PostgreSQL hướng dẫn cài bản 16 trên
   Ubuntu 24.04 qua PGDG apt repository trong
   [tài liệu chính thức](https://www.postgresql.org/download/linux/ubuntu/).
2. Chuyển source từ repo hiện tại, cài dependency vào virtualenv và build
   frontend với `VITE_API_URL=/api/v1`, `VITE_AI_API_URL` để trống.
3. Tạo PostgreSQL local, restore bản dump thử và đối chiếu bảng, tài khoản cùng
   số bản ghi trước khi đổi traffic.
4. Tạo Tunnel trong Cloudflare Dashboard, cài `cloudflared` service bằng tunnel
   token và đặt hostname route vào Nginx. Tunnel mở kết nối đi ra Cloudflare,
   không cần mở cổng ứng dụng vào Internet; xem
   [tài liệu Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/get-started/).
   Khởi động API, scheduler, Nginx và Tunnel; kiểm tra health/API/login qua
   hostname thử nghiệm.
5. Sao lưu lần cuối, tạm dừng ghi trong lúc chuyển dữ liệu cuối, rồi mới chuyển
   route của domain. Giữ Render và Neon sẵn sàng rollback cho tới khi xác nhận
   app và dữ liệu hoạt động ổn định.
6. Thiết lập backup PostgreSQL hằng ngày, kiểm tra khôi phục và theo dõi RAM,
   swap, dung lượng đĩa, log lỗi API và `pg_stat_activity`.

## Kế hoạch chỉnh code

- Giữ queue AI hiện có làm đường gọi chính trên UI; nó trả job ID nhanh và lưu
  trạng thái trong PostgreSQL.
- Dùng một API origin cùng domain. Sau khi rà soát các luồng còn gọi endpoint AI
  đồng bộ, có thể bỏ cơ chế `VITE_AI_API_URL` riêng cho Render và cập nhật các
  chú thích cũ nói request AI phải bypass Worker.
- Giữ endpoint đồng bộ để tương thích trong giai đoạn đầu; không xóa API công khai
  trong cùng lần chuyển hạ tầng.
- Không đổi thuật toán nghiệp vụ hoặc schema chỉ để phục vụ VPS. Mọi thay đổi
  nguồn cần phân tích GitNexus và giữ cấu hình production tách khỏi mặc định dev.

## Rủi ro vận hành

VPS đơn là một điểm lỗi duy nhất. Backup trên cùng đĩa không bảo vệ khi hỏng VPS;
cần có bản sao ngoài VPS và phải thử restore. Chuyển domain chỉ thực hiện sau khi
đã kiểm tra bản chạy mới và có thể quay lại Render/Neon.
Khi chuyển hostname đang gắn với Cloudflare Worker, chỉ đổi route của
`marketing.kienhieu.id.vn`; giữ nguyên các DNS record email.

## Trạng thái đã triển khai (2026-10-09)

Phần trên là kế hoạch. Dưới đây là những gì đã thực sự chạy và đã kiểm chứng.

| Hạng mục | Giá trị thực tế |
| --- | --- |
| Máy chủ | CloudCode NAT, Ubuntu 24.04, 2 vCPU, 2 GiB RAM, 30 GiB đĩa |
| SSH | `vn-hn.cloudcode.io.vn` cổng `30513`, key `marketflow_vps_ed25519` |
| Python | 3.12.3 hệ thống; venv ứng dụng Python 3.11.17 |
| PostgreSQL | 16.15, `shared_buffers` 384 MB, `max_connections` 40 |
| Nginx | 1.24.0, nghe `127.0.0.1:8080` |
| Cloudflared | 2026.10.0, tunnel `marketflow-prod` |
| Source | `/opt/marketflow`, venv `/opt/marketflow/.venv` |
| Cấu hình | `/opt/marketflow/backend/.env` (quyền 600) |
| Giao diện tĩnh | `/var/www/marketflow` |
| Domain | `https://marketing.kienhieu.id.vn` |

Dịch vụ systemd: `marketflow-api` (2 Uvicorn worker, `MemoryMax=1200M`, AI
concurrency 1 mỗi worker) và `cloudflared-tunnel`.

### Ba sai lệch phát hiện khi dựng thật

Tài liệu và hướng dẫn ban đầu đều dự đoán, phần này ghi lại điều thực tế:

1. **QUIC bị chặn.** Mạng VPS không mở UDP/443 nên tunnel thử QUIC rồi timeout.
   Buộc dùng `protocol: http2` trong `/etc/cloudflared/config.yml`.
2. **`.env` phải nằm trong `backend/`.** `config.py` tính đường dẫn tương đối
   tới chính nó; đặt ở thư mục gốc khiến app từ chối `SECRET_KEY`.
3. **Lệch phiên bản PostgreSQL.** Kế hoạch ghi bản 18; máy chủ đã có 16.15 từ
   khoá Ubuntu nên dùng bản 16 cho khớp.

### Đã kiểm chứng bằng thực thi, không phải giả định

- Health, trang chủ, đăng nhập ADMIN, các endpoint có phân trang: HTTP 200.
- Dashboard báo `real_rows: 0` — cơ sở dữ liệu sạch, không còn dữ liệu mẫu.
- **AI thật**: job chạy 100 giây, `is_fallback=false`, model `space-bunny-free`,
  không phải fallback mô phỏng.
- **Sao lưu đã thử khôi phục**: phục hồi vào cơ sở dữ liệu tạm được 20 bảng và
  1 user, khớp với bản gốc. Lịch 03:00 hằng ngày, giữ 7 bản mới nhất.

### Hạ tầng cũ đã gỡ

Render (`marketflow-api`, `marketflow-db`), Neon (`marketflow-prod`), Cloudflare
Worker (`marketflow-kienhieu`) và Pages (`marketflow`) đều đã xoá. `render.yaml`
và `cloudflare/wrangler.jsonc` đã xoá khỏi repo để không bị tái tạo ngoài ý muốn.

### Việc còn lại

- `marketflow-api` đang chạy bằng `User=root`; cần chuyển sang user không đặc quyền.
- Xoá `/opt/marketflow/.env` trùng thừa (app đọc bản trong `backend/`).
- Bản sao lưu nằm cùng đĩa với ứng dụng nên không cứu được lỗi phần cứng; cần
  đẩy lên Cloudflare R2 hoặc tương tự.
- Bộ giới hạn đăng nhập gắn với IP do Cloudflare gửi trong `X-Forwarded-For`, nên
  mọi người dùng đều dùng chung một "IP" và dễ khoá nhầm lẫn nhau.
