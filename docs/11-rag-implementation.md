---
document_id: AIA331-DOC-11
document_type: rag-implementation-and-operations
project_id: AIA331-80300-MARKETING-AI
priority: P1
priority_level: HIGH
status: IMPLEMENTED_BASELINE
last_reviewed: 2026-08-18
---

# RAG tài liệu canonical — hướng dẫn vận hành

## 1. Quyết định kiến trúc

Repo tách hai nhiệm vụ để tránh tra cứu chậm và lẫn đề tài:

| Nhiệm vụ | Công cụ | Phạm vi |
|---|---|---|
| Truy vết symbol, caller/callee, execution flow và impact | GitNexus | Mã nguồn baseline và công cụ RAG đang dùng |
| Tra cứu yêu cầu, nhóm, checklist, prompt và hồ sơ | SQLite FTS5 RAG | Corpus được allowlist trong `docs/rag-corpus.json` |

GitNexus không còn được dùng như kho hỏi đáp tài liệu. Các thư mục legacy bán
hàng, prompt bài cũ, notebook, slide và bộ sinh báo cáo đã được loại khỏi
`.gitnexusignore`. Hai ảnh P0 vẫn là nguồn authority; RAG lưu chúng trong bảng
`authority_assets` và trỏ các bản Markdown diễn giải về đúng ảnh nguồn.

## 2. Corpus và hợp đồng truy hồi

Manifest máy đọc là [`docs/rag-corpus.json`](rag-corpus.json). Mỗi chunk giữ:

- `project_id`, `document_id`, `status`, `priority`, `priority_level`;
- đường dẫn tương đối, tiêu đề section và dòng bắt đầu/kết thúc;
- `authority_paths` nếu chunk được diễn giải từ nguồn P0;
- `citation`, `snippet` và toàn bộ `content`.

Index mặc định chỉ chứa đề tài `AIA331-80300-MARKETING-AI`; không đưa
`LEGACY` hoặc `REFERENCE` vào corpus mặc định. Database nằm ở
`.rag/marketing-rag.sqlite3`, là artifact sinh lại được và không commit.

## 3. Lệnh vận hành

Chạy từ thư mục gốc repo:

```powershell
python tools/rag_index.py validate
python tools/rag_index.py build
python tools/rag_index.py search "tên đề tài chính thức chiến dịch marketing" --top-k 5
python -m unittest tools.test_rag_index -v
```

Nếu máy không có Python trong PATH, dùng Python bundled của môi trường Codex
hoặc Python 3.10+ có SQLite FTS5. `build` phải chạy lại sau khi thay đổi
`project.md`, `docs/`, `marketing_management/`, `prompts/marketing/` hoặc hồ sơ
canonical.

## 4. Kiểm soát chất lượng

Baseline hiện tại kiểm tra được: đủ hai ảnh P0, không có đường dẫn legacy trong
allowlist, citation có file/section/dòng, kết quả có metadata ưu tiên và ID
chunk ổn định qua hai lần build. Corpus lần build ngày 18/08/2026 gồm 48 nguồn
và 160 chunk.

Đây là lexical RAG có xếp hạng theo BM25 + ưu tiên nguồn, chưa phải semantic
embedding. Cách này được chọn vì môi trường hiện có SQLite FTS5 nhưng không có
`chromadb`/`sentence-transformers`, đồng thời dễ kiểm chứng citation. Chỉ thêm
embedding khi bộ đánh giá truy hồi chứng minh lexical RAG chưa đủ; không thêm
dependency nặng chỉ để làm index khó kiểm soát.

Ảnh P0 chưa bị OCR tự động trong baseline. Nội dung diễn giải dùng
`project.md` và `docs/09-assessment-checklist.md`, nhưng câu trả lời vẫn phải
hiển thị `authority_paths` để người đọc đối chiếu ảnh gốc khi cần.

## 5. Quy tắc sử dụng cho AI

1. Câu hỏi về yêu cầu, tên đề tài, tiêu chí hoặc nhóm: dùng RAG trước.
2. Câu hỏi về code, luồng chạy hoặc blast radius: dùng GitNexus trước.
3. Nếu hai nguồn mâu thuẫn, P0 thắng; ghi `OPEN` và dẫn citation thay vì tự
   hợp nhất.
4. Không coi chunk `PROPOSED` là bằng chứng đã triển khai.
