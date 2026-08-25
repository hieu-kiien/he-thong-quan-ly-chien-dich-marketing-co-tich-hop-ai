---
document_id: AIA331-DOC-01
document_type: requirements-summary
project_id: AIA331-80300-MARKETING-AI
status: CANONICAL_DERIVED
priority: P1
priority_level: HIGH
sources: [../source-materials/BÀI KIỂM TRA.png, ../source-materials/DỰ ÁN.png, ../project.md]
last_reviewed: 2026-08-18
---

# Ma trận yêu cầu

## 1. Yêu cầu chức năng

| ID | Yêu cầu | Actor | Acceptance criteria |
|---|---|---|---|
| FR-001 | Đăng nhập và phân quyền | Manager/Staff | Người chưa đăng nhập không vào màn hình nghiệp vụ; vai trò được kiểm tra |
| FR-002 | Quản lý chiến dịch | Manager/Staff | Có tên, mục tiêu, audience, product, thời gian, ngân sách, trạng thái |
| FR-003 | Quản lý kênh | Manager/Staff | Tạo, sửa, tra cứu kênh; kênh hoạt động được gắn với content/metric |
| FR-004 | Quản lý nội dung/lịch | Manager/Staff | Tạo content gắn campaign/channel, có loại và scheduled time |
| FR-005 | Ghi nhận metric | Staff | Tạo metric theo campaign/channel/ngày; kiểm tra funnel và chống trùng |
| FR-006 | Duyệt nội dung | Manager | Duyệt/từ chối/đăng; nội dung chưa approved không được publish |
| FR-007 | Tìm kiếm/lọc | Manager/Staff | Lọc chiến dịch theo tên và status; mở rộng theo channel/time |
| FR-008 | Thống kê | Manager | Tính totals, CTR, conversion rate, cost per conversion |
| AI-001 | Sinh ý tưởng | Manager/Staff | Có 5 ý tưởng theo objective/channel/audience |
| AI-002 | Sinh caption/email nháp | Manager/Staff | Output phù hợp channel, có warning và approval gate |
| AI-003 | Tóm tắt/gợi ý | Manager | Dựa metric được cấp quyền, nêu thiếu dữ liệu |

## 2. Yêu cầu phi chức năng

| ID | Nhóm | Tiêu chí |
|---|---|---|
| NFR-001 | Security | Secret ở environment; authentication/authorization/CSRF; không để API key trong repo |
| NFR-002 | Safety | AI không tự đăng; không bịa claim; output có nguồn/phiên bản |
| NFR-003 | Data integrity | Ngày hợp lệ, metric không âm, quan hệ unique và giới hạn click/conversion |
| NFR-004 | Availability | Có migration/seed/hướng dẫn chạy từ môi trường sạch; backup SQLite và restore được kiểm tra |
| NFR-005 | Performance | CRUD p95 mục tiêu < 2 giây với tối đa 50 người dùng đồng thời; AI timeout 20 giây và fallback |
| NFR-006 | Authorization | Manager duyệt/đăng; Staff nhập content/metric; mọi route nghiệp vụ kiểm tra role |
| NFR-007 | UX | Trạng thái, lỗi form, empty state và thông báo thao tác rõ ràng |
| NFR-008 | Testability | Test model, constraint, permission, view, service và fallback AI |
| NFR-009 | Printability | A4, tương phản đủ khi in đen trắng; màu không phải tín hiệu duy nhất; sơ đồ/biểu đồ có nhãn và kiểu nét phân biệt |

## 3. Quy tắc nghiệp vụ

| ID | Quy tắc |
|---|---|
| BR-001 | `start_date <= end_date`. |
| BR-002 | `clicks <= impressions`, `conversions <= clicks`. |
| BR-003 | Một campaign/channel/ngày chỉ có một bản metric. |
| BR-004 | Content AI phải qua `APPROVED` trước `PUBLISHED`. |
| BR-005 | Khi provider lỗi hoặc thiếu key, fallback phải nói rõ là bản nháp. |

## 3.1 Ma trận phân quyền

| Chức năng | Marketing Staff | Marketing Manager |
|---|---:|---:|
| Xem/tạo/sửa campaign | Có | Có |
| Quản lý channel | Có | Có |
| Tạo content và ghi metric | Có | Có |
| Duyệt/từ chối/đăng content | Không | Có |
| Xem thống kê và gọi AI | Có | Có |

## 3.2 Sao lưu và hiệu năng

- SQLite được sao lưu bằng `python manage.py dbbackup` hoặc bản sao nhất quán
  của `db.sqlite3` khi ứng dụng dừng; bản backup không đưa vào Git/ZIP.
- Mục tiêu phục hồi: RPO tối đa 24 giờ, RTO tối đa 30 phút cho bản demo; quy trình
  restore được ghi trong `docs/12-operations-and-backup.md`.
- CRUD không gọi provider phải phản hồi dưới 2 giây ở tải lớp học; AI có timeout
  20 giây, lỗi/thiếu key chuyển sang fallback offline.
