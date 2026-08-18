---
document_id: AIA331-SOURCE-REGISTER
document_type: source-register
project_id: AIA331-80300-MARKETING-AI
status: CANONICAL_DERIVED
last_reviewed: 2026-08-18
---

# Sổ đăng ký nguồn

| Source ID | Nguồn | Authority | Dùng cho |
|---|---|---|---|
| SRC-000 | `source-materials/BÀI KIỂM TRA.png` / ảnh bài kiểm tra người dùng cung cấp | P0 / CRITICAL | 10 tiêu chí đánh giá, nội dung bắt buộc của báo cáo |
| SRC-001 | `source-materials/DỰ ÁN.png` / ảnh đề bài người dùng cung cấp | P0 / CRITICAL | tên đề tài, AIA331, 80300, requirements |
| SRC-002 | `project.md` | CANONICAL | yêu cầu đã biên tập có truy vết |
| SRC-003 | `informember.md` | CANONICAL | nhóm, thành viên, lớp, khoa, trường |
| SRC-004 | `marketing_management/` | IMPLEMENTED_BASELINE | code và trạng thái triển khai |
| SRC-005 | `marketing_management/campaigns/tests.py` | IMPLEMENTED_BASELINE | bằng chứng kiểm thử |
| SRC-006 | `docs/` | DERIVED | tài liệu tra cứu/canonical cho AI |
| SRC-007 | Google Classroom screenshots/user notes | REFERENCE_TO_CANONICAL | quy cách thư mục ZIP, mốc nộp |
| SRC-008 | `Code QLBH/`, `sales_management/`, báo cáo bán hàng | LEGACY | lịch sử; không dùng làm yêu cầu marketing |

## Quy tắc nguồn

Nếu nội dung từ nguồn legacy khác một trong hai đề bài ảnh, chọn `SRC-000` hoặc
`SRC-001` tương ứng và ghi xung đột. Hai nguồn P0 / CRITICAL luôn được ưu tiên
trước tài liệu diễn giải.
Không dùng đường dẫn ổ đĩa cá nhân trong báo cáo phát hành; chỉ dùng path tương
đối trong repo.
