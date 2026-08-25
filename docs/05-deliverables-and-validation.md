---
document_id: AIA331-DOC-05
document_type: deliverables-and-validation
project_id: AIA331-80300-MARKETING-AI
priority: P1
priority_level: HIGH
status: DERIVED
last_reviewed: 2026-08-25
---

# Hồ sơ cần nộp và cổng kiểm chứng

## 1. Gói nộp cho thầy

Theo hướng dẫn Google Classroom đã cung cấp: cho toàn bộ nội dung báo cáo và
file liên quan vào một thư mục tên nhóm, ví dụ `Nhom25`, sau đó nén thành ZIP.

Gói chuẩn của nhóm gồm:

1. Báo cáo phân tích/thiết kế LaTeX (`.tex`).
2. Bản PDF A4 sinh từ LaTeX để xem/in.
3. Markdown canonical để AI tra cứu.
4. Phụ lục prompt và minh chứng dùng AI.
5. Sơ đồ use case, ERD, kiến trúc và biểu đồ metric.
6. Mã nguồn baseline và `.env.example` (không có `.env`, database, cache).
7. Hai ảnh nguồn P0 / CRITICAL: `source-materials/BÀI KIỂM TRA.png` và
   `source-materials/DỰ ÁN.png`.
8. `evidence/ai/` chứa phản hồi JSON redacted và bảng kiểm chứng/chỉnh sửa.
9. Bản dựng đã kiểm tra grayscale/print-safe; logo và màu nhấn chỉ dùng để tăng
   nhận diện, không làm mất thông tin khi in đen trắng.

## 2. Cổng chất lượng

| Gate | Phải chứng minh |
|---|---|
| Gate A — Phân tích | Bối cảnh, actor, FR/NFR/BR, use case, ERD, vị trí AI |
| Gate B — Baseline | Migration, `manage.py check`, test, seed, CRUD chiến dịch |
| Gate C — AI | Prompt version, provider/fallback, output contract, approval gate |
| Gate D — Hồ sơ | LaTeX/PDF render ổn, ZIP đúng cấu trúc, không secret, checksum |
| Gate E — RAG | Corpus validate, citation, evaluator đạt ngưỡng, không truy hồi legacy |
| Gate F — Print-safe | PDF A4 và ảnh/sơ đồ đọc được ở grayscale; không phụ thuộc màu |
| Gate G — Bài 2 | Đủ 10 tiêu chí triển khai, test CRUD/filter/dashboard/RBAC và hướng dẫn chạy |

## 3. Lệnh kiểm tra

```powershell
cd marketing_management
.venv\Scripts\python.exe manage.py check
.venv\Scripts\python.exe manage.py test campaigns -v 1
.venv\Scripts\python.exe manage.py migrate --check

cd ..
python tools/rag_index.py validate
python tools/rag_index.py build
python tools/rag_eval.py --top-k 5
python -m unittest tools.test_rag_index -v
python -m unittest tools.test_rag_eval -v
```

## 4. Trạng thái bằng chứng hiện tại

- Test baseline: `IMPLEMENTED_BASELINE` — 25 test cho model, RBAC, CRUD,
  filter/dashboard, report theo ngày/kênh, phân trang, metric entry,
  approval/rejection, AI fallback và provider contract.
- Bài kiểm tra thường xuyên 2: `IMPLEMENTED_BASELINE` — ma trận đối chiếu chi tiết
  ở `docs/13-bai-2-implementation.md`.
- System check: `IMPLEMENTED_BASELINE` — không có lỗi tại lần kiểm tra gần nhất.
- Provider ngoài: `PROPOSED/OPTIONAL` — cần key và test tích hợp riêng.
- Độ chính xác AI: `OPEN` — chưa có bộ chấm định lượng, không được tự ghi điểm.
- RAG tài liệu: `IMPLEMENTED_BASELINE` — index local có allowlist, citation,
  evaluator 9 câu hỏi đạt hit-rate tối thiểu 0.90 và không có forbidden hit;
  `.rag/` là artifact sinh lại được, không đưa vào ZIP nộp.
- Hình/bảng báo cáo: `IMPLEMENTED_BASELINE` — Use Case, ERD có User/approved_by,
  architecture có RAG/approval và biểu đồ metric minh họa; PNG được chèn vào LaTeX/PDF.
- Print-safe: `IMPLEMENTED_BASELINE` — palette tiết chế, chart/sơ đồ có nhãn và
  kiểm tra render grayscale trước khi đóng gói.
