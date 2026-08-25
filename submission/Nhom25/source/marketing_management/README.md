---
project_id: AIA331-80300-MARKETING-AI
project_title: Hệ thống quản lý chiến dịch marketing có tích hợp AI
priority: P1
priority_level: HIGH
status: IMPLEMENTED_BASELINE
---

# Baseline Django — Marketing AI

Đây là baseline chạy được của đề tài AIA331 mã 80300. Ứng dụng tập trung vào
quản lý chiến dịch, kênh, nội dung, lịch/metric và luồng AI sinh bản nháp có
duyệt thủ công.

## Đối chiếu Bài 2

Baseline hiện có CRUD campaign/channel/content/metric, đăng nhập và phân quyền,
tìm kiếm/lọc/sắp xếp/phân trang campaign, dashboard KPI có lọc ngày và report
theo kênh, validation và dữ liệu mẫu. Ma trận
10 tiêu chí cùng bằng chứng nằm ở `../docs/13-bai-2-implementation.md`.

## Chạy local

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Nếu cần file môi trường local, sao chép `.env.example` thành `.env` trước khi
chạy. Không commit `.env` hoặc API key.

Tạo tài khoản staff để vào màn hình quản lý:

```powershell
python manage.py createsuperuser
```

Mặc định AI chạy `mock/fallback`, không cần API key. Có thể cấu hình provider
OpenAI-compatible qua `.env` theo `.env.example`; API key không được commit.

## Phạm vi hiện thực

- `Campaign`, `Channel`, `Content`, `Metric` có migration và admin.
- Có tạo/sửa/tìm kiếm/lọc/phân trang chiến dịch, quản lý channel, ghi metric, xem
  tổng hợp chỉ số theo khoảng ngày/kênh và thêm nội dung.
- Nội dung AI luôn có cảnh báo và phải chuyển qua trạng thái duyệt trước khi
  được đăng.
- Provider adapter có prompt version `AI-CAM-001-v1`, JSON contract validation và
  fallback offline để demo; provider thật vẫn cần API key và integration test.

Các route chính:

- `/accounts/login/` — đăng nhập.
- `/` — dashboard KPI.
- `/campaigns/` — tìm kiếm/lọc/sắp xếp và CRUD campaign.
- `/channels/` — CRUD channel; xóa cần quyền manager và không xóa channel đang được dùng.
- `/campaigns/<id>/` — CRUD content/metric và approval gate.

Đây là baseline học tập, không tuyên bố đã hoàn thành mọi yêu cầu sản phẩm hoặc
đã đo độ chính xác AI ở môi trường production.
