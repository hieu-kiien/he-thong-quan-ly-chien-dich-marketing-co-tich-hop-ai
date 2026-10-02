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
3. Backend giữ SQLite tại `/app/data/marketing_campaigns.db` trên persistent disk.
4. Cron `*/5 * * * *` của Worker gọi `POST /api/v1/schedules/trigger-worker` ở
   backend kèm header `X-Scheduler-Secret`.

Không còn Durable Object, `writeQueue`, snapshot R2, `containerFetch`, hay
`/snapshot` — toàn bộ quyền ghi dữ liệu thuộc backend Render.

Frontend gọi `/api/v1` bằng **đường dẫn tương đối** nên đi qua Worker, không
hardcode domain backend. File `frontend/.env` cũngng đã đổi sang `VITE_API_URL=/api/v1`
— nếu để `http://127.0.0.1:8000/api/v1` thì Vite bake giá trị đó vào bundle và
mọi người dùng thật đều gọi localhost của chính họ.

## Cron và scheduler

Scheduler trong tiến trình backend bị tắt khi deploy (`SCHEDULER_ENABLED=false`)
vì nó ghi thẳng vào SQLite ngoài HTTP path và không đi qua bất kỳ cơ chế snapshot
nào. Worker đánh thức nó mỗi 5 phút. Nếu bỏ trigger `criggers.crons`, lịch đăng
sẽ không bao giờ chạy.

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

- **Render Free tier không có persistent disk.** Blueprint khai báo disk nên cần
  plan Starter trở lên. Nếu dùng plan free, mọi thay đổi mất khi service restart
  — đó là mất dữ liệu thật, không phải hành vi được chấp nhận.
- Backend nằm sau Worker thêm một network hop vào mỗi request API.
- Render free tier cold-start chậm (vài chục giây). Đã có banner "Máy chủ đang
  thức dậy" ở frontend nhưng cần kiểm thử lại với backend thật.
- Chưa có kết quả kiểm thử concurrency, restore và rollback trên hạ tầng này.

Không đưa dữ liệu khách hàng thật lên deployment này trước khi có kết quả kiểm
thử và quyết định lưu trữ phù hợp. Kế hoạch giải quyết nằm trong
[docs/ROADMAP.md](../docs/ROADMAP.md).

## Cổng trước khi dùng dữ liệu thật

- [ ] Có staging và dữ liệu giả lập tách biệt.
- [ ] Persistent disk đã gắn và đã chứng minh dữ liệu còn sau restart.
- [ ] Đo latency/throughput khi nhiều người ghi đồng thời.
- [ ] Thử backend không phản hồi và xác nhận Worker trả lỗi có thông điệp, không
      phải trang trắng.
- [ ] Chứng minh cron thực sự đánh thức scheduler (không chỉ deploy thành công).
- [ ] Có rollback/migration/backup procedure được diễn tập.
- [ ] Có phương án lưu trữ được chọn theo kết quả đo và được cập nhật trong kiến trúc.

Nếu chưa đạt các mục trên, hãy dùng local hoặc staging với dữ liệu có thể khôi
phục.