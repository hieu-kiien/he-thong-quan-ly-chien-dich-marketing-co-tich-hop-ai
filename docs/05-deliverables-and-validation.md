---
document_id: BAI03-DOC-05
document_type: deliverables-and-validation
project_id: BAI03-SALES-AI
status: DERIVED
authority: project-plan-and-rubric
sources:
  - ../project.md
  - ../../../Bai 02/CacGiaiDoanThucHien/01_GenAI_SoftwareDevelopment_project-plan.docx
  - 01-requirements-summary.md
last_reviewed: 2026-08-18
---

# Sản phẩm bàn giao và cổng kiểm chứng

## 1. Bốn mốc học tập/nghiệm thu

| Mốc | Phạm vi | Sản phẩm cần có | Không được nhầm với |
|---|---|---|---|
| KT1 / tuần 4 | Phân tích và thiết kế | context, actor/use case, FR/NFR/BR, ERD, flow, vị trí AI | Tài liệu DOCX tự sinh không chứng minh code |
| KT2 / tuần 6 | Chức năng quản lý | model/schema, auth/RBAC, CRUD chính, tồn kho, tìm kiếm | Skeleton app chưa phải CRUD hoàn chỉnh |
| KT3 / tuần 8 | AI và kiểm thử | provider/adapter, prompt version, fallback, test AI + quản lý | `AIEventLog` đơn lẻ chưa phải integration |
| Cuối kỳ / tuần 9 | Hoàn thiện và trình bày | README, `.env.example`, dữ liệu mẫu, demo, report, slide, review | Kế hoạch mục tiêu chưa phải kết quả đo |

Kế hoạch DOCX ghi lịch 27/07/2026–27/09/2026; đây là lịch suy ra từ tài liệu
đã sinh và cần được nhóm/giảng viên xác nhận nếu dùng làm lịch chính thức.

## 2. Cổng chất lượng theo giai đoạn

### Gate A — Phân tích

- Mỗi FR/NFR/BR có ID, actor, input, xử lý, output và acceptance criteria.
- Actor/role không mâu thuẫn; schema có PK/FK/unique/check cần thiết.
- Tách rõ business rule với việc AI chỉ hỗ trợ.

### Gate B — Chức năng quản lý

- Chạy được migration và `manage.py check` trên baseline đã chọn.
- Có dữ liệu mẫu và route/view cho chức năng công bố là hoàn thành.
- Test các bất biến tồn kho, hóa đơn, quyền và validation.

### Gate C — AI

- Provider được cấu hình qua `.env`, có `.env.example`, không secret trong git.
- Có version prompt, schema input/output, timeout, fallback, audit/redaction.
- Test grounding, hết hàng, PII, injection, timeout và output sai schema.

### Gate D — Bàn giao

- README chạy được từ môi trường sạch.
- Có kịch bản demo tái lập, ảnh/log hoặc test report làm bằng chứng.
- Tài liệu chỉ dùng `IMPLEMENTED` khi có file/mã/test tương ứng.
- Mọi mục tiêu hiệu năng/accuracy/uptime có phương pháp đo và kết quả.

## 3. Nhóm rubric 40 tiêu chí

| Nhóm | Tiêu chí chính |
|---|---|
| 1–10 | Chức năng, AI integration, phân tích, cấu trúc, code, API key, FR, auth/RBAC, DB, prompt |
| 11–20 | NFR, CRUD, UX, prompt iteration, actor/use case, search/filter, chất lượng AI, dữ liệu vào AI, ERD, report |
| 21–30 | Bảo mật/đạo đức, hiển thị AI, kiến trúc, UX, hiệu năng, xử lý lỗi AI, vị trí AI, CSDL, deploy, test |
| 31–40 | Prompt contract, lỗi cơ bản, báo cáo, code review, minh chứng dùng AI trong phân tích/lập trình, demo, trải nghiệm AI, tài liệu, quản lý mã nguồn |

Danh sách diễn giải đầy đủ 40 mục nằm ở phần cuối
[`project.md`](../project.md). Bảng này là chỉ mục, không thay thế rubric gốc.

## 4. Mẫu bằng chứng nên lưu

```text
evidence/
  kt1/requirements-coverage.md
  kt1/erd-and-flows.png
  kt2/test-report.txt
  kt2/demo-data.json
  kt3/prompts/ai-001-v001.md
  kt3/prompts/ai-001-v002.md
  kt3/evaluation/summary.csv
  final/runbook.md
  final/screenshots/
```

Thư mục trên là đề xuất; không tạo file bằng chứng giả. Mỗi bằng chứng nên ghi
ngày, commit/version, lệnh chạy, kết quả và người kiểm tra.

## 5. Chuẩn hồ sơ tài liệu

Áp dụng [`08-documentation-standard.md`](08-documentation-standard.md) cho
mọi bản nộp BAI03:

- DOCX/PDF là lớp trình bày cho giảng viên; Markdown/YAML là lớp canonical cho
  Git, AI và RAG.
- Báo cáo phân tích và thiết kế dùng một bìa, mục lục tự động, phần nội dung
  chính khoảng 25–40 trang và phụ lục cho prompt/bằng chứng dài.
- Khi không có mẫu riêng của giảng viên, dùng baseline A4, Times New Roman
  13 pt, lề trái 3,5 cm/phải 2 cm/trên-dưới 2,5 cm, Multiple 1,3 và Before/
  After 6 pt.
- Không coi mục tiêu, prompt template, model-only, schema-only hoặc
  `PROPOSED/OPEN` là kết quả nghiệm thu.
