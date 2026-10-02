# Cloudflare deployment — trạng thái và giới hạn

Thư mục này triển khai frontend assets và FastAPI Container qua Cloudflare Worker. Worker dùng Durable Object làm điểm vào API, database hiện là SQLite trong container, và R2 giữ snapshot database.

## Luồng hiện tại

1. Worker phục vụ frontend từ binding ASSETS.
2. Yêu cầu API được chuyển tiếp tới FastAPI Container.
3. Container dùng SQLite tại /app/data/marketing_campaigns.db.
4. Khi khởi động, Worker lấy snapshot mới nhất từ bucket R2 và phục hồi database.
5. Sau thao tác ghi API, code serialize write và lưu snapshot SQLite lên R2.

Chi tiết triển khai là source code trong src/index.ts và binding/limit là wrangler.jsonc. README này tóm tắt hành vi, không thay thế cấu hình đó.

## Trạng thái sử dụng

Cấu hình này hiện phù hợp cho demo/staging và kiểm chứng kiến trúc. Chưa được xác nhận là nền tảng production cho nhiều workspace/khách hàng thật.

Trong src/index.ts có các giới hạn đã ghi nhận:

- Một Durable Object/write queue tuần tự hóa các thao tác ghi; với max_instances hiện tại, write chậm có thể làm các thao tác ghi khác phải đợi.
- Mỗi write tải toàn bộ database lên R2. Chi phí và latency tăng theo kích thước SQLite file.
- Cần giữ tính nhất quán giữa write database và snapshot; cần thử lỗi R2, restart, restore và request đọc có side-effect.
- Snapshot cuối cùng không tự chứng minh có point-in-time recovery, lịch sử phiên bản hữu dụng hay quy trình restore đã được diễn tập.

Không đưa dữ liệu khách hàng thật lên deployment này trước khi có kết quả kiểm thử concurrency/restore và quyết định lưu trữ phù hợp. Kế hoạch giải quyết nằm trong [docs/ROADMAP.md](../docs/ROADMAP.md).

## Cấu hình an toàn

Tạo file local không commit theo mẫu/required secrets trong wrangler.jsonc. Các tên secret được code yêu cầu gồm SECRET_KEY, JWT_SECRET_KEY, BYOK_ENCRYPTION_KEY, AI_API_KEY và mật khẩu khởi tạo các vai trò demo.

- Không ghi giá trị secret vào README, log hoặc commit.
- Dùng giá trị riêng cho staging/production; không dùng mật khẩu demo trong môi trường có người dùng thật.
- Kiểm tra binding R2 và Durable Object trước khi deploy.
- Triển khai bằng script trong package.json; kiểm tra cấu hình và biến bắt buộc trước khi chạy.
- Sau deploy, xác nhận health endpoint, AI provider thật (không rơi âm thầm về fallback), ghi dữ liệu thử, restart và restore.

## Cổng trước khi dùng dữ liệu thật

- [ ] Có staging và dữ liệu giả lập tách biệt.
- [ ] Đo latency/throughput khi nhiều người ghi đồng thời.
- [ ] Thử R2 unavailable, snapshot upload thất bại, container restart và phục hồi snapshot.
- [ ] Chứng minh write không báo thành công khi snapshot chưa bền vững.
- [ ] Đánh giá endpoint đọc gây side-effect và đường đi qua write queue.
- [ ] Có rollback/migration/backup procedure được diễn tập.
- [ ] Có phương án lưu trữ được chọn theo kết quả đo và được cập nhật trong kiến trúc.

Nếu chưa đạt các mục trên, hãy dùng local hoặc staging với dữ liệu có thể khôi phục.
