---
document_id: AIA331-B2-EV-UI-001
project_id: AIA331-80300-MARKETING-AI
status: IMPLEMENTED_BASELINE
version: B2-UI-001-v1
last_reviewed: 2026-08-25
---

# Minh chứng kiểm tra giao diện và runtime — Bài 2

## Phạm vi đã kiểm tra

- Dashboard render được bộ lọc khoảng ngày, KPI tổng hợp và bảng hiệu quả theo
  kênh.
- Biểu đồ thanh có `role="img"` và `aria-label` mô tả số click, nên thông tin
  không chỉ phụ thuộc vào màu.
- Danh sách campaign có trạng thái rỗng, phân trang và giữ query filter khi
  chuyển trang.
- Form lỗi và message thành công/lỗi được render qua Django messages; CSS có
  `table-wrap`, grid responsive và breakpoint màn hình nhỏ.

## Bằng chứng lệnh/test

```text
python manage.py check                         -> no issues
python manage.py migrate --check                -> pass
python manage.py test campaigns -v 1            -> 25 tests, OK
```

Các assertion giao diện nằm trong `campaigns/tests.py`, gồm text bộ lọc báo cáo,
bảng kênh, `role="img"`, phân trang `Trang 2 / 2` và trạng thái lỗi ngày sai.

## Giới hạn cần nói rõ

Môi trường hiện tại không có Chrome DevTools MCP được cấu hình, vì vậy tài liệu
này chỉ khẳng định kiểm tra bằng Django test client và CSS/template tĩnh; không
tự suy ra đã kiểm thử mọi trình duyệt hoặc thiết bị thật.
