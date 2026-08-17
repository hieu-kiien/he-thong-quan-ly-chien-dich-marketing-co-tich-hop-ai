---
document_id: BAI03-DOC-99
document_type: source-register
project_id: BAI03-SALES-AI
status: CANONICAL
language: vi
last_reviewed: 2026-08-17
---

# Sổ đăng ký nguồn tài liệu và mã nguồn

`authority` chỉ mức ưu tiên trong phạm vi `project_id`; `status` mô tả cách
dùng nguồn, không phải đánh giá chất lượng tuyệt đối.

## Nguồn chính của BAI03-SALES-AI

| ID | Đường dẫn | Loại | Status | Dùng để |
|---|---|---|---|---|
| SRC-001 | [`project.md`](../project.md) | Project brief + rubric | `CANONICAL` | Bối cảnh, mục tiêu, FR, AI scope, tiêu chí chấm |
| SRC-002 | [`informember.md`](../informember.md) | Team metadata | `CANONICAL` | Tên nhóm, lớp, trường; vai trò Mai cần xác nhận với bản Bài 02 |
| SRC-003 | [`ContextProject.md`](../ContextProject.md) | Coding context | `DERIVED` | Định hướng Django, module, coding convention |
| SRC-004 | [`Code QLBH/`](<../Code QLBH/>) | Django scaffold | `IMPLEMENTED` | Kiến trúc module; nhiều phần còn skeleton |
| SRC-005 | [`Code QLBH/docs/architecture/codebase-blueprint.md`](<../Code QLBH/docs/architecture/codebase-blueprint.md>) | Architecture note | `DERIVED` | Nguyên tắc view → service → selector → model |
| SRC-006 | [`sales_management/`](<../sales_management/>) | Django implementation branch | `IMPLEMENTED` | Model nghiệp vụ và CRUD danh mục đã kiểm tra tĩnh |
| SRC-007 | [`docs/`](.) | Curated documentation layer | `DERIVED` | Tra cứu có ID, trạng thái và ma trận đối chiếu |
| SRC-008 | [`sales_management/apps/knowledge/`](<../sales_management/apps/knowledge/>) | Document retrieval app | `IMPLEMENTED` | Index tài liệu có metadata, embedding và context trích dẫn |
| SRC-009 | [`docs/07-knowledge-retrieval.md`](07-knowledge-retrieval.md) | RAG operating contract | `DERIVED` | Cách index, truy vấn và giới hạn của lớp truy hồi |

## Nguồn cùng miền nhưng cũ hơn hoặc chỉ là đầu vào

| ID | Đường dẫn | Status | Cách sử dụng |
|---|---|---|---|
| SRC-010 | [`Bai 02/CacGiaiDoanThucHien/project.md`](<../../../Bai 02/CacGiaiDoanThucHien/project.md>) | `CANONICAL` trong baseline BAI02 | Brief sớm hơn, cùng đề tài bán hàng; dùng để đối chiếu tiến trình, không thay thế nguồn Bài 03 |
| SRC-011 | [`Bai 02/CacGiaiDoanThucHien/informember.md`](<../../../Bai 02/CacGiaiDoanThucHien/informember.md>) | `CANONICAL` trong baseline BAI02 | Bản nhóm cũ; vai trò của Mai khác SRC-002, cần xác nhận |
| SRC-012 | [`Bai 02/CacGiaiDoanThucHien/01. project-plan.md`](<../../../Bai 02/CacGiaiDoanThucHien/01.%20project-plan.md>) | `DERIVED` prompt | Prompt sinh kế hoạch; không phải kế hoạch đã đo/đạt |
| SRC-013 | [`Bai 02/CacGiaiDoanThucHien/02 requirements-qa.md`](<../../../Bai 02/CacGiaiDoanThucHien/02%20requirements-qa.md>) | `DERIVED` prompt | Prompt sinh tài liệu BA |
| SRC-014 | `Bai 02/CacGiaiDoanThucHien/01–07_*.docx` | `DERIVED` generated | Kết quả diễn giải; một số file còn template, không dùng làm bằng chứng chạy code |
| SRC-015 | [`Mau/`](<../../../Mau/>) | `TEMPLATE` | Mẫu môn học, không phải dữ liệu dự án |

## Pipeline BAI02 mới bổ sung

| ID | Đường dẫn | Status | Cách sử dụng |
|---|---|---|---|
| SRC-016 | [`Bai 02/CacGiaiDoanThucHien/project.md`](<../../Bai%2002/CacGiaiDoanThucHien/project.md>) | `REFERENCE` | Brief và quy trình SDLC đầu vào; không thay thế brief BAI03 |
| SRC-017 | [`Bai 02/CacGiaiDoanThucHien/informember.md`](<../../Bai%2002/CacGiaiDoanThucHien/informember.md>) | `REFERENCE` | Thông tin nhóm từ pipeline Bài 02 để đối chiếu |
| SRC-018 | [`Bai 02/CacGiaiDoanThucHien/`](<../../Bai%2002/CacGiaiDoanThucHien/>) | `REFERENCE` | Prompt và DOCX theo các giai đoạn plan → requirements → design → test → guide |
| SRC-019 | [`Bai 02/CacGiaiDoanThucHien/BK/`](<../../Bai%2002/CacGiaiDoanThucHien/BK/>) | `TEMPLATE` | Bản sao lưu; loại khỏi chỉ mục tự động |

## Nguồn độc lập hoặc tham khảo

| ID | Đường dẫn | Status | Ghi chú |
|---|---|---|---|
| SRC-020 | [`KT1_PHAN_TICH_THIET_KE.md`](<../../../KT1_PHAN_TICH_THIET_KE.md>) | `LEGACY`/separate | Dự án `BAOHANHAI`; không trộn actor, schema hoặc workflow vào bán hàng |
| SRC-021 | [`QLBH demo/`](<../../QLBH%20demo/>) | `LEGACY` | Bản demo cũ; có lỗi thiết kế/bảo mật và không phải baseline |
| SRC-022 | [`Slide_PDF/`](<../../../Slide_PDF/>) | `REFERENCE` | Tài liệu bài giảng AI, không phải đặc tả sản phẩm |
| SRC-023 | [`Bài giảng DJANGO.docx`](<../../../Bài giảng DJANGO.docx>) | `REFERENCE` | Tài liệu học Django |
| SRC-024 | [`legacy-prime-number-utilities.md`](legacy-prime-number-utilities.md) | `LEGACY` | README cũ không liên quan, đã tách khỏi README dự án |

## Nguyên tắc loại trừ

Không lập chỉ mục `.venv/`, `venv/`, `__pycache__/`, `.pytest_cache/`,
`.ipynb_checkpoints/`, `.venv-rag/`, `.gitnexus/`, `knowledge_store/`,
`db.sqlite3`, file `.env`, file biên dịch và cache. Không đọc hoặc sao chép secret
chỉ để làm tài liệu.
