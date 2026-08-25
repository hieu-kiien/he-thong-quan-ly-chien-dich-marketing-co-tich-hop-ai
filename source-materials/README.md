---
document_id: AIA331-SOURCE-MATERIALS
document_type: canonical-source-index
project_id: AIA331-80300-MARKETING-AI
priority: P0
priority_level: CRITICAL
status: CANONICAL
last_reviewed: 2026-08-19
---

# Kho nguồn P0 / CRITICAL

Hai ảnh dưới đây là nguồn người dùng cung cấp và phải được ưu tiên cao nhất khi
đọc, tra cứu, phân tích hoặc kiểm tra tính đầy đủ của hồ sơ:

| File | Vai trò | Authority |
|---|---|---|
| `BÀI KIỂM TRA.png` | 10 tiêu chí đánh giá bài kiểm tra: phân tích, FR/NFR, use case, CSDL, kiến trúc, AI, prompt, minh chứng và tài liệu | P0 / CRITICAL |
| `DỰ ÁN.png` | Tên đề tài, học phần, mã số, mục tiêu, chức năng, kỹ thuật và mức độ khó | P0 / CRITICAL |

## Kiểm tra toàn vẹn

`python tools/rag_index.py validate` kiểm tra cả sự tồn tại và SHA-256 của hai
ảnh. Nếu checksum lệch, nguồn P0 bị coi là không hợp lệ và không được build RAG.

- `BÀI KIỂM TRA.png`: `d12f72d01eff51649108c867e0e30d74d445daebf36360bcddfa1460666957fd`
- `DỰ ÁN.png`: `6c4fe9441baf80ba5cb574357b3295c37ef032b2799bec7e7ba0d150264ad7e3`

Các bản Markdown trong `project.md` và `docs/` là bản chép/biên tập có truy vết,
không thay thế hai ảnh nguồn. Khi có xung đột, ưu tiên ảnh và ghi lại xung đột
trong `docs/06-open-questions.md`.
