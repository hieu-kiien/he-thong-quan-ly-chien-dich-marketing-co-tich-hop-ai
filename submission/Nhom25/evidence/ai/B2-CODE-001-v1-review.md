---
document_id: AIA331-B2-EV-CODE-001
project_id: AIA331-80300-MARKETING-AI
status: IMPLEMENTED_BASELINE
prompt_id: B2-CODE-001
version: B2-CODE-001-v1
last_reviewed: 2026-08-25
---

# Minh chứng AI hỗ trợ lập trình — Bài 2

## 1. Input/prompt đã ghi nhận

Yêu cầu đầu vào của người dùng là đối chiếu và hoàn thiện dự án theo 10 tiêu
chí Bài kiểm tra thường xuyên 2 trong ảnh P0 `source-materials/BÀI KIỂM TRA.png`,
với đề tài marketing trong `source-materials/DỰ ÁN.png`. Người dùng yêu cầu
không suy đoán; điểm thiếu phải được kiểm tra từ code/tài liệu hoặc hỏi lại.

## 2. Phản hồi/đề xuất được sử dụng

AI hỗ trợ phân tích baseline hiện có và đề xuất các lát cắt có thể kiểm chứng:

1. Bổ sung update/delete cho Campaign, Channel, Content, Metric; delete dùng
   POST và quyền manager để tránh thao tác phá dữ liệu ngoài ý muốn.
2. Mở rộng campaign list với từ khóa, status, channel, khoảng ngày và sort.
3. Bổ sung dashboard aggregate từ Metric và số nội dung chờ duyệt.
4. Bổ sung xử lý ProtectedError, 405/400 và trạng thái lỗi trên giao diện.
5. Ghi lại ma trận Bài 2, README, `.env.example` và bằng chứng kiểm thử.

Đây là bản tóm tắt phạm vi hỗ trợ được lưu theo code diff; không phải bản chép
toàn bộ hội thoại nội bộ và không khẳng định AI provider bên ngoài đã được gọi.

## 3. Phần code được AI hỗ trợ và phần sinh viên kiểm tra/chỉnh sửa

| Phần | File | Cách kiểm chứng/chỉnh sửa |
|---|---|---|
| URL CRUD | `marketing_management/campaigns/urls.py` | Đối chiếu từng route với view và test `reverse()` |
| CRUD, filter, dashboard, RBAC | `marketing_management/campaigns/views.py` | Kiểm tra quyền, method POST, filter invalid và redirect; chạy test Django |
| Form datetime-local | `marketing_management/campaigns/forms.py` | Kiểm tra input format khi sửa lịch đăng |
| Giao diện | `marketing_management/templates/`, `static/css/app.css` | Kiểm tra URL template, trạng thái rỗng, message lỗi, confirm xóa và responsive CSS tĩnh |
| Regression tests | `marketing_management/campaigns/tests.py` | Sinh test trước khi sửa CRUD; sau đó chạy lại và đọc toàn bộ output |
| Hướng dẫn/ma trận | `README.md`, `marketing_management/README.md`, `docs/13-bai-2-implementation.md` | Đối chiếu với 10 tiêu chí P0, không ghi provider thật là đã nghiệm thu |

## 4. Bằng chứng kiểm tra đã chạy

```text
python manage.py check                         -> no issues
python manage.py migrate --check                -> pass
python manage.py test campaigns -v 1            -> 21 tests, OK
```

Các test mới bao phủ CRUD bốn nhóm dữ liệu, lọc keyword/channel/date/sort,
dashboard KPI, filter sai không crash, channel đang được dùng, seed demo
idempotent/console-safe và staff bị chặn route delete manager-only.

## 5. Giới hạn

- Không có API key hoặc endpoint provider thật trong repo; AI nghiệp vụ vẫn dùng
  fallback offline khi demo.
- Không có dữ liệu người dùng thật trong minh chứng.
- Tài liệu này chứng minh cách kiểm tra code hiện tại, không tự suy ra điểm số
  hoặc sự chấp thuận của giảng viên.
