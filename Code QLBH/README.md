# Sales Management Django Project

Blueprint codebase cho hệ thống quản lý bán hàng bằng Python/Django.

> **Trạng thái:** `IMPLEMENTED` ở mức skeleton kiến trúc. Nhiều model, URL,
> view, service và test còn là khung; README này không chứng minh các module đã
> chạy đầy đủ.

## Cài đặt nhanh

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## Kiến trúc

Project dùng cấu trúc modular trong `apps/`. Business logic đặt ở `services.py`,
query đọc dữ liệu đặt ở `selectors.py`, view chỉ điều phối request/response.
