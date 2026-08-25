---
document_id: AIA331-SUBMISSION-INDEX
project_id: AIA331-80300-MARKETING-AI
project_title: Hệ thống quản lý chiến dịch marketing có tích hợp AI
priority: P1
priority_level: HIGH
status: SUBMISSION_CANONICAL
version: 1.0
last_reviewed: 2026-08-25
---

# Hồ sơ nộp — Nhóm 25

## Thông tin

- **Học phần:** Ứng dụng trí tuệ nhân tạo - AIA331.
- **Mã số:** 80300; **hình thức:** Dự án.
- **Đề tài:** Hệ thống quản lý chiến dịch marketing có tích hợp AI.
- **Thành viên:** Nguyễn Hải Đăng (`dtc2451200051`); Vũ Hiếu Kiên (`dtc245200244`).
- **Lớp:** CNTTK23C; **Khoa:** Công nghệ thông tin.
- **Trường:** Trường Đại học Công nghệ Thông tin và Truyền thông Thái Nguyên.

## Cách nộp

Đặt toàn bộ file liên quan vào thư mục `Nhom25`, nén thành `Nhom25.zip`, rồi
nộp file ZIP theo hướng dẫn Google Classroom. Gói nộp không chứa `.env`, database
local, virtualenv, cache, vector store hoặc `.gitnexus/`.

## Danh mục

- `Bao_cao_du_an_marketing_ai.tex` — nguồn LaTeX canonical của bản in; biên dịch
  bằng Tectonic/XeLaTeX.
- `Bao_cao_du_an_marketing_ai.pdf` — PDF A4 sinh từ LaTeX, bản xem/in chính.
- `Bao_cao_du_an_marketing_ai.md` — nguồn Markdown để RAG/tra cứu và đối chiếu.
- `Phu_luc_minh_chung_AI.md` — prompt, phản hồi, bảng kiểm chứng, test và giới hạn bằng chứng.
- `docs/13-bai-2-implementation.md` — ma trận 10 tiêu chí Bài 2 và lệnh kiểm tra.
- `evidence/ai/B2-CODE-001-v1-review.md` — nhật ký AI hỗ trợ CRUD, filter, dashboard và kiểm chứng.
- `diagrams/` — logo ICTU tham chiếu, sơ đồ use case, ERD, kiến trúc và biểu đồ metric.
- `evidence/ai/` — JSON phản hồi fallback đã khử dữ liệu và review trước/sau.
- `docs/12-operations-and-backup.md` — yêu cầu sao lưu, phục hồi và vận hành.
- `docs/13-bai-2-implementation.md` — đối chiếu Bài 2: full CRUD, RBAC, lọc/sắp xếp, KPI, lỗi và tài liệu chạy.
- `source/marketing_management/` — mã nguồn baseline và `.env.example`, đã loại
  database local, virtualenv, cache và secret.
- `source-materials/` — bản sao đề bài nếu cần đối chiếu.
  Hai nguồn P0 / CRITICAL là `BÀI KIỂM TRA.png` và `DỰ ÁN.png`.

## Trạng thái trung thực

Báo cáo phân biệt `IMPLEMENTED_BASELINE`, `PROPOSED` và `OPEN`. Chỉ các phần có
file code/test tương ứng mới được gọi là baseline đã kiểm chứng.
