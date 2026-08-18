---
document_id: BAI03-DOCS-README
document_type: documentation-index
project_id: BAI03-SALES-AI
status: CANONICAL
language: vi
last_reviewed: 2026-08-18
---

# Chỉ mục tài liệu chuẩn hóa — BAI03-SALES-AI

Thư mục này là lớp “nguồn tra cứu” được biên tập từ yêu cầu gốc, DOCX đã sinh,
prompt và mã nguồn. Mục tiêu là giúp AI hoặc người mới phân biệt rõ: yêu cầu
phải làm, tính năng đã có, đề xuất thiết kế và tài liệu mẫu.

## Đọc theo câu hỏi

| Câu hỏi | Đọc file |
|---|---|
| Dự án này là gì, phạm vi nào? | [`00-project-context.md`](00-project-context.md) |
| Cần làm những chức năng nào? | [`01-requirements-summary.md`](01-requirements-summary.md) |
| Chức năng nào đã có trong code? | [`02-architecture-and-code-status.md`](02-architecture-and-code-status.md) |
| Quy trình bán hàng và bất biến dữ liệu ra sao? | [`03-business-flows.md`](03-business-flows.md) |
| AI được phép làm gì, dữ liệu vào/ra thế nào? | [`04-ai-specification.md`](04-ai-specification.md) |
| Cần nộp và kiểm chứng những gì? | [`05-deliverables-and-validation.md`](05-deliverables-and-validation.md) |
| Còn mâu thuẫn hoặc quyết định mở nào? | [`06-open-questions.md`](06-open-questions.md) |
| Một thông tin đến từ đâu, có đáng tin không? | [`99-source-register.md`](99-source-register.md) |
| GitNexus và RAG được vận hành thế nào? | [`07-knowledge-retrieval.md`](07-knowledge-retrieval.md) |
| Chuẩn Word, bìa, độ dài, source-of-truth và hồ sơ nộp? | [`08-documentation-standard.md`](08-documentation-standard.md) |
| Cần đọc bằng máy theo danh sách nào? | [`manifest.yaml`](manifest.yaml) |

## Quy ước trạng thái nguồn

| Nhãn | Ý nghĩa |
|---|---|
| `CANONICAL` | Nguồn yêu cầu/định danh được ưu tiên trong phạm vi dự án |
| `IMPLEMENTED` | Đã xác minh trực tiếp trong mã nguồn; chưa mặc định là đã đạt mọi test |
| `DERIVED` | Nội dung được tổng hợp hoặc suy ra từ nguồn khác |
| `PROPOSED` | Thiết kế/giải pháp đề xuất, chưa phải hiện trạng |
| `OPEN` | Chưa có quyết định hoặc bằng chứng đủ chắc chắn |
| `TEMPLATE` | Mẫu dùng để sinh tài liệu, không phải sự thật dự án |
| `REFERENCE` | Tài liệu học tập/tham khảo bên ngoài phạm vi triển khai |
| `LEGACY` | Bản cũ, chỉ dùng để đối chiếu lịch sử |

## Cách trả lời khi tra cứu

1. Xác định `project_id` và `document_id` trước khi dùng thông tin.
2. Ưu tiên `project.md`, `informember.md`, sau đó đối chiếu mã nguồn.
3. Với mỗi kết luận về triển khai, nêu đường dẫn file và trạng thái.
4. Nếu có xung đột, dùng [`06-open-questions.md`](06-open-questions.md), không
   tự gộp hai phiên bản thành một sự thật.
5. Không coi các con số mục tiêu như tốc độ, độ chính xác AI hoặc uptime là
   số đo đã đạt nếu chưa có kết quả kiểm thử/đo lường.

## Nguồn gốc và phạm vi

Danh mục đầy đủ nằm trong [`99-source-register.md`](99-source-register.md).
Các file sinh ra, virtual environment, database local và secret bị loại khỏi
chỉ mục theo [`manifest.yaml`](manifest.yaml). Báo cáo nộp dùng DOCX/PDF để
đọc/in, còn Markdown/YAML trong `docs/` là lớp canonical cho Git và RAG; hai
lớp này phải trỏ về cùng một version nội dung.
