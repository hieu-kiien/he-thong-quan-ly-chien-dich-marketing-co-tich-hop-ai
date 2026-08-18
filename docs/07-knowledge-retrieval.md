---
document_id: AIA331-DOC-07
document_type: knowledge-retrieval-guide
project_id: AIA331-80300-MARKETING-AI
priority: P2
priority_level: MEDIUM
status: DERIVED
last_reviewed: 2026-08-18
---

# GitNexus và RAG cho tra cứu dự án

## 1. Corpus canonical

Ưu tiên kiểm tra P0 / CRITICAL trước: `source-materials/BÀI KIỂM TRA.png`,
`source-materials/DỰ ÁN.png`; sau đó truy hồi các tài liệu P1/P2 có truy vết.
Allowlist thực thi nằm trong [`docs/rag-corpus.json`](rag-corpus.json), thay vì
quét toàn bộ repo. Database sinh ra nằm trong `.rag/` và có thể build lại.

## 2. GitNexus

GitNexus phù hợp để truy vết symbol, module, execution flow và impact của code.
`.gitnexusignore` loại legacy, tài liệu học tập và helper sinh báo cáo khỏi code
graph. GitNexus không thay thế `project.md` và không phải RAG tài liệu nghiệp vụ.
Sau khi code đổi, chạy lại analyze/index; trước commit kiểm tra thay đổi symbol
và flow nếu CLI khả dụng.

## 3. RAG tài liệu

Pipeline đề xuất:

```text
canonical Markdown + code
  -> allowlist theo docs/rag-corpus.json
  -> chunk theo heading/symbol, giữ document_id/project_id/status/priority
  -> SQLite FTS5 local + BM25 và boost theo ưu tiên
  -> retrieve top-k có project/status filter
  -> câu trả lời có citation file/section/dòng và authority P0
```

Metadata tối thiểu: `project_id`, `document_id`, `status`, `source`, `path`,
`last_reviewed`, `priority`, `authority_paths`. Truy hồi không được trộn
`LEGACY` với `CANONICAL` nếu câu hỏi liên quan yêu cầu chính thức. Chi tiết lệnh
và giới hạn baseline nằm ở [`docs/11-rag-implementation.md`](11-rag-implementation.md).

## 4. Quy tắc citation

Mỗi kết luận về code phải trỏ tới file; mỗi kết luận về yêu cầu phải trỏ tới
`project.md` hoặc `docs/01-requirements-summary.md`; mỗi kết luận về nhóm phải
trỏ tới `informember.md`. Nếu không có bằng chứng, ghi `OPEN`.
