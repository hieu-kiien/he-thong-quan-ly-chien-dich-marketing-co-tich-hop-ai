# Cloudflare deployment — trạng thái và giới hạn

Thư mục này triển khai **frontend tĩnh** qua Cloudflare Worker và **proxy** mọi
request `/api/*` sang backend FastAPI chạy ở Render. Worker **không** chạy
backend.

## Vì sao không dùng Cloudflare Containers

Cấu hình cũ chạy FastAPI trong Cloudflare Containers qua Durable Object, R2
làm nơi snapshot SQLite. Đã thử deploy thật và **không deploy được**: tài khoản
Cloudflare này trả

```
Unauthorized: You do not have access to Cloudflare Containers.
Deploying containers requires the Workers Paid plan.
```

Worker và assets upload được, nhưng container không khởi động nên **mọi route
`/api/*` trả 404**. Đã xác nhận bằng cách gọi thật:

```
https://marketing.kienhieu.id.vn/                 -> 200 (HTML)
https://marketing.kienhieu.id.vn/api/v1/workspaces -> 404
```

Vì vậy backend chuyển sang Render (xem [`render.yaml`](../render.yaml) ở thư mục
gốc).

## Luồng hiện tại

1. Worker phục vụ frontend từ binding `ASSETS`.
2. `/api/*` và `/health` được proxy tới `BACKEND_ORIGIN` (Render).
3. Backend giữ dữ liệu trong Postgres, kết nối qua `DATABASE_URL` gán tay trong
   Render Dashboard. Render Free tier **không** có persistent disk, nên SQLite
   không phải lựa chọn được ở production — xem [`render.yaml`](../render.yaml).
4. Cron `*/5 * * * *` của Worker gọi `POST /api/v1/schedules/trigger-worker` ở
   backend kèm header `X-Scheduler-Secret`.

Không còn Durable Object, `writeQueue`, snapshot R2, `containerFetch`, hay
`/snapshot` — toàn bộ quyền ghi dữ liệu thuộc backend Render.

Frontend gọi `/api/v1` bằng **đường dẫn tương đối** nên đi qua Worker, không
hardcode domain backend. File `frontend/.env` cũngng đã đổi sang `VITE_API_URL=/api/v1`
— nếu để `http://127.0.0.1:8000/api/v1` thì Vite bake giá trị đó vào bundle và
mọi người dùng thật đều gọi localhost của chính họ.

### Ngoại lệ: nhóm endpoint AI đi thẳng Render

Frontend **không** gọi nhóm endpoint AI qua Worker. `isAiPath()` trong
`frontend/src/services/api.ts` tách các path `/ai/*` ra và dùng biến
`VITE_AI_API_URL` (mặc định trỏ thẳng `https://marketflow-api-9onk.onrender.com/api/v1`).

Lý do có số đo, không phải phỏng đoán: Cloudflare giới hạn subrequest ~100 giây.
Trên production, `POST /api/v1/ai/omnichannel` qua Worker trả `error 524` sau
khoảng 100 giây; gọi thẳng Render cùng endpoint đó trả `HTTP 200` sau **237 giây**
với `is_fallback=false`. Với provider AI nghề, mọi lời gọi thật đều chết nếu đi qua
Worker.

Hệ quả phải nói thẳng: URL backend lộ ra trong JavaScript gửi tới trình duyệt ở
nhóm endpoint này. Đó là đánh đổi có số đo, không phải thiết kế lý tưởng.

## Cron và scheduler

Scheduler trong tiến trình backend bị tắt khi deploy (`SCHEDULER_ENABLED=false`)
vì nó ghi thẳng vào database ngoài HTTP path. Worker đánh thức nó mỗi 5 phút.
Nếu bỏ trigger `criggers.crons`, lịch đăng sẽ không bao giờ chạy.

## Cấu hình an toàn

Worker chỉ còn **một** secret: `SCHEDULER_SECRET`. `BACKEND_ORIGIN` nằm trong
`vars` vì đó là địa chỉ công khai. Các secret thật (key JWT, AI key, mật khẩu
demo) đã chuyển sang biến môi trường của Render.

```bash
wrangler secret put SCHEDULER_SECRET
npm run deploy   # build frontend + wrangler deploy --secrets-file .env.production
```

- Không ghi giá trị secret vào README, log hoặc commit.
- Kiểm tra cấu hình trước khi deploy: `npm run check`.
- Sau deploy, xác nhận health endpoint, AI provider thật (không rơi âm thầm về
  fallback), đăng nhập thật, ghi dữ liệu thử rồi restart backend.

## Giới hạn còn lại

- **Render Free tier không có persistent disk.** Blueprint cố tình **không** khai
  báo `databases:` lẫn disk: Render Postgres plan free tự hạn sau 30 ngày và bị
  **xoá** (không phải khoá). Vì vậy production phải trỏ `DATABASE_URL` tới Postgres
  có sở hữu lâu dài ngoài Render — Neon đã tạo sẵn (`marketflow-prod`).
- Backend nằm sau Worker thêm một network hop vào mỗi request API — trừ nhóm
  endpoint AI, vốn cố ý đi thẳng Render (xem mục ở trên).
- Render free tier cold-start chậm (vài chục giây). Đã có banner "Máy chủ đang
  thức dậy" ở frontend nhưng cần kiểm thử lại với backend thật.
- Chưa có kết quả kiểm thử concurrency, restore và rollback trên hạ tầng này.

Không đưa dữ liệu khách hàng thật lên deployment này trước khi có kết quả kiểm
thử và quyết định lưu trữ phù hợp. Kế hoạch giải quyết nằm trong
[docs/ROADMAP.md](../docs/ROADMAP.md).

## Cổng trước khi dùng dữ liệu thật

- [ ] Có staging và dữ liệu giả lập tách biệt.
- [ ] `DATABASE_URL` production trỏ tới Postgres lâu dài (Neon), không phải DB Render
      plan free và không phải SQLite file trong container.
- [ ] Đo latency/throughput khi nhiều người ghi đồng thời.
- [ ] Thử backend không phản hồi và xác nhận Worker trả lỗi có thông điệp, không
      phải trang trắng.
- [ ] Chứng minh cron thực sự đánh thức scheduler (không chỉ deploy thành công).
- [ ] Có rollback/migration/backup procedure được diễn tập.
- [ ] Có phương án lưu trữ được chọn theo kết quả đo và được cập nhật trong kiến trúc.

Nếu chưa đạt các mục trên, hãy dùng local hoặc staging với dữ liệu có thể khôi
phục.