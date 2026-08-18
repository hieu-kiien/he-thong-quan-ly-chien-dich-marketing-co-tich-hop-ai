---
document_id: AIA331-DOC-05
document_type: deliverables-and-validation
project_id: AIA331-80300-MARKETING-AI
priority: P1
status: DERIVED
last_reviewed: 2026-08-18
---

# Hồ sơ cần nộp và cổng kiểm chứng

## 1. Gói nộp cho thầy

Theo hướng dẫn Google Classroom đã cung cấp: cho toàn bộ nội dung báo cáo và
file liên quan vào một thư mục tên nhóm, ví dụ `Nhom25`, sau đó nén thành ZIP.

Gói chuẩn của nhóm gồm:

1. Báo cáo phân tích/thiết kế DOCX.
2. Bản PDF để xem/in.
3. Markdown canonical để AI tra cứu.
4. Phụ lục prompt và minh chứng dùng AI.
5. Sơ đồ use case, ERD, kiến trúc.
6. Mã nguồn baseline và `.env.example` (không có `.env`, database, cache).

## 2. Cổng chất lượng

| Gate | Phải chứng minh |
|---|---|
| Gate A — Phân tích | Bối cảnh, actor, FR/NFR/BR, use case, ERD, vị trí AI |
| Gate B — Baseline | Migration, `manage.py check`, test, seed, CRUD chiến dịch |
| Gate C — AI | Prompt version, provider/fallback, output contract, approval gate |
| Gate D — Hồ sơ | DOCX/PDF render ổn, ZIP đúng cấu trúc, không secret, checksum |

## 3. Lệnh kiểm tra

```powershell
cd marketing_management
.venv\Scripts\python.exe manage.py check
.venv\Scripts\python.exe manage.py test campaigns -v 1
.venv\Scripts\python.exe manage.py migrate --check
```

## 4. Trạng thái bằng chứng hiện tại

- Test baseline: `IMPLEMENTED_BASELINE` — 4 test cho model, approval, AI fallback,
  campaign list.
- System check: `IMPLEMENTED_BASELINE` — không có lỗi tại lần kiểm tra gần nhất.
- Provider ngoài: `PROPOSED/OPTIONAL` — cần key và test tích hợp riêng.
- Độ chính xác AI: `OPEN` — chưa có bộ chấm định lượng, không được tự ghi điểm.
