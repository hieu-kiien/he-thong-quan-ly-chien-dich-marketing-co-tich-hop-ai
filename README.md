---
document_id: BAI03-README
document_type: project-index
project_id: BAI03-SALES-AI
status: CANONICAL
language: vi
last_reviewed: 2026-08-18
---

# BAI03-SALES-AI — Hệ thống quản lý bán hàng có tích hợp AI

Đây là README điều hướng của dự án. Tài liệu phân tích đã được chuẩn hóa ở
[`docs/README.md`](docs/README.md); file này không mô tả một tính năng là đã
hoàn thành nếu chưa có bằng chứng trong mã nguồn và kiểm thử.

## Bắt đầu trong 5 phút

1. Đọc [`docs/00-project-context.md`](docs/00-project-context.md).
2. Tra yêu cầu trong [`docs/01-requirements-summary.md`](docs/01-requirements-summary.md).
3. Kiểm tra hiện trạng mã trong
   [`docs/02-architecture-and-code-status.md`](docs/02-architecture-and-code-status.md).
4. Nếu cần chạy nhánh skeleton, xem [`Code QLBH/README.md`](<Code QLBH/README.md>).
5. Nếu cần xem nhánh đã có model và CRUD danh mục, xem
   [`sales_management/README.md`](<sales_management/README.md>).
6. Nếu cần index tài liệu và tra cứu có citation, xem
   [`docs/07-knowledge-retrieval.md`](docs/07-knowledge-retrieval.md).
7. Nếu cần chuẩn hóa Word/PDF, bìa, độ dài và checklist hồ sơ, xem
   [`docs/08-documentation-standard.md`](docs/08-documentation-standard.md).

## Cấu trúc chính

| Đường dẫn | Vai trò |
|---|---|
| [`project.md`](project.md) | Yêu cầu gốc và rubric 40 tiêu chí; `CANONICAL` |
| [`informember.md`](informember.md) | Thông tin nhóm; `CANONICAL`, còn một điểm cần xác nhận |
| [`docs/`](docs/) | Lớp tài liệu chuẩn hóa cho AI và con người |
| [`Code QLBH/`](<Code QLBH/>) | Blueprint/skeleton Django modular |
| [`sales_management/`](<sales_management/>) | Nhánh hiện thực một phần |
| [`prompts/`](prompts/) | Prompt/kỹ thuật thử nghiệm; không phải nguồn yêu cầu |
| [`../Bai 02/CacGiaiDoanThucHien/`](<../Bai%2002/CacGiaiDoanThucHien/>) | Pipeline tài liệu upstream để đối chiếu; `REFERENCE` |
| [`QLBH demo/`](<../QLBH demo/>) | Không nằm trong thư mục này; bản demo cũ ở cấp `Codes/` |

## Trạng thái hiện tại

- Định hướng kỹ thuật trong code là Django, dù yêu cầu gốc cho phép FastAPI,
  Flask hoặc Django.
- `Code QLBH/` có cấu trúc module rõ nhưng nhiều model, URL, view và test còn
  là khung trống.
- `sales_management/` có model nghiệp vụ đáng kể và CRUD `categories`, nhưng
  phần lớn route/view/test chưa hoàn chỉnh.
- Chưa thấy bộ gọi provider AI, prompt runtime hoặc luồng AI chạy trong hai
  nhánh code; `AIEventLog` mới là mô hình ghi nhận sự kiện.
- Hồ sơ nộp được quản lý theo hai lớp: Markdown/YAML canonical cho tra cứu và
  DOCX/PDF cho giảng viên; trạng thái và giới hạn phải giống nhau ở cả hai.

Chi tiết và bằng chứng nằm trong
[`docs/02-architecture-and-code-status.md`](docs/02-architecture-and-code-status.md).

## Quy ước

Đọc [`AGENTS.md`](AGENTS.md) trước khi sửa dự án. Các tài liệu mới dùng
frontmatter YAML, ID ổn định và liên kết tương đối. Không đưa secret hoặc file
local sinh ra vào tài liệu.
