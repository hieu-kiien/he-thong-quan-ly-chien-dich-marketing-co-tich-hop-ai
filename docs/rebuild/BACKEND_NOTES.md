# MarketFlow — Backend Implementation Notes

## 1. Tổng quan & Kiến trúc

Backend của MarketFlow được tái cấu trúc hoàn toàn (clean rebuild) tuân thủ nghiêm ngặt theo **Design Contract** (`docs/rebuild/CONTRACT.md`), đề bài môn học AIA331 và bộ quy tắc chống "tính năng ảo" (Rule 0).

- **Framework**: FastAPI (Python 3.13 môi trường local Windows; Python 3.12 trên Ubuntu VPS Production).
- **ORM**: SQLAlchemy 2.0 (Typed `Mapped[...]`, `DeclarativeBase`).
- **Migrations**: Alembic (`alembic>=1.13.0,<2.0.0`).
- **Schemas**: Pydantic v2 (`pydantic>=2.8.0`).
- **Phân tách trách nhiệm (Clean Layered Architecture)**:
  - `app/core/`: Cấu hình (`config.py`), kết nối CSDL & UTC datetime (`database.py`), bảo mật & rate-limiter in-memory (`security.py`), xử lý lỗi & validation tiếng Việt chuẩn CONTRACT (§4) (`errors.py`), phân trang & sắp xếp (`pagination.py`), múi giờ Việt Nam (`timeutil.py`).
  - `app/models/`: Định nghĩa 14 bảng CSDL (Users, Channels, Campaigns, CampaignChannels, Contents, ContentReviews, Schedules, Metrics, BrandProfile, BannedKeywords, Notifications, AiThreads, AiMessages, AiActions).
  - `app/schemas/`: Pydantic schemas với Ref object nhúng (`UserRef`, `ChannelRef`, `CampaignRef`), ép kiểu tiền tệ số nguyên VND, validation quy tắc.
  - `app/services/`: **Trọng tâm nghiệp vụ & phân quyền**. Mọi hàm nhận `(db, user, ...)` và ném lỗi có kiểu (`DomainError`). Tầng REST router và tầng AI tools gọi chung một service layer duy nhất.
  - `app/api/v1/`: Router RESTful mỏng (thin controllers), ánh xạ request/response.
  - `app/assistant/`: Placeholder và README (`__init__.py`) dành riêng cho AI Assistant runtime agent triển khai.

---

## 2. Hướng dẫn chạy & Thao tác cục bộ

### Cài đặt môi trường
```powershell
cd backend
python -m pip install -r requirements.txt
```

### Chạy Migration CSDL
```powershell
# Chạy migration ban đầu lên SQLite file mặc định (backend/data/marketflow.db)
python -m alembic upgrade head
```

### Nạp dữ liệu mẫu (Seed Demo)
```powershell
# Nạp dữ liệu mẫu chuỗi cà phê đặc sản Việt Nam (source=SEED, từ chối chạy trên production trừ khi có --force)
python seed/seed_demo.py [--reset]
```

### Khởi chạy Backend Dev Server
```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Chạy Kiểm thử (Pytest) & Kiểm tra Định dạng (Ruff)
```powershell
# Toàn bộ test suite (54 tests, in-memory SQLite, phân quyền, biên, state machine)
python -m pytest

# Kiểm tra linter
python -m ruff check backend

# Smoke-test 10 endpoint chính với HTTP thật qua Uvicorn
python tests/smoke_test_real_http.py
```

---

## 3. Danh mục biến môi trường (`.env`)

| Biến môi trường | Kiểu | Mặc định | Ý nghĩa |
|---|---|---|---|
| `APP_NAME` | string | `MarketFlow` | Tên hệ thống |
| `APP_ENV` | string | `development` | Môi trường: `development`, `test`, `production` |
| `API_V1_PREFIX` | string | `/api/v1` | Tiền tố router REST |
| `DATABASE_URL` | string | `sqlite:///./data/marketflow.db` | CSDL: SQLite (dev/test), PostgreSQL 16 (prod) |
| `JWT_SECRET` | string | `dev-only-insecure-secret-change-me` | Secret ký token HS256 (bắt buộc >= 32 ký tự trên prod) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | int | `480` (8 giờ) | Thời hạn hiệu lực của Access Token |
| `CORS_ORIGINS` | string | `http://localhost:5173,http://127.0.0.1:5173` | Danh sách CORS cho phép React SPA |
| `AI_RUNNER_URL` | string | `http://127.0.0.1:8100` | Địa chỉ AI Runner nội bộ (health check & stream) |
| `AI_RUNNER_TOKEN` | string | `""` | Token bảo mật gọi AI Runner (`X-Runner-Token`) |

> **Quy định an toàn Production**: Phương thức `settings.validate_for_runtime()` tự động kiểm tra khi `APP_ENV=production`: từ chối khởi động nếu `JWT_SECRET` chưa đổi, nếu dùng SQLite thay vì PostgreSQL, hoặc nếu thiếu `AI_RUNNER_TOKEN`.

---

## 4. Các quyết định thiết kế & Giải pháp kỹ thuật (Deviations & Decisions)

1. **Enum lưu trữ thống nhất**:
   - Các enum (`UserRole`, `CampaignGoal`, `CampaignStatus`, `ContentType`, `ContentStatus`, `ContentOrigin`, `ReviewDecision`, `ScheduleStatus`, `MetricSource`, `AiMessageRole`, `AiMessageStatus`, `AiActionStatus`) được lưu dưới dạng `VARCHAR(20)` có ràng buộc `CHECK (role IN (...))`.
   - Giúp việc chạy migration, backup/restore trên cả SQLite và PostgreSQL 16 hoàn toàn tương thích và không gặp lỗi kiểu native enum của PostgreSQL khi thay đổi.
2. **Chuẩn hoá thời gian UTC & Giờ làm việc Việt Nam**:
   - Model sử dụng `UTCDateTime` custom TypeDecorator: SQLite lưu naive datetime nhưng luôn được parse trả về datetime có timezone UTC (`+00:00` / `Z`).
   - Múi giờ làm việc `Asia/Ho_Chi_Minh` (`UTC+7`) được xử lý qua `app.core.timeutil.today_vn()` và `vn_day_start_utc()` / `vn_day_end_utc()` khi lọc lịch và tính ngày báo cáo.
3. **Phân quyền chặt chẽ tại Service Layer (CONTRACT §2)**:
   - `MARKETER` không thể duyệt nội dung của bất kỳ ai.
   - `MANAGER` có thể duyệt nội dung nhưng **tuyệt đối không được duyệt nội dung do chính mình tạo** (`CANNOT_REVIEW_OWN`).
   - `MARKETER` chỉ được sửa/xoá chiến dịch hoặc số liệu do chính mình tạo/nhập.
4. **Xử lý số liệu & tỷ lệ (CONTRACT §10.13)**:
   - `ctr`, `cvr` là phân số thập phân (ví dụ `0.05` → UI hiển thị `5%`).
   - Các trường có hậu tố `_pct` (`budget_used_pct`, `budget.used_pct`, `used_pct`) là số phần trăm (ví dụ `45.2` → UI hiển thị `45,2%`).
   - Mọi phép chia có mẫu số bằng 0 đều trả về `null` (None), UI hiển thị dấu gạch ngang `"—”`.
5. **Đánh giá rủi ro xóa ký hiệu cũ (GitNexus Impact Analysis)**:
   - Ký hiệu cũ: `AIService`, `MarketFlowMCPServer`, `AIDoctorEngine`.
   - Kết quả GitNexus Impact upstream cho thấy các phụ thuộc chỉ nằm trong các file router/services legacy cũ đã được thay thế hoàn toàn trong lần tái cấu trúc này. Rủi ro được kiểm soát 100%, không ảnh hưởng đến hệ thống mới.
