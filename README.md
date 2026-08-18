---
document_id: AIA331-README
document_type: project-index
project_id: AIA331-80300-MARKETING-AI
project_title: Hệ thống quản lý chiến dịch marketing có tích hợp AI
priority: P1
priority_level: HIGH
status: CANONICAL
language: vi
last_reviewed: 2026-08-18
---

# AIA331-80300-MARKETING-AI

## Hệ thống quản lý chiến dịch marketing có tích hợp AI

Hai ảnh `source-materials/BÀI KIỂM TRA.png` và
`source-materials/DỰ ÁN.png` là nguồn P0 / CRITICAL do người dùng cung cấp.
Ảnh **BÀI KIỂM TRA** quy định 10 tiêu chí đánh giá; ảnh **DỰ ÁN** quy định tên
đề tài chính thức của học phần **Ứng dụng trí tuệ nhân tạo - AIA331**, mã
**80300**, hình thức **Dự án**. Repo này dùng chúng làm source-of-truth; không
trộn với dự án quản lý bán hàng trước đó.

Phân cấp đầy đủ được ghi tại [`docs/10-priority-policy.md`](docs/10-priority-policy.md):
chỉ hai ảnh là P0; hồ sơ, checklist, baseline và test là P1; tài liệu hỗ trợ và
prompt là P2; các dự án bán hàng cũ là LEGACY.

## Đọc nhanh

1. Đọc [`project.md`](project.md) để biết yêu cầu gốc và ID yêu cầu.
2. Đọc [`docs/00-project-context.md`](docs/00-project-context.md) để biết phạm vi,
   nhóm và quy tắc suy luận.
3. Tra chức năng trong [`docs/01-requirements-summary.md`](docs/01-requirements-summary.md).
4. Đối chiếu code và trạng thái trong [`docs/02-architecture-and-code-status.md`](docs/02-architecture-and-code-status.md).
5. Xem AI contract/prompt tại [`docs/04-ai-specification.md`](docs/04-ai-specification.md).
6. Xem hồ sơ nộp tại [`submission/Nhom25/README_NHOM25.md`](submission/Nhom25/README_NHOM25.md).
7. Xem cấp ưu tiên và bản đồ thư mục tại [`docs/10-priority-policy.md`](docs/10-priority-policy.md).
8. Dùng [`docs/11-rag-implementation.md`](docs/11-rag-implementation.md) để
   build/truy hồi corpus tài liệu; dùng GitNexus riêng cho code graph.

## Chạy baseline

```powershell
cd marketing_management
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py createsuperuser
python manage.py runserver
```

Mở `http://127.0.0.1:8000/`. Provider mặc định là fallback offline; cấu hình
provider ngoài chỉ qua `.env` theo `marketing_management/.env.example`.

## Thông tin nhóm

- Nhóm 25 — lớp CNTTK23C.
- Nguyễn Hải Đăng — `dtc2451200051`.
- Vũ Hiếu Kiên — `dtc245200244`.
- Trường Đại học Công nghệ Thông tin và Truyền thông Thái Nguyên.
- Khoa Công nghệ thông tin.

## Cấu trúc nguồn

| Đường dẫn | Vai trò |
|---|---|
| `project.md` | Yêu cầu gốc, `CANONICAL` |
| `docs/` | Tài liệu đã chuẩn hóa cho AI/người đọc |
| `docs/rag-corpus.json` và `tools/rag_index.py` | Manifest + RAG local có citation; database `.rag/` sinh lại được |
| `marketing_management/` | Baseline Django marketing, `IMPLEMENTED_BASELINE` |
| `prompts/` | Prompt/minh chứng theo đề tài marketing |
| `submission/Nhom25/` | Hồ sơ nộp được sinh từ nguồn canonical |
| `source-materials/` | Hai nguồn P0 / CRITICAL, không chỉnh nội dung |
| `Slide_PDF/` và các file học tập ở root | Tài liệu tham khảo, không phải source-of-truth |
| `submission/legacy-sales/`, `Code QLBH/`, `sales_management/` và các nhánh bán hàng cũ | `LEGACY`, không phải source của đề tài |

## Quy tắc trạng thái

`CANONICAL` là yêu cầu chính thức; `IMPLEMENTED_BASELINE` là phần đã có code/test;
`DERIVED` là nội dung suy ra; `PROPOSED` là thiết kế chưa triển khai; `OPEN` là
điểm cần chốt; `LEGACY` chỉ để giữ lịch sử. Không gọi mục tiêu hoặc prompt mẫu
là bằng chứng nghiệm thu.
