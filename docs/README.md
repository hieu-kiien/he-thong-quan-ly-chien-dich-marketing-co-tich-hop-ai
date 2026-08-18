---
document_id: AIA331-DOCS-README
document_type: documentation-index
project_id: AIA331-80300-MARKETING-AI
priority: P0
priority_level: CRITICAL
status: CANONICAL
language: vi
last_reviewed: 2026-08-18
---

# Chỉ mục tài liệu chuẩn hóa — Marketing AI

## Đọc theo câu hỏi

| Câu hỏi | Tài liệu |
|---|---|
| Đề tài chính thức là gì? | [`../project.md`](../project.md) |
| Bối cảnh, nhóm và phạm vi? | [`00-project-context.md`](00-project-context.md) |
| Những chức năng nào phải có? | [`01-requirements-summary.md`](01-requirements-summary.md) |
| Code đã có gì, thiếu gì? | [`02-architecture-and-code-status.md`](02-architecture-and-code-status.md) |
| Luồng nghiệp vụ và bất biến? | [`03-business-flows.md`](03-business-flows.md) |
| AI input/output/prompt/safety? | [`04-ai-specification.md`](04-ai-specification.md) |
| Cần nộp và kiểm tra gì? | [`05-deliverables-and-validation.md`](05-deliverables-and-validation.md) |
| Điểm nào còn mở? | [`06-open-questions.md`](06-open-questions.md) |
| RAG/GitNexus dùng thế nào? | [`07-knowledge-retrieval.md`](07-knowledge-retrieval.md) |
| Chuẩn Word/PDF/bìa? | [`08-documentation-standard.md`](08-documentation-standard.md) |
| Nguồn nào đáng tin? | [`99-source-register.md`](99-source-register.md) |
| 10 tiêu chí bài kiểm tra? | [`09-assessment-checklist.md`](09-assessment-checklist.md) |

## Trạng thái

`CANONICAL` = yêu cầu/định danh chính thức; `IMPLEMENTED_BASELINE` = đã có code
và test trong baseline; `DERIVED` = biên tập từ nguồn; `PROPOSED` = thiết kế
chưa triển khai; `OPEN` = cần quyết định; `REFERENCE` = tham khảo;
`LEGACY` = lịch sử, không dùng làm nguồn của đề tài.

## Quy tắc trả lời cho AI

Luôn xác định `project_id` trước khi trả lời. Ưu tiên hai ảnh P0 / CRITICAL trong
`source-materials/`, rồi `project.md` và nhóm `docs/`, sau đó code/test. Khi chưa
có bằng chứng, dùng “chưa được chứng minh”;
không biến mục tiêu hoặc prompt mẫu thành kết quả đã đạt. Các tệp bán hàng cũ
không thuộc corpus canonical.
