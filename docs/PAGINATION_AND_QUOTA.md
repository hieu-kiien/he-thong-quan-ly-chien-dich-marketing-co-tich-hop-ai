# Phân trang & Hạn mức gói miễn phí

Tài liệu hợp đồng cho hai tính năng phục vụ trực tiếp cho **Bài kiểm tra thường xuyên 2, mục 4** ("Xây dựng chức năng tìm kiếm và lọc: cho phép tìm kiếm, lọc, sắp xếp dữ liệu theo tiêu chí phù hợp"), **Bài 3 mục 7** ("Xử lý và giới hạn AI") và **Thiết kế mục 4** ("Giới hạn quân").

Mã nguồn: `backend/app/core/pagination.py`, `backend/app/services/quota.py`.

---

## 1. Phân trang

### 1.1 Hợp đồng (duy nhất cho toàn API)

**Query**

| Tham số | Mặc định | Ràng buộc |
| --- | --- | --- |
| `page` | `1` | `>= 1` |
| `page_size` | `20` | `1 .. 100` |

**Response** — model `Page[T]`

```json
{
  "items": [ ... ],
  "total": 132,
  "page": 1,
  "page_size": 20,
  "total_pages": 7,
  "has_next": true,
  "has_prev": false
}
```

- `total` là **tổng số bản ghi sau khi lọc**, không phải số bản ghi của trang hiện tại.
- `total_pages = ceil(total / page_size)`, bằng `0` khi không có bản ghi.
- `has_next` / `has_prev` do server quyết định. UI **phải** dựa vào chúng, không suy đoán lại từ `page`.

### 1.2 Thứ tự áp dụng — chỗ dễ sai nhất

Mọi endpoint đi qua `paginate_query()`, đặt `count()` **sau tất cả điều kiện lọc** và **trước** `offset`/`limit`:

```
lọc (tenant scope + search + filter) → sắp xếp → count() → offset/limit
```

Phân trang rồi mới lọc là lỗi kinh điển: `total` sai, trang cuối rỗng bất thường, và nếu bộ lọc tenant vốn nằm sai chỗ thì `offset` có thể đọc lọt dòng của tenant khác.

### 1.3 Ổn định thứ tự

Mỗi nhánh `ORDER BY` đều kèm cột khoá phá thế (`id` tăng/giảm) để trang sau không lặp hoặc mất dòng khi hai bản ghi trùng giá trị sắp xếp.

### 1.4 `page_size` có trần

Trần `100` là bắt buộc: tham số `limit` không trần là đường DoS, và instance thật chạy Render free chỉ có **512 MB RAM / 0.1 CPU**. Vượt trần trả `422` (báo rõ) chứ không âm thầm cắt.

### 1.5 Tương thích ngược

- Client **bỏ qua** tham số phân trang vẫn nhận trang đầu hợp lệ (20 dòng).
- `GET /notifications` bỏ tham số `limit` cũ — FastAPI bỏ qua tham số lạ, nên client cũ vẫn nhận trang đầu.

### 1.6 Phong cách vỡ (có chủ đích)

9 endpoint chuyển từ **mảng phẳng** sang envelope vì không thể vừa giữ mảng phẳng vừa có `total` mà vẫn dùng một hợp đồng. Frontend được cập nhật cùng đợt.

### 1.7 Endpoint dùng hợp đồng

| Endpoint | Ghi chú thêm |
| --- | --- |
| `GET /campaigns` | `search`, `status`, `channel_id`, `start_date`, `end_date`, `objective`, `sort` |
| `GET /campaigns/{id}/contents` | `search`, `status`, `sort` |
| `GET /contents` | `search`, `status`, `channel_id`, `campaign_id`, `sort` (`status` nhận **nhiều giá trị**, cách nhau bằng dấu phẩy) |
| `GET /schedules` | `status`, `content_id` |
| `GET /notifications` | `unread_only` |
| `GET /workspaces` | — |
| `GET /ai/jobs` | `status`, `kind` |
| `GET /ai/logs` | `status` |
| `GET /settings/ai-keys/list` | — |
| `GET /tasks/my-tasks` | `status`, `priority`, `campaign_id`, `search`, `due` (`today`/`overdue`) |
| `GET /campaigns/{id}/tasks` | `status`, `priority`, `assignee_id` |
| `GET /tasks/my-tasks/summary` | Endpoint **đếm** (không phân trang) — phạm vi toàn bộ, xem mục 1.9 |

Giá trị `sort` là **allowlist**. Gửi giá trị lạ trả `422`, không nối thẳng vào `ORDER BY`.

### 1.8 Endpoint CỐ TÌNH không phân trang

| Endpoint | Vì sao |
| --- | --- |
| `GET /channels/channels`, `/products`, `/product-categories` | Dữ liệu tham chiếu tĩnh, tổng số bản ghi có trần nhỏ và cố định. Cắt trang ở đây chỉ thêm một vòng gọi mà không đổi gì, và dễ làm hỏng các ô chọn kênh/sản phẩm. |
| `GET /campaigns/{id}/budget-allocations` | Một dòng cho mỗi kênh, tức tối đa bằng số kênh. |
| `GET /campaigns/{id}/kpi-targets` | Một dòng cho mỗi loại KPI. |
| `GET /campaigns/{id}/metrics`, `/attribution` | Chuỗi số liệu cho biểu đồ. **Cắt trang một chuỗi biểu đồ là sai về ngữ nghĩa** — phải giữ toàn bộ chuỗi để tính tổng/tỷ lệ. |
| `GET /export/data` | Cố ý xuất TOÀN BỘ, không phải màn hình danh sách. |

### 1.9 Nguyên tắc: số liệu tổng hợp không được lấy từ một trang

Sau khi danh sách được phân trang ở server, mảng mà client giữ chỉ là **trang hiện tại**. Mọi số liệu mang nghĩa "toàn tenant" phải đếm ở server, nếu không nó sẽ báo sai ngay khi người dùng sang trang 2 — một con số sai mà không có tín hiệu nào cho biết.

| Số liệu | Nguồn |
| --- | --- |
| Ngân sách đang chạy, chi tiêu thực tế, clicks, ROAS (màn Chiến dịch) | `GET /analytics/dashboard` (`kpi`, `campaigns_summary.active_budget`) |
| Thẻ "Quá hạn / Hôm nay / Đang làm / Đã xong" (màn Tác vụ) | `GET /tasks/my-tasks/summary` |

### 1.10 Phía frontend

- `toPage<T>()` trong `frontend/src/services/api.ts` chấp nhận **cả** envelope lẫn mảng phẳng, nên endpoint chưa phân trang vẫn dùng chung được `<Pagination>`.
- Mỗi API có hai bản: `getAllPage(...)` trả `Page<T>`, `getAll(...)` trả `T[]` là lớp bọc mảng — giữ nguyên mọi nơi gọi cũ.
- `<Pagination>` (`frontend/src/components/Pagination.tsx`) áp ba quy tắc:
  1. `total === 0` → **không render** (màn hình trống không có thanh "Trang 1/1").
  2. Nút Trước/Sau vô hiệu hóc theo `has_prev`/`has_next` của server.
  3. Đổi `page_size` → **về trang 1** (giữ trang 7 rồi đổi sang 50 sẽ ra trang không tồn tại).

Màn hình đã có bộ điều khiển: **Quản Lý Chiến Dịch**, **Hàng Đợi Duyệt**, **Tác Vụ Của Tôi**.

---

## 2. Hạn mức gói miễn phí

### 2.1 KHác `enforce_quota` — đừng gộp

| | `enforce_quota` (`app/core/security.py`) | `app/services/quota.py` |
| --- | --- | --- |
| Mục đích | Chống lạm dụng (rate limit) | Giới hạn sản phẩm |
| Lưu trữ | Bộ nhớ tiến trình | CSDL (bền qua restart) |
| Khoá | Chuỗi tự do, thường theo user | Workspace / người dùng |
| Khi restart | Mất sạch | Giữ nguyên |

Hai tầng độc lập, **cả hai đều giữ nguyên**.

### 2.2 Bảng hạn mức

| Mã | Mặc định | Phạm vi | Loại |
| --- | --- | --- | --- |
| `ai_jobs_per_day` | 50 | workspace | Cửa sổ **trượt 24h** |
| `campaigns` | 25 | workspace | Đồng hồ tích luỹ |
| `contents` | 500 | workspace | Đồng hồ tích luỹ |
| `workspace_members` | 10 | workspace | Đồng hồ tích luỹ |
| `schedules` | 200 | workspace | Đồng hồ tích luỹ |
| `workspaces_per_user` | 5 | người dùng | Đồng hồ tích luỹ |

Vì sao chọn số: đủ rộng để một nhóm sinh viên demo cả buổi học (20–30 người) không bị vướng, nhưng hữu hạn để còn ý nghĩa. Mỗi dòng giải thích chi tiết hơn trong `.env.example`.

### 2.3 AI job tính lúc ENQUEUE, không phải lúc hoàn thành

"Lượt tiêu" của một AI job **chính là hàng trong bảng `ai_jobs`** — ta đếm chính những hàng đó, không lưu bộ đếm riêng. Hệ quả:

- Job được nhận → có hàng → đã tính 1 lượt. Người dùng biết **ngay** khi đã vượt, thay vì đợi vài phút rồi thấy job chết.
- **Retry idempotent không thể tính hai lần**: `find_by_idempotency_key` trả về job cũ, không tạo hàng mới. Đây là bảo đảm **cấu trúc**, không phải kỷ luật code.
- Job hỏng/huỷ **vẫn được tính** — nó đã chiếm slot worker và đã cố gọi LLM. Chỉ đếm job `succeeded` sẽ cho phép dồn hàng trăm job toàn lỗi mà không tốn lượt nào.
- Restart tiến trình không xoá lịch sử tiêu.

**Vì sao cửa sổ trượt chứ không phải ngày lịch UTC:** múi giờ Việt Nam là UTC+7, nên "ngày UTC" cắt qua lúc 7h sáng giờ địa phương — người demo buổi sáng sẽ thấy hạn mứng tự nhảy về 0 giữa chừng. Cửa sổ trượt cũng cho `resets_at` chính xác: thời điểm job cũ nhất rơi khỏi cửa sổ.

### 2.4 Điểm chặn (đều thuộc **server**)

| Endpoint | Hạn mức |
| --- | --- |
| `POST /ai/jobs` | `ai_jobs_per_day` |
| `POST /campaigns` | `campaigns` |
| `POST /contents` | `contents` |
| `POST /contents/{id}/schedule` | `schedules` |
| `POST /workspaces/{id}/members` | `workspace_members` |
| `POST /workspaces` | `workspaces_per_user` |

Mỗi điểm chặn có ít nhất một test gọi HTTP thật và khẳng định `429` (`backend/tests/test_quota.py`).

Kiểm tra luôn chạy **sau** khi đã chốt tenant và xác thực quyền — nếu kiểm tra sớm hơn thì một workspace khác nhận `429` thay vì `403`, tức lộ trạng thái hạn mức của tenant mà người gọi không thuộc về.

### 2.5 Thân lỗi 429

```json
{
  "detail": {
    "error": "quota_exceeded",
    "limit_code": "campaigns",
    "message": "Bạn đã dùng hết hạn mức chiến dịch của gói miễn phí (25/25). Hạn mức này KHÔNG tự đặt lại — hãy xoá bản ghi cũ hoặc liên hệ quản trị viên để được nâng hạn mức.",
    "used": 25,
    "limit": 25,
    "remaining": 0,
    "requested": 1,
    "scope": "workspace",
    "resets_at": null,
    "would_be_used": 26
  }
}
```

Kèm header `Retry-After` khi hạn mức có mốc reset. Hạn mức tích luỹ có `resets_at: null` và thông báo nói rõ **không tự đặt lại** — để người dùng biết phải xoá gì thay vì chờ.

### 2.6 Đường ghi đè cho quản trị viên

Cần thiết vì một admin khoá ngoài chính instance của mình thì không tự sửa được.

- `QUOTA_OVERRIDE_WORKSPACE_IDS` — danh sách id workspace được miễn trần, cách nhau bằng dấu phẩy. Rỗng = không miễn gì.
- Người dùng vai trò `ADMIN` được miễn sẵn (khớp mô hình "ADMIN có phạm vi toàn cục" đã có ở mọi endpoint khác).
- **Mọi lần dùng đường miễn trần đều được ghi log ở mức `WARNING`.** Một lớp phòng thủ bị bỏ qua trong im lặng thì không còn là lớp phòng thủ.

### 2.7 Phía frontend

- `quotaApi.get(workspaceId)` đọc `GET /workspaces/{id}/quota` (dùng chung `check_workspace_access`, nên không lọt chéo tenant).
- `<QuotaBadge>` hiện thanh "đã dùng / trần" + đồng hồ đặt lại, để người dùng thấy **trước khi** bấm chứ không chỉ biết sau khi thao tác đã thất bại.
- `getQuotaError(error)` + `<QuotaErrorCard>` hiện lỗi hạn mứng **bền** trên màn hình, kèm nút "Thử lại" — không phải toast biến mất sau vài giây.
- Ẩn/hiện nút ở UI chỉ để **hiển thị trước**; hạn mức thật vẫn thực thi ở server.

### 2.8 Giới hạn đã biết

Giữa lúc đếm và lúc ghi có thể có hai request cùng vượt trần (TOCTOU). Trên deployment này — Render free, dưới 50 người dùng đồng thời — chấp nhận được và ghi rõ tại `app/services/quota.py`. Hạn mứng ở đây là đường phòng thủ, không phải hàng rào tài chính, nên lệch một lượt khi tranh chấp không nghiêm trọng. Siết thành khoá ghi `SERIALIZABLE` sẽ tốn thêm một round-trip cho mọi lần tạo.