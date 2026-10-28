# Kế hoạch nghiên cứu, thiết kế và nghiệm thu dự án (MarketFlow AI)

## 1. Nhận diện dự án

- Tên dự án: Hệ thống quản lý chiến dịch marketing có tích hợp AI (MarketFlow AI)
- Học phần: Ứng dụng trí tuệ nhân tạo - AIA331 (Mã đề tài: 80300)
- Đơn vị: Trường Đại học Công nghệ Thông tin và Truyền thông, Đại học Thái Nguyên
- Nhóm: 25; Vũ Hiếu Kiên DTC245200244; Nguyễn Hải Đăng DTC245120051
- Giảng viên hướng dẫn: TS. Nguyễn Tuấn Anh
- Trạng thái hiện tại: **Đã hoàn thành 100% mã nguồn Full-stack, vượt qua 151 ca kiểm thử tự động và vận hành thực tế trên Production VPS (`https://marketing.kienhieu.id.vn`)**

## 2. Bài toán và Kiến trúc giải pháp

- **Các vai trò người dùng**: `MANAGER` (quản trị nhân sự, kênh, Brand Kit, quản lý chiến dịch toàn cục, phê duyệt nội dung HITL, giám sát KPI), `MARKETER` (vận hành chiến dịch sở hữu `owner_id`, soạn nội dung, gọi Trợ lý AI, nhập chỉ số).
- **Lược đồ CSDL 14 bảng**: `users`, `channels`, `brand_profile`, `banned_keywords`, `campaigns`, `campaign_channels`, `contents`, `content_reviews`, `schedules`, `metrics`, `notifications`, `ai_threads`, `ai_messages`, `ai_actions`.
- **Kiến trúc Trợ lý AI có kiểm soát**: Dịch vụ `ai-runner` (`:8100`) cô lập tiến trình `opencode run` dưới tài khoản `mfai` (`RUNNER_CONCURRENCY=1`, `MemoryMax=896M`), gọi ngược vào máy chủ công cụ nội bộ FastMCP (`/mcp`) của Backend bằng mã thông báo `Run-Token` JWT ngắn hạn (10 phút).
- **14 Công cụ MCP (9 Read + 5 Propose)**: Mọi thao tác ghi của AI bắt buộc đi qua 5 công cụ `propose_*` tạo thẻ đề xuất `ai_action = PROPOSED` chờ người dùng bấm *Xác nhận* (`EXECUTED`) hoặc *Từ chối* (`REJECTED`).

## 3. Kết quả nghiệm thu theo mục tiêu

| Mục tiêu | Bằng chứng thực nghiệm trong dự án | Trạng thái |
|---|---|---|
| Quản lý nghiệp vụ cốt lõi 14 bảng | 104 ca kiểm thử Backend Pytest (`backend/tests/test_*.py`) đạt 100% Pass | `TESTED` |
| Phân quyền RBAC & Chống tự duyệt | Kiểm tra `owner_id` và chặn tự duyệt bài của chính mình (`CANNOT_REVIEW_OWN`) | `TESTED` |
| Máy trạng thái HITL & Từ khóa cấm | `DRAFT` -> `PENDING_REVIEW` -> `APPROVED`/`REJECTED` -> `PUBLISHED`, khóa xóa `CONTENT_LOCKED` | `TESTED` |
| Điều phối AI & Dự phòng 13 mô hình | 18 ca kiểm thử `ai-runner/tests/` Pass 100%, hỗ trợ 13 mô hình trên 5 nền tảng | `TESTED` |
| Đánh giá định lượng 4 giai đoạn Prompt | `scripts/evaluate_assistant.py` trên 8 kịch bản: Bản 1: 75%, Bản 2: 62.5%, Bản 3: 75%, Bản 4: 87.5% (7/8) | `MEASURED` |
| Kiểm thử giao diện E2E & Triển khai VPS | 29 ca kiểm thử Playwright E2E trên Chromium Pass 100%; vận hành tại `https://marketing.kienhieu.id.vn` | `TESTED` |
