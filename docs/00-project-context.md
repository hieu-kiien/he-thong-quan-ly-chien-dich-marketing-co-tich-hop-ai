---
document_id: AIA331-DOC-00
document_type: project-context
project_id: AIA331-80300-MARKETING-AI
project_title: Hệ thống quản lý chiến dịch marketing có tích hợp AI
course: Ứng dụng trí tuệ nhân tạo - AIA331
assignment_code: "80300"
priority: P1
priority_level: HIGH
status: DERIVED
sources: [../source-materials/BÀI KIỂM TRA.png, ../source-materials/DỰ ÁN.png, ../project.md, ../informember.md]
last_reviewed: 2026-08-18
---

# Bối cảnh dự án

## 1. Định danh và nhóm

| Trường | Giá trị | Trạng thái |
|---|---|---|
| Đề tài | Hệ thống quản lý chiến dịch marketing có tích hợp AI | CANONICAL |
| Học phần | Ứng dụng trí tuệ nhân tạo - AIA331 | CANONICAL |
| Mã số | 80300 | CANONICAL |
| Hình thức | Dự án | CANONICAL |
| Ưu tiên hồ sơ triển khai | P1 / HIGH | INTERNAL_PRIORITY; hai ảnh nguồn là P0 |
| Nhóm | Nhóm 25 | CANONICAL |
| Thành viên | Nguyễn Hải Đăng; Vũ Hiếu Kiên | CANONICAL |
| Lớp/khoa | CNTTK23C / Khoa Công nghệ thông tin | CANONICAL |
| Trường | Trường ĐH CNTT & TT Thái Nguyên | CANONICAL |

## 2. Vấn đề

Thông tin chiến dịch, kênh, nội dung, ngân sách, lịch đăng và metric thường nằm
rải rác. Người làm marketing mất thời gian lên ý tưởng và tổng hợp kết quả.
Ứng dụng cần cung cấp một nơi quản lý thống nhất và một lớp AI hỗ trợ có thể
kiểm tra được.

## 3. Actor

| Actor | Quyền/trách nhiệm |
|---|---|
| Marketing Manager | Toàn quyền nghiệp vụ được cấp; duyệt nội dung; xem chỉ số |
| Marketing Staff | Tạo/cập nhật dữ liệu được phân quyền; yêu cầu AI sinh nháp |
| AI Service | Chỉ nhận context đã lọc; không tự đăng và không tự quyết định |

## 4. Ranh giới hiện thực

`marketing_management/` là baseline canonical. Các thư mục `Code QLBH/`,
`sales_management/`, báo cáo bán hàng và `QLBH demo/` là `LEGACY`, giữ lại để
không mất lịch sử nhưng không được dùng để chứng minh đề tài marketing.

## 5. Nguồn P0 / CRITICAL

`source-materials/BÀI KIỂM TRA.png` là checklist 10 tiêu chí đánh giá;
`source-materials/DỰ ÁN.png` là đề bài chính thức. Hai ảnh phải được ưu tiên
trước tài liệu diễn giải, code và prompt khi có xung đột.
