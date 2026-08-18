---
project_id: AIA331-80300-MARKETING-AI
project_title: Hệ thống quản lý chiến dịch marketing có tích hợp AI
priority: P0
priority_level: CRITICAL
status: IMPLEMENTED_BASELINE
---

# Baseline Django — Marketing AI

Đây là baseline chạy được của đề tài AIA331 mã 80300. Ứng dụng tập trung vào
quản lý chiến dịch, kênh, nội dung, lịch/metric và luồng AI sinh bản nháp có
duyệt thủ công.

## Chạy local

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Tạo tài khoản staff để vào màn hình quản lý:

```powershell
python manage.py createsuperuser
```

Mặc định AI chạy `mock/fallback`, không cần API key. Có thể cấu hình provider
OpenAI-compatible qua `.env` theo `.env.example`; API key không được commit.

## Phạm vi hiện thực

- `Campaign`, `Channel`, `Content`, `Metric` có migration và admin.
- Có tạo/sửa/tìm kiếm/lọc chiến dịch, xem tổng hợp chỉ số và thêm nội dung.
- Nội dung AI luôn có cảnh báo và phải chuyển qua trạng thái duyệt trước khi
  được đăng.
- Provider adapter có prompt version `AI-CAM-001-v1` và fallback offline để demo.

Đây là baseline học tập, không tuyên bố đã hoàn thành mọi yêu cầu sản phẩm hoặc
đã đo độ chính xác AI ở môi trường production.
