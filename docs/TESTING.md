# Kế Hoạch & Danh Mục Ca Kiểm Thử (Testing Guide & Test Catalogue)

> Học phần: Ứng dụng trí tuệ nhân tạo (AIA331)  
> Hệ thống: MarketFlow v2  
> Ngày cập nhật số liệu: 24/10/2026  
> Căn cứ kỹ thuật: `backend/tests/`, `ai-runner/tests/`, `frontend/`, `scripts/evaluate_assistant.py`  

---

## 1. Hướng dẫn Chạy các Bộ Kiểm Thử (How to Run Test Suites)

Tất cả các lệnh kiểm thử dưới đây được thiết kế độc lập, không yêu cầu dịch vụ nền bên ngoài (sử dụng CSDL in-memory SQLite và các fake runner kiểm thử):

### 1.1. Kiểm thử Backend (FastAPI - Python 3.12 / 3.13)
```powershell
# Chạy toàn bộ 54 ca kiểm thử backend
cd backend
python -m pytest -v

# Kiểm tra định dạng và quy chuẩn mã nguồn (Ruff Linter)
python -m ruff check .

# Chạy smoke test HTTP thật qua Uvicorn server cục bộ
python tests/smoke_test_real_http.py
```

### 1.2. Kiểm thử Dịch vụ AI Runner (ai-runner)
```powershell
# Chạy toàn bộ 16 ca kiểm thử runner (bao gồm kiểm thử hàng đợi, timeout và luồng NDJSON)
cd ai-runner
python -m pytest -v
```

### 1.3. Kiểm thử Chất lượng Giao diện Frontend (React SPA)
```powershell
cd frontend

# 1. Kiểm tra an toàn kiểu dữ liệu TypeScript (Strict Mode)
npm run typecheck

# 2. Kiểm tra chất lượng mã nguồn & Accessibility (ESLint - Zero Warnings)
npm run lint

# 3. Biên dịch gói xuất bản Production (Vite Build)
npm run build
```

### 1.4. Đánh giá Tự động Prompt Trợ lý AI (Evaluate Assistant)
```powershell
# Chạy đánh giá định lượng 8 ca kiểm thử qua 3 phiên bản prompt (Offline Dry-Run)
python scripts/evaluate_assistant.py --dry-run --all-versions

# Chạy đánh giá trực tiếp với AI Runner đang hoạt động
python scripts/evaluate_assistant.py --prompt-version deploy/opencode/prompts/v3.md
```

### 1.5. Kiểm thử Tích hợp Đầu-Cuối (Playwright E2E Test Suite)
```powershell
# 1. Khởi chạy QA Fake AI Runner (cổng 8100, phục vụ MCP streamable HTTP):
python backend/tests/qa_fake_runner.py --port 8100

# 2. Khởi tạo CSDL SQLite mới và nạp dữ liệu mẫu trên Backend (cổng 8000):
cd backend
$env:DATABASE_URL="sqlite:///./data/qa.db"
$env:AI_RUNNER_URL="http://127.0.0.1:8100"
$env:AI_RUNNER_TOKEN="qa-runner-token"
python -m alembic upgrade head
python seed/seed_demo.py --reset
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# 3. Khởi chạy Frontend React SPA (cổng 5173):
cd frontend
npm run dev

# 4. Thực thi toàn bộ bộ kiểm thử E2E (Playwright Chromium Headless):
cd frontend
npm run test:e2e
```

---

## 2. Kết Quả Đo Lường Thực Tế (Actual Execution Results)

Các số liệu ghi nhận trực tiếp từ các lệnh thực thi trong hệ thống:

| Phân hệ / Bộ kiểm thử | Công cụ | Số lượng kiểm thử | Kết quả thực tế | Thời gian thực thi |
|---|---|---|---|---|
| **ai-runner** | Pytest 9.1.0 | 16 test cases | **16 / 16 PASSED (100%)** | 3.90 giây |
| **Frontend Typecheck** | `tsc --noEmit` | Toàn bộ `src/**/*.ts(x)` | **0 lỗi (Exit Code 0)** | 8.87 giây |
| **Frontend Lint** | ESLint 9 | 100+ component & hooks | **0 cảnh báo (0 warnings)** | 7.35 giây |
| **Frontend Production Build** | Vite 5.4.21 | 2.788 modules | **Thành công (`dist/index.html`)** | 11.63 giây |
| **Frontend Playwright E2E** | Playwright 1.63.0 | 28 test cases | **28 / 28 PASSED (100%)** | 1.4 phút (84 giây) |
| **AI Prompt Evaluation** | `evaluate_assistant.py` | 8 ca kiểm thử định lượng | **Dry-Run (Harness Self-Test): Đạt**<br>*(Tự kiểm tra bộ chấm điểm bằng phản hồi mẫu viết tay; KHÔNG phản ánh kết quả mô hình thật)*<br>Chạy thật trên VPS: **Chưa chạy — sẽ cập nhật sau khi triển khai** | 0.85 giây |
| **Backend Full Test Suite** | Pytest 9.1.0 | 76 test cases | **76 / 76 PASSED (100%)** | 39.09 giây |

---

## 3. Danh Mục Ca Kiểm Thử Chi Tiết (Test Case Catalogue)

Bộ kiểm thử được phân nhóm theo từng module nghiệp vụ, bao gồm đầy đủ trường hợp bình thường (Normal), trường hợp lỗi (Error) và trường hợp biên (Boundary):

### 3.1. Phân hệ Xác thực & Quản lý Phiên (`backend/tests/test_auth.py`)

| Mã test | Tên ca kiểm thử | Loại ca | Hành vi & Kỳ vọng |
|---|---|---|---|
| `AUTH_01` | `test_login_success` | Normal | Đăng nhập đúng email và mật khẩu. Trả về HTTP 200, JWT token và thông tin người dùng. |
| `AUTH_02` | `test_login_wrong_password` | Error | Đăng nhập sai mật khẩu. Trả về HTTP 401 với mã lỗi `INVALID_CREDENTIALS`. |
| `AUTH_03` | `test_login_rate_limit` | Boundary | Thử đăng nhập sai 5 lần liên tiếp. Lần thứ 6 trả về HTTP 429 `LOGIN_RATE_LIMITED`. |
| `AUTH_04` | `test_login_disabled_account` | Error | Đăng nhập tài khoản bị khoá (`is_active=False`). Trả về HTTP 403 `ACCOUNT_DISABLED`. |
| `AUTH_05` | `test_me_endpoint` | Normal | Gửi Bearer Token lấy thông tin cá nhân. Trả về HTTP 200 và quyền hạn vai trò. |
| `AUTH_06` | `test_logout_revokes_token` | Normal | Đăng xuất làm tăng `token_version`. Token cũ gửi lại lập tức bị từ chối HTTP 401 `TOKEN_REVOKED`. |
| `AUTH_07` | `test_change_password` | Normal | Đổi mật khẩu thành công với mật khẩu cũ hợp lệ. Đăng nhập lại với mật khẩu mới. |

### 3.2. Phân hệ Quản lý Người dùng (`backend/tests/test_users.py`)

| Mã test | Tên ca kiểm thử | Loại ca | Hành vi & Kỳ vọng |
|---|---|---|---|
| `USER_01` | `test_list_users_as_manager` | Normal | Quản lý (`MANAGER`) liệt kê danh sách nhân sự trong công ty. HTTP 200. |
| `USER_02` | `test_list_users_as_marketer_forbidden` | Error | Nhân viên (`MARKETER`) gọi API quản lý người dùng. Trả về HTTP 403 `PERMISSION_DENIED`. |
| `USER_03` | `test_create_user_as_manager` | Normal | Quản lý tạo mới tài khoản nhân viên tiếp thị. HTTP 201. |
| `USER_04` | `test_create_duplicate_email` | Error | Tạo người dùng với email đã tồn tại. Trả về HTTP 409 `EMAIL_EXISTS`. |
| `USER_05` | `test_update_user_and_self_protection` | Boundary | Quản lý tự khoá tài khoản hoặc tự hạ quyền của chính mình. Bị chặn HTTP 400 `CANNOT_MODIFY_SELF`. |
| `USER_06` | `test_reset_password` | Normal | Quản lý đặt lại mật khẩu cho nhân viên. |

### 3.3. Phân hệ Kênh Tiếp thị (`backend/tests/test_channels.py`)

| Mã test | Tên ca kiểm thử | Loại ca | Hành vi & Kỳ vọng |
|---|---|---|---|
| `CHAN_01` | `test_list_channels` | Normal | Lấy danh mục 7 kênh tiếp thị chuẩn (FACEBOOK, TIKTOK, INSTAGRAM...). HTTP 200. |
| `CHAN_02` | `test_create_channel_manager` | Normal | Quản lý tạo kênh mới kèm quy tắc định dạng ký tự. HTTP 201. |
| `CHAN_03` | `test_create_channel_marketer_forbidden` | Error | Nhân viên cố gắng thêm kênh tiếp thị. Trả về HTTP 403. |
| `CHAN_04` | `test_delete_channel_in_use_conflict` | Error | Xoá kênh đã phát sinh nội dung hoặc chiến dịch. Trả về HTTP 409 `CHANNEL_IN_USE`. |
| `CHAN_05` | `test_delete_channel_unused` | Normal | Xoá kênh chưa từng được sử dụng. HTTP 204. |

### 3.4. Phân hệ Quản lý Chiến dịch (`backend/tests/test_campaigns.py`)

| Mã test | Tên ca kiểm thử | Loại ca | Hành vi & Kỳ vọng |
|---|---|---|---|
| `CAMP_01` | `test_create_campaign` | Normal | Tạo chiến dịch mới với ngân sách tổng và phân bổ ngân sách theo kênh. HTTP 201. |
| `CAMP_02` | `test_campaign_validation_end_before_start` | Error | Nhập `end_date` trước `start_date`. Trả về HTTP 422 `VALIDATION_ERROR`. |
| `CAMP_03` | `test_campaign_planned_budget_exceeds_total` | Boundary | Tổng ngân sách các kênh con lớn hơn ngân sách tổng chiến dịch. Trả về HTTP 422. |
| `CAMP_04` | `test_campaign_date_overlap_filter` | Normal | Lọc chiến dịch theo giao khoảng thời gian [start, end] với [date_from, date_to]. |
| `CAMP_05` | `test_marketer_cannot_edit_others_campaign` | Error | Nhân viên sửa chiến dịch do nhân viên khác làm chủ sở hữu. Trả về HTTP 403. |
| `CAMP_06` | `test_campaign_invalid_transition` | Error | Chuyển trạng thái sai quy tắc máy trạng thái. Trả về HTTP 409 `INVALID_TRANSITION`. |
| `CAMP_07` | `test_delete_campaign_with_content_conflict` | Error | Xoá chiến dịch đã có bài viết hoặc số liệu. Trả về HTTP 409 `CAMPAIGN_HAS_DATA`. |

### 3.5. Phân hệ Quản lý Nội dung & Kiểm duyệt (`backend/tests/test_contents.py`)

| Mã test | Tên ca kiểm thử | Loại ca | Hành vi & Kỳ vọng |
|---|---|---|---|
| `CONT_01` | `test_create_content` | Normal | Tạo bài viết bản nháp (`DRAFT`). Trạng thái ban đầu hợp lệ. |
| `CONT_02` | `test_create_content_channel_not_in_campaign` | Error | Tạo bài viết trên kênh không nằm trong danh mục phân bổ của chiến dịch. Trả về HTTP 400. |
| `CONT_03` | `test_submit_content_with_banned_matches` | Boundary | Gửi duyệt bài viết chứa từ cấm. Hệ thống chuyển `PENDING_REVIEW` và đính kèm danh sách `banned_matches`. |
| `CONT_04` | `test_marketer_cannot_approve` | Error | Nhân viên tự bấm phê duyệt bài viết. Trả về HTTP 403. |
| `CONT_05` | `test_manager_cannot_approve_own_content` | Boundary | Quản lý cố tình phê duyệt bài viết do chính mình tạo. Bị chặn HTTP 400 `CANNOT_REVIEW_OWN`. |
| `CONT_06` | `test_approve_and_reject_flow` | Normal | Quản lý duyệt bài (APPROVED) hoặc từ chối bài viết kèm lý do bắt buộc (REJECTED). |
| `CONT_07` | `test_mark_published` | Normal | Cập nhật bài viết APPROVED thành PUBLISHED kèm liên kết URL thực tế; tự động hoàn tất lịch đăng liên quan. |
| `CONT_08` | `test_delete_locked_content` | Error | Xoá bài viết đã được APPROVED hoặc PUBLISHED. Bị chặn HTTP 409 `CONTENT_LOCKED`. |
| `CONT_09` | `test_check_banned_endpoint` | Normal | Gọi API kiểm tra danh sách từ cấm độc lập (`POST /contents/check-banned`). |

### 3.6. Phân hệ Lập lịch Đăng bài (`backend/tests/test_schedules.py`)

| Mã test | Tên ca kiểm thử | Loại ca | Hành vi & Kỳ vọng |
|---|---|---|---|
| `SCHED_01`| `test_create_schedule_success` | Normal | Lập lịch đăng bài cho bài viết hợp lệ. HTTP 201. |
| `SCHED_02`| `test_create_schedule_in_past` | Error | Đặt lịch đăng trong quá khứ. Trả về HTTP 422. |
| `SCHED_03`| `test_create_schedule_outside_campaign_dates` | Boundary | Đặt lịch đăng ngoài khoảng thời gian bắt đầu/kết thúc của chiến dịch. Bị chặn HTTP 422. |
| `SCHED_04`| `test_complete_schedule_workflow` | Normal | Đánh dấu hoàn thành lịch đăng (`POST /schedules/{id}/done`) đồng bộ trạng thái bài viết thành `PUBLISHED`. |
| `SCHED_05`| `test_cancel_schedule` | Normal | Huỷ lịch đăng dự kiến. Trạng thái chuyển sang `CANCELLED`. |

### 3.7. Phân hệ Số liệu & Import CSV (`backend/tests/test_metrics.py`)

| Mã test | Tên ca kiểm thử | Loại ca | Hành vi & Kỳ vọng |
|---|---|---|---|
| `METR_01` | `test_upsert_metric_success` | Normal | Nhập số liệu hàng ngày. Nếu trùng ngày/chiến dịch/kênh thì tự động cập nhật đè (upsert). |
| `METR_02` | `test_metric_validation_clicks_greater_than_views` | Error | Nhập Clicks (150) lớn hơn Views (100). Trả về HTTP 422 `CLICKS_EXCEED_VIEWS`. |
| `METR_03` | `test_metric_validation_conversions_greater_than_clicks`| Error | Nhập Conversions (50) lớn hơn Clicks (30). Trả về HTTP 422 `CONVERSIONS_EXCEED_CLICKS`. |
| `METR_04` | `test_marketer_cannot_edit_other_marketer_metric` | Error | Nhân viên sửa bản ghi số liệu do nhân viên khác nhập. Trả về HTTP 403. |
| `METR_05` | `test_csv_template` | Normal | Tải tệp CSV mẫu chuẩn 8 cột (`GET /metrics/import/template`). HTTP 200. |
| `METR_06` | `test_csv_preview_and_commit` | Normal | Tải file CSV lên xem trước (preview phân loại insert/update), sau đó xác nhận lưu (commit). Ghi nhận `source=CSV`. |

### 3.8. Phân hệ Thống kê & Báo cáo (`backend/tests/test_stats.py`)

| Mã test | Tên ca kiểm thử | Loại ca | Hành vi & Kỳ vọng |
|---|---|---|---|
| `STAT_01` | `test_stats_overview_zero_denominators`| Boundary | Khi Views=0, Clicks=0, Cost=0. Các chỉ số CTR, CVR, CPC, CPA trả về `null` (không crash chia cho 0). |
| `STAT_02` | `test_stats_overview_with_metrics` | Normal | Tính toán chính xác CTR, CVR, CPC, CPA, CPM và tỷ lệ giải ngân ngân sách (`used_pct`). |
| `STAT_03` | `test_stats_timeseries` | Normal | Tổng hợp số liệu chuỗi thời gian theo ngày, tuần, tháng. |
| `STAT_04` | `test_stats_by_channel_and_by_campaign`| Normal | Báo cáo phân tích hiệu quả so sánh giữa các kênh và giữa các chiến dịch. |

### 3.9. Phân hệ AI Runner (`ai-runner/tests/`)

Bộ kiểm thử gồm 16 test cases tự động (`test_api.py` và `test_runner.py`):
1. `test_health_ok`: Trả về HTTP 200 và cấu hình model khi runner sẵn sàng.
2. `test_run_success_stream`: Stream NDJSON đầy đủ chu kỳ (`run` -> `session` -> `text` -> `done`).
3. `test_run_with_tool_call`: Xử lý sự kiện tool MCP, tự động cắt bỏ tiền tố `marketflow_`.
4. `test_run_timeout`: Kích hoạt timeout cứng, gửi `SIGKILL` huỷ toàn bộ nhóm tiến trình.
5. `test_run_rate_limited`: Nhận diện lỗi `FreeTierError` / 429 và ánh xạ thành mã lỗi `AI_RATE_LIMITED`.
6. `test_run_empty_response`: Nhận diện trường hợp model kết thúc mà không có văn bản -> `AI_EMPTY_RESPONSE`.
7. `test_abort_endpoint`: Endpoint `POST /abort` huỷ ngay tiến trình đang chạy.
8. `test_concurrency_queue`: Giới hạn đồng thời 1, yêu cầu thứ 2 nhận sự kiện `queued` với vị trí hàng đợi.
9. `test_queue_overflow`: Vượt quá `MAX_QUEUE=8` trả về lỗi HTTP 503 `AI_BUSY`.
10. `test_session_continuity`: Giữ nguyên `-s <session_id>` qua các lượt kế tiếp trong cùng phiên.
11. `test_fallback_model`: Tự động chuyển model dự phòng khi model chính lỗi.
12. `test_runner_token_auth`: Từ chối truy cập HTTP 401 khi thiếu hoặc sai `X-Runner-Token`.
13-16. Các kiểm thử biên về độ dài prompt, tham số môi trường và mã lỗi tiến trình.

---

### 3.10. Phân hệ Trợ lý AI Backend (`backend/tests/test_assistant_*.py`)

Bao gồm 21 ca kiểm thử chuyên sâu cho tầng Trợ lý AI của Backend:
1. **`test_assistant_actions.py` (6 tests)**:
   - Liệt kê danh sách đề xuất (`GET /assistant/actions`).
   - Lọc theo `thread_id` và `status`.
   - Xác nhận đề xuất bản nháp nội dung (`confirm` -> tạo `contents` thật trạng thái `PENDING_REVIEW` hoặc `DRAFT`).
   - Sửa tham số (`args`) trước khi xác nhận.
   - Từ chối đề xuất (`reject`).
   - Kiểm tra phân quyền: người dùng không được can thiệp vào đề xuất của người khác.
2. **`test_assistant_mcp.py` (5 tests)**:
   - Khởi tạo bắt tay giao thức MCP (Initialize & Handshake qua Stateless-HTTP `/mcp`).
   - Liệt kê công cụ (`tools/list`) trả về đầy đủ 14 công cụ với tiền tố `marketflow_`.
   - Gọi công cụ đọc với Run-Token hợp lệ (`tools/call` `list_channels`).
   - Từ chối khi thiếu Bearer Token hoặc token hết hạn.
   - Từ chối khi token sai `typ` (không phải `assistant_run`).
3. **`test_assistant_stream.py` (7 tests)**:
   - Khởi tạo phiên hội thoại mới (`POST /assistant/threads`).
   - Gửi tin nhắn và nhận luồng SSE hoàn chỉnh với FakeRunner (`message_start`, `status`, `tool_call`, `action`, `text`, `message_end`).
   - Chặn gửi tin nhắn song song khi phiên đang bận (HTTP 409 `THREAD_BUSY`).
   - Huỷ luồng giữa chừng (`POST /assistant/threads/{id}/stop`).
   - Tạo lại phản hồi (`POST /assistant/messages/{id}/regenerate`).
   - Bắt lỗi timeout và trả về mã lỗi `AI_TIMEOUT`.
   - Bắt lỗi rate limit và trả về mã lỗi `AI_RATE_LIMITED`.
4. **`test_assistant_tools.py` (3 tests)**:
   - Thực thi các công cụ tra cứu số liệu (`get_campaign`, `get_stats`).
   - Kiểm tra công cụ rà soát từ cấm (`check_banned_keywords`).
   - Tạo bản nháp nội dung nhiều mục (`propose_content_drafts`).

### 3.11. Phân hệ Kiểm thử Tích hợp Đầu-Cuối E2E (`frontend/tests/e2e/*.spec.ts`)

Bộ kiểm thử tích hợp đầu-cuối tự động gồm **28 ca kiểm thử E2E** thực thi trên trình duyệt Chromium Headless qua Playwright (`playwright.config.ts`, `npm run test:e2e`):

| Tệp kiểm thử | Số ca | Luồng nghiệp vụ kiểm thử | Kết quả thực tế (24/10/2026) |
|---|---|---|---|
| `auth.spec.ts` | 4 | Đăng nhập sai mật khẩu (báo lỗi tiếng Việt), Đăng nhập Quản lý (MANAGER) & Đăng xuất, Đăng nhập Nhân viên (MARKETER - ẩn menu duyệt), Cơ chế Rate Limit đăng nhập sai 5 lần chặn HTTP 429 | **4 / 4 PASSED** (8.0s) |
| `dashboard.spec.ts` | 4 | Kiểm tra đối soát số liệu tổng quan với API, nhãn Dữ liệu mẫu SEED (CONTRACT §0), Giao diện Responsive 768px, Đổi giao diện Sáng / Tối (Dark Mode), Chuông thông báo & Đánh dấu đã đọc | **4 / 4 PASSED** (8.7s) |
| `campaigns.spec.ts` | 4 | Danh sách & bộ lọc/tìm kiếm chiến dịch, Tạo chiến dịch với kiểm tra hợp lệ ngày kết thúc >= ngày bắt đầu, Chi tiết 3 tab chiến dịch, Chặn xoá chiến dịch đã phát sinh dữ liệu (409 Conflict) | **4 / 4 PASSED** (11.7s) |
| `metrics.spec.ts` | 2 | Nhập số liệu thủ công với ràng buộc Clicks <= Views và Conversions <= Clicks, Xem trước Preview và Commit tệp CSV `sample_ads_report.csv` | **2 / 2 PASSED** (6.1s) |
| `contents_reviews.spec.ts` | 4 | Soạn thảo bài viết bản nháp & gửi duyệt cảnh báo từ cấm, Quản lý phê duyệt bài viết nhân viên, Quản lý KHÔNG được tự duyệt bài viết của chính mình (`CANNOT_REVIEW_OWN`), Đánh dấu đã đăng (`PUBLISHED`) | **4 / 4 PASSED** (11.0s) |
| `calendar.spec.ts` | 3 | Chuyển đổi lịch Tháng / Tuần & điều hướng thời gian, Lập lịch đăng mới cho bài viết đã duyệt trong hạn chiến dịch, Xem chi tiết lịch và huỷ lịch đăng | **3 / 3 PASSED** (8.0s) |
| `settings.spec.ts` | 2 | Quản lý truy cập đủ 5 tab (Tài khoản, Người dùng, Kênh, Hồ sơ thương hiệu, Trạng thái AI với Fake Runner), Nhân viên chỉ thấy tab Tài khoản cá nhân | **2 / 2 PASSED** (6.2s) |
| `assistant.spec.ts` | 4 | Mở phiên từ nút "Hỏi Trợ lý AI" trên trang chiến dịch (tự động gắn ngữ cảnh), Gửi yêu cầu sinh bài -> gọi MCP tool -> hiển thị thẻ đề xuất -> sửa tham số -> Xác nhận tạo bài viết AI, Nút Dừng phản hồi (Stop), Báo lỗi khi chạm ngưỡng `AI_RATE_LIMITED`, Quản lý danh sách phiên (Tạo mới, Ghim, Xoá) | **4 / 4 PASSED** (15.6s) |
| `visual_audit.spec.ts` | 1 | Audit giao diện 8 trang cốt lõi ở 1280px & 768px (16 ảnh chụp màn hình), kiểm tra không tràn ngang, zero console error, không có từ ngữ cấm ("Copilot", "Doctor", "Enterprise", "Closed-loop") | **1 / 1 PASSED** (13.6s) |

---

## 4. Ghi Chú Kỹ Thuật & Báo Cáo Chất Lượng Mã Nguồn

1. **Kết quả kiểm thử Backend**: 100% kiểm thử tự động đã vượt qua (**76 / 76 tests PASSED** trong 39.09 giây).
2. **Linter Ruff Backend**: Tầng ứng dụng và kiểm thử (`backend/app/`, `backend/tests/`) đạt chuẩn 100% không có lỗi (`All checks passed!`).
3. **Frontend Quality Gates**:
   - `npm run typecheck`: **0 lỗi** TypeScript Strict Mode.
   - `npm run lint`: **0 cảnh báo** ESLint 9 Zero Warnings (`--max-warnings=0`).
   - `npm run build`: Biên dịch Production Bundle sạch trong 11.63 giây.
   - `npm run test:e2e`: **28 / 28 tests PASSED (100%)** trong 1.4 phút (84 giây).
4. **Các lỗi tích hợp đã phát hiện và xử lý triệt để**:
   - **Xung đột hủy luồng SSE khi chuyển đổi route Trợ lý AI**: Trong `useAssistantStream.ts`, `useEffect([threadId])` dọn dẹp nhầm luồng fetch khi route chuyển từ `undefined` sang `newThread.id`. Đã thêm `activeStreamThreadIdRef` để bảo vệ luồng SSE không bị ngắt quãng ngoài ý muốn.
   - **Cảnh báo React `validateDOMNesting`**: Khắc phục thẻ `<div>` lồng trong thẻ `<p>` tại `PageHeader` và thẻ `<div>` nằm trực tiếp trong thẻ `<table>` khi hiển thị `SkeletonRows` tại `CampaignsPage` và `ContentsPage`.
   - **Đồng bộ mã lỗi & ngôn ngữ thông báo**: Thống nhất định dạng thông báo tiếng Việt chuẩn CONTRACT giữa frontend UI và backend REST / MCP endpoint.
