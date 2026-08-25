---
document_id: AIA331-DOC-12
document_type: operations-and-backup
project_id: AIA331-80300-MARKETING-AI
priority: P1
priority_level: HIGH
status: IMPLEMENTED_BASELINE
last_reviewed: 2026-08-19
---

# Vận hành, sao lưu và phục hồi

## 1. Chạy từ môi trường sạch

```powershell
cd marketing_management
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py check
python manage.py test campaigns -v 1
```

## 2. Sao lưu SQLite

Tắt server trước khi sao lưu để tránh bản sao không nhất quán. Tạo thư mục
backup nằm ngoài repo và giữ tối đa 7 bản gần nhất:

```powershell
Copy-Item .\db.sqlite3 C:\Backups\marketing-ai\db-$(Get-Date -Format yyyyMMdd-HHmm).sqlite3
```

Không đưa database, backup hoặc `.env` vào Git/ZIP nộp.

## 3. Phục hồi

1. Dừng server và giữ lại file database lỗi để điều tra.
2. Chép bản backup đã kiểm tra vào `marketing_management/db.sqlite3`.
3. Chạy `python manage.py migrate --check` và `python manage.py check`.
4. Chạy test nghiệp vụ rồi mới khởi động server.

Mục tiêu bản demo: RPO ≤ 24 giờ, RTO ≤ 30 phút. Backup phải được thử restore
ít nhất một lần trước khi trình diễn.

## 4. Hiệu năng và khả dụng

- CRUD nội bộ mục tiêu p95 dưới 2 giây ở tải lớp học tối đa 50 người dùng đồng thời.
- Provider AI timeout 20 giây; lỗi mạng, thiếu key hoặc sai JSON chuyển fallback.
- Migration và seed cho phép dựng lại hệ thống trên máy mới mà không cần database
  hoặc secret từ máy phát triển.
