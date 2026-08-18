---
document_id: AIA331-DOC-07
document_type: knowledge-retrieval-guide
project_id: AIA331-80300-MARKETING-AI
status: DERIVED
last_reviewed: 2026-08-18
---

# GitNexus và RAG cho tra cứu dự án

## 1. Corpus canonical

Ưu tiên index P0 / CRITICAL: `source-materials/BÀI KIỂM TRA.png`,
`source-materials/DỰ ÁN.png`, sau đó `project.md`, `informember.md`,
`docs/*.md`, `marketing_management/**/*.py`, prompt và
`submission/Nhom25/*.md`. Loại khỏi corpus canonical: `.venv`, `.env`, database,
cache, `.gitnexus`, notebook checkpoint và toàn bộ nội dung bán hàng legacy.

## 2. GitNexus

GitNexus phù hợp để truy vết symbol, module, execution flow và impact của code.
Nó không thay thế `project.md` và không phải vector RAG cho tài liệu nghiệp vụ.
Sau khi code đổi, chạy lại analyze/index; trước commit kiểm tra thay đổi symbol
và flow nếu CLI khả dụng.

## 3. RAG tài liệu

Pipeline đề xuất:

```text
canonical Markdown + code
  -> lọc trạng thái/path
  -> chunk theo heading, giữ document_id/project_id/status
  -> embedding + vector store local
  -> retrieve top-k có metadata filter
  -> câu trả lời có citation file/section
```

Metadata tối thiểu: `project_id`, `document_id`, `status`, `source`, `path`,
`last_reviewed`. Truy hồi không được trộn `LEGACY` với `CANONICAL` nếu câu hỏi
liên quan yêu cầu chính thức.

## 4. Quy tắc citation

Mỗi kết luận về code phải trỏ tới file; mỗi kết luận về yêu cầu phải trỏ tới
`project.md` hoặc `docs/01-requirements-summary.md`; mỗi kết luận về nhóm phải
trỏ tới `informember.md`. Nếu không có bằng chứng, ghi `OPEN`.
