---
document_id: BAI03-DOC-02
document_type: architecture-and-implementation-status
project_id: BAI03-SALES-AI
status: DERIVED
authority: static-code-audit
verification_mode: static-inspection
last_reviewed: 2026-08-17
---

# Kiến trúc và hiện trạng mã nguồn

## 1. Kết luận nhanh

Có hai nhánh Django khác nhau trong thư mục Bài 03. Cả hai đều chưa chứng minh
được một sản phẩm bán hàng tích hợp AI hoàn chỉnh.

| Nhánh | Vai trò nên hiểu | Mức hiện thực quan sát được |
|---|---|---|
| [`Code QLBH/`](<../Code QLBH/>) | Skeleton/blueprint modular, gần với kiến trúc mục tiêu | Thấp: nhiều model, URL, view, service và test là khung trống |
| [`sales_management/`](<../sales_management/>) | Nhánh hiện thực một phần | Trung bình ở model và CRUD danh mục; thấp ở route toàn hệ thống, báo cáo, AI |
| [`../../QLBH demo/`](<../../QLBH demo/>) | Demo cũ, lịch sử | Không dùng làm baseline; có cấu hình/bất biến tồn kho cần xem xét lại |

Đây là kết quả kiểm tra tĩnh file và kiểm tra Django. Virtual environment của
`sales_management` đang trỏ tới `C:\Python\Python310\python.exe` không còn tồn
tại; vì vậy đã dùng system Python 3.13 với `site-packages` của virtual
environment để chạy kiểm tra. Kết quả: `manage.py check` đạt ở cả hai nhánh;
toàn bộ test nghiệp vụ vẫn chưa được chạy trong đợt rà soát này.

## 2. Kiến trúc mục tiêu được mô tả

`Code QLBH/docs/architecture/codebase-blueprint.md` đề xuất luồng:

```text
request -> URL -> view -> service (ghi/thay đổi) hoặc selector (đọc)
        -> model/ORM -> response/template
```

Đây là nguyên tắc kiến trúc `DERIVED`, chưa phải bằng chứng mọi module đã tuân
theo. Business logic cập nhật tồn kho nên nằm trong service/transaction; báo cáo
nên đọc qua selector/query được kiểm soát.

## 3. Nhánh `Code QLBH/`

### Thành phần đã thấy

- `config/settings/base.py` khai báo các app `accounts`, `customers`,
  `suppliers`, `catalog`, `inventory`, `purchases`, `sales`, `invoices`,
  `payments`, `reports` và cấu hình SQLite.
- `config/urls.py` include URL của các app.
- `core/models.py` có `TimeStampedModel` trừu tượng.
- `README.md`, `.env.example` và tài liệu blueprint có hướng dẫn kiến trúc/cài
  đặt.

### Giới hạn đã xác minh

- Hầu hết `models.py` của app nghiệp vụ chỉ còn docstring hoặc khung khai báo.
- Các `urlpatterns` của `accounts`, `customers`, `catalog`, `suppliers`,
  `inventory`, `purchases`, `sales`, `invoices`, `payments` và `reports` đang
  là danh sách rỗng.
- `services.py`, `selectors.py`, `views.py`, `forms.py`, `permissions.py` và
  test phần lớn chưa có nghiệp vụ thực.
- Không thấy client/provider AI, endpoint chatbot, prompt runtime hay báo cáo
  AI trong code.

**Kết luận:** dùng nhánh này làm khung kiến trúc tham khảo; không dùng để tuyên
bố FR-003–FR-015 đã hoàn thành.

## 4. Nhánh `sales_management/`

### Model/nghiệp vụ có nội dung

| Khu vực | Bằng chứng đã thấy | Liên quan |
|---|---|---|
| `apps/accounts/models.py` | `Role`, `UserProfile`, `AuditLog`, `AIEventLog` | FR-001/002, NFR-010/012 |
| `apps/categories/` | Model, form, view, URL và test CRUD | FR-004 |
| `apps/products/models.py` | `Product` với code, category, giá, tồn và trạng thái | FR-003/009 |
| `apps/customers/models.py` | `Customer` và lịch sử mua ở mức model | FR-005 |
| `apps/sales/models.py` | `Invoice`, `InvoiceItem`, trạng thái, giảm giá, total/confirm | FR-006/007 |
| `apps/inventory/models.py` | `GoodsReceipt`, line, `StockMovement`, atomic confirm và guard tồn | FR-008/009, BR-003/014 |
| `apps/reports/models.py` | `SalesReportSnapshot` | FR-011, nhưng chưa phải dashboard chạy |
| `apps/purchases/models.py` | Chưa có nghiệp vụ đáng kể | FR-008 còn thiếu |

### Route, UI và test

- Root URL include nhiều app, nhưng URL của `accounts`, `customers`, `products`,
  `suppliers`, `inventory`, `purchases`, `sales` và `reports` đang rỗng.
- `categories/urls.py` có các route list/create/detail/update/delete và là phần
  CRUD rõ nhất.
- Test thực chất được thấy chủ yếu ở `categories/tests.py`; nhiều app khác còn
  test rỗng hoặc chỉ là khung.
- Chưa thấy route/dashboard/export cho FR-007, FR-010–FR-012.

### AI

`AIEventLog` là model lưu `purpose`, tóm tắt prompt/response, trạng thái và
thời gian. Nó không phải integration: chưa thấy SDK/provider, service gọi model,
prompt runtime, kiểm soát output hoặc endpoint FR-013–FR-015.

## 5. Ma trận yêu cầu → bằng chứng hiện tại

| Nhóm ID | Có dấu hiệu code | Chưa chứng minh |
|---|---|---|
| FR-001–002 | Model/profile/role và cấu hình Django ở mức khung | Login, lockout, permission trên request và test đầy đủ |
| FR-003–004 | Product/category model; category CRUD | Product CRUD hoàn chỉnh, ràng buộc và test đủ |
| FR-005 | Customer model | Route, search, lịch sử, quyền và test |
| FR-006–007 | Invoice/InvoiceItem model | POS UI/API, transaction, history/search, test |
| FR-008–009 | GoodsReceipt/StockMovement một phần | Luồng nhập đầy đủ, hủy/sửa hóa đơn, invariant test |
| FR-010 | Chưa có route rõ ràng | Bộ lọc và đo hiệu năng |
| FR-011–012 | Snapshot model | Query/dashboard/biểu đồ và PDF/Excel/CSV |
| FR-013–015 | AIEventLog chỉ là hạ tầng ghi nhận | Provider, adapter, prompt, endpoint, fallback, eval và test |

## 6. Rủi ro kỹ thuật cần xử lý trước khi mở rộng

1. Chọn một nhánh làm baseline thực thi; không phát triển hai settings/schema
   song song mà không có kế hoạch hợp nhất.
2. Chuẩn hóa tên module `catalog`/`products`, `sales`/`invoices`,
   `purchases`/`inventory` và vai trò `Owner`/`Manager`.
3. Đưa các quy tắc BR-003, BR-013, BR-014 vào transaction/service và test cạnh
   tranh; không chỉ xử lý trong form.
4. Không bật AI trước khi có lớp lọc dữ liệu server-side, quyền truy cập, timeout,
   fallback và log không chứa PII.
5. Không coi README, model hoặc migration là chứng minh UI/API đã dùng được;
   cần route, test và kịch bản chạy.

## 7. Bằng chứng cần bổ sung

- `python manage.py check` và `python manage.py test` của baseline đã chọn.
- Test cho tồn kho: bán vừa đủ, vượt kho, nhập, hủy, sửa, đồng thời.
- Test quyền của cả ba vai trò.
- Test báo cáo và export với dữ liệu mẫu.
- Test AI: hết hàng, thiếu dữ liệu, prompt injection, timeout, provider error,
  output sai schema và câu hỏi ngoài phạm vi.
- Nhật ký chạy thật có version prompt/model, latency, trạng thái và đánh giá
  của người dùng.
