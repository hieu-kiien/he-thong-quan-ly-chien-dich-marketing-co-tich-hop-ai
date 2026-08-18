---
document_id: AIA331-DOC-01
document_type: requirements-summary
project_id: AIA331-80300-MARKETING-AI
status: CANONICAL_DERIVED
priority: P0
priority_level: CRITICAL
sources: [../source-materials/BÀI KIỂM TRA.png, ../source-materials/DỰ ÁN.png, ../project.md]
last_reviewed: 2026-08-18
---

# Ma trận yêu cầu

## 1. Yêu cầu chức năng

| ID | Yêu cầu | Actor | Acceptance criteria |
|---|---|---|---|
| FR-001 | Đăng nhập và phân quyền | Manager/Staff | Người chưa đăng nhập không vào màn hình nghiệp vụ; vai trò được kiểm tra |
| FR-002 | Quản lý chiến dịch | Manager/Staff | Có tên, mục tiêu, audience, product, thời gian, ngân sách, trạng thái |
| FR-003 | Quản lý kênh | Manager/Staff | Kênh hoạt động được gắn với content/metric |
| FR-004 | Quản lý nội dung/lịch | Manager/Staff | Content gắn campaign/channel, có loại và scheduled time |
| FR-005 | Ghi nhận metric | Staff | Lưu views, clicks, conversions, cost theo campaign/channel/ngày |
| FR-006 | Duyệt nội dung | Manager | Nội dung chưa approved không được publish |
| FR-007 | Tìm kiếm/lọc | Manager/Staff | Lọc chiến dịch theo tên và status; mở rộng theo channel/time |
| FR-008 | Thống kê | Manager | Tính totals, CTR, conversion rate, cost per conversion |
| AI-001 | Sinh ý tưởng | Manager/Staff | Có 5 ý tưởng theo objective/channel/audience |
| AI-002 | Sinh caption/email nháp | Manager/Staff | Output phù hợp channel, có warning và approval gate |
| AI-003 | Tóm tắt/gợi ý | Manager | Dựa metric được cấp quyền, nêu thiếu dữ liệu |

## 2. Yêu cầu phi chức năng

| ID | Nhóm | Tiêu chí |
|---|---|---|
| NFR-001 | Security | Secret ở environment; authentication/authorization/CSRF |
| NFR-002 | Safety | AI không tự đăng; không bịa claim; output có nguồn/phiên bản |
| NFR-003 | Data integrity | Ngày hợp lệ, metric không âm, quan hệ unique và giới hạn click/conversion |
| NFR-004 | Availability | Có migration/seed/hướng dẫn chạy từ môi trường sạch |
| NFR-005 | UX | Trạng thái, lỗi form và thông báo thao tác rõ ràng |
| NFR-006 | Testability | Test model, service, view và fallback AI |

## 3. Quy tắc nghiệp vụ

| ID | Quy tắc |
|---|---|
| BR-001 | `start_date <= end_date`. |
| BR-002 | `clicks <= impressions`, `conversions <= clicks`. |
| BR-003 | Một campaign/channel/ngày chỉ có một bản metric. |
| BR-004 | Content AI phải qua `APPROVED` trước `PUBLISHED`. |
| BR-005 | Khi provider lỗi hoặc thiếu key, fallback phải nói rõ là bản nháp. |
