---
document_id: AIA331-B2-IMPLEMENTATION
document_type: implementation-and-verification-checklist
project_id: AIA331-80300-MARKETING-AI
priority: P0
priority_level: CRITICAL
status: IMPLEMENTED_BASELINE
source: ../source-materials/BÀI KIỂM TRA.png
last_reviewed: 2026-08-25
---

# Bài kiểm tra thường xuyên 2 — đối chiếu triển khai

Tài liệu này đối chiếu 10 tiêu chí Bài 2 trong ảnh P0
`source-materials/BÀI KIỂM TRA.png` với mã nguồn và lệnh kiểm thử hiện có.
`IMPLEMENTED_BASELINE` chỉ có nghĩa là repo có code/test tương ứng; không phải
lời hứa về điểm số hay nghiệm thu của giảng viên.

## Ma trận tiêu chí

| # | Tiêu chí P0 | Trạng thái | Bằng chứng kiểm tra |
|---:|---|---|---|
| 1 | Cấu trúc dự án hợp lý | IMPLEMENTED_BASELINE | `marketing_management/config/`, `campaigns/`, `templates/`, `static/`, `docs/`, `requirements.txt` |
| 2 | Đăng nhập và phân quyền | IMPLEMENTED_BASELINE | `config/urls.py`, `views.py` với `marketing_access_required`/`manager_access_required`, test staff bị chặn route manager |
| 3 | CRUD nghiệp vụ chính | IMPLEMENTED_BASELINE | Campaign/Channel/Content/Metric có create, list/detail, update, POST delete; test CRUD trong `campaigns/tests.py` |
| 4 | Tìm kiếm, lọc, sắp xếp | IMPLEMENTED_BASELINE | `campaign_list`: từ khóa, status, channel, khoảng ngày, sort và phân trang 8 dòng/trang; test lọc đúng, phân trang và ngày sai không crash |
| 5 | Thống kê/báo cáo cơ bản | IMPLEMENTED_BASELINE | Dashboard có lọc theo khoảng ngày, KPI CTR/conversion/chi phí và bảng/biểu đồ thanh hiệu quả theo kênh; aggregate từ `Metric` và test KPI/report |
| 6 | Giao diện rõ ràng, dễ sử dụng | IMPLEMENTED_BASELINE | Django templates, CSS responsive, trạng thái rỗng, messages thành công/lỗi, confirm trước xóa, form validation và nhãn ARIA cho biểu đồ; `evidence/runtime/B2-UI-001-v1-review.md` |
| 7 | CSDL ổn định và dữ liệu mẫu | IMPLEMENTED_BASELINE | SQLite, migration `0001_initial.py`, `seed_demo`, constraint/validation và `migrate --check`; test seed idempotent |
| 8 | Xử lý lỗi cơ bản | IMPLEMENTED_BASELINE | Validation ngày/metric, lọc dashboard sai ngày không crash, 400 AI thiếu brief, 405 route chỉ POST, ProtectedError khi xóa channel đang được dùng |
| 9 | Minh chứng dùng AI khi lập trình | IMPLEMENTED_BASELINE | `evidence/ai/B2-CODE-001-v1-review.md` ghi input, phạm vi hỗ trợ, file đã sửa và cách kiểm chứng; test cả fallback và provider contract; evidence AI nghiệp vụ giữ riêng |
| 10 | Mã nguồn và tài liệu chạy thử | IMPLEMENTED_BASELINE | `README.md`, `marketing_management/README.md`, `.env.example`, `requirements.txt`, lệnh migrate/seed/test, LaTeX/PDF/ZIP và lịch sử Git có commit mô tả rõ ràng |

## Cách chạy và kiểm tra

```powershell
cd marketing_management
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py seed_demo
python manage.py test campaigns -v 1
python manage.py runserver
```

Mở `http://127.0.0.1:8000/accounts/login/`. Tài khoản demo phải được tạo bằng
`python manage.py createsuperuser` hoặc gán nhóm `Marketing Manager`/
`Marketing Staff` trong Django admin; repo không chứa mật khẩu mẫu.

## Phạm vi chưa được khẳng định

- Provider AI thật chưa được gọi trong test tích hợp vì cần API key và endpoint
  do người dùng cung cấp; baseline dùng fallback offline và đã kiểm tra contract
  provider bằng mock.
- Chưa có số đo production hoặc kiểm thử tải; không dùng tài liệu này để suy ra
  hiệu năng ngoài phạm vi demo local.
- Kiểm tra giao diện trong tài liệu này là kiểm tra template/test client và CSS
  tĩnh; chưa tuyên bố đã kiểm thử trên mọi trình duyệt/thiết bị.
