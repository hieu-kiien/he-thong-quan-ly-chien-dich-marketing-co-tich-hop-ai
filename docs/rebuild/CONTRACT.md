# MarketFlow v2 — Design Contract (nguồn sự thật chung cho mọi agent)

> Branch: `rebuild/v2`. Code cũ tham khảo qua tag `legacy-v1` (`git show legacy-v1:<path>`).
> Ngôn ngữ UI & thông báo lỗi: **tiếng Việt**. Code, tên biến, enum: tiếng Anh.
> Đề bài gốc: `de_tai_AIA331_80300.txt`, rubric: `yeu_cau_mon_hoc_AIA331.txt`.

## 0. Luật chống "tính năng ảo" (bắt buộc)

1. Không hiển thị/ghi bất kỳ con số nào không đến từ dữ liệu người dùng nhập/import. Không ước tính, không "dự kiến +X%", không điểm số tự chế. Dữ liệu mẫu luôn `source=SEED` và UI có nhãn "Dữ liệu mẫu".
2. Không giả vờ tích hợp bên ngoài (không auto-đăng Facebook/TikTok, không gửi Zalo/email giả, không thanh toán giả, không webhook giả).
3. Chỉ gọi là "AI" khi thực sự gọi LLM (OpenCode). Luật if/else gọi là "cảnh báo theo quy tắc".
4. AI **không bao giờ** tự ghi dữ liệu nghiệp vụ: mọi thao tác ghi do AI đề xuất là `ai_action` trạng thái `PROPOSED`, người dùng bấm **Xác nhận** mới thực thi (bằng quyền của chính người đó). AI không bao giờ được duyệt (approve) hay đánh dấu đã đăng.
5. AI lỗi → báo lỗi thật. Không có "template fallback" giả làm AI.
6. Không emoji trong UI, không buzzword ("Enterprise", "Closed-loop", "Copilot", "Doctor"...).

## 1. Kiến trúc

```
Browser (React SPA)
  │  REST JSON + SSE (cùng origin /api/v1)
  ▼
FastAPI backend (marketflow-api, 127.0.0.1:8000)  ── PostgreSQL (prod) / SQLite (dev, test)
  │  ▲
  │  │ MCP streamable-HTTP  /mcp  (Bearer run-token, gọi ngược từ OpenCode)
  ▼  │
ai-runner (marketflow-ai-runner, 127.0.0.1:8100, user `mfai`)
  │ spawn mỗi lượt:  opencode run --agent marketflow [-s <session>] --format json "<prompt>"
  ▼
OpenCode CLI → OpenCode Zen (model miễn phí)
```

- Không API key, không chọn provider/model trên UI. Model (tuỳ chọn) đặt bằng env `OPENCODE_MODEL` ở runner.
- Agent OpenCode `marketflow` được định nghĩa trong `deploy/opencode/agent/marketflow.md`. **Không dùng `tools: false`** (Zen free tier trả 403) — khoá tool built-in bằng `permission: deny`.

## 2. Vai trò & phân quyền

| Vai trò | Mô tả |
|---|---|
| `MANAGER` | Quản lý marketing: toàn quyền, duyệt nội dung, quản lý người dùng/kênh/hồ sơ thương hiệu |
| `MARKETER` | Nhân viên marketing: tạo/sửa chiến dịch của mình, soạn nội dung, gửi duyệt, lập lịch, nhập số liệu |

| Hành động | MANAGER | MARKETER |
|---|---|---|
| Xem mọi chiến dịch, nội dung, lịch, số liệu, thống kê | ✓ | ✓ |
| Tạo chiến dịch | ✓ | ✓ (thành owner) |
| Sửa/xoá chiến dịch | ✓ | chỉ chiến dịch mình owner |
| Tạo nội dung | ✓ | ✓ |
| Sửa nội dung | khi chưa APPROVED/PUBLISHED | chỉ nội dung mình tạo, khi DRAFT/REJECTED |
| Gửi duyệt | người tạo | người tạo |
| Duyệt / từ chối | ✓ nhưng **không được duyệt nội dung do chính mình tạo** | ✗ |
| Đánh dấu đã đăng (APPROVED→PUBLISHED) | ✓ | người tạo hoặc người phụ trách lịch |
| Lập lịch đăng | ✓ | ✓ |
| Nhập/sửa số liệu | ✓ | ✓ (sửa/xoá: chỉ bản ghi mình nhập) |
| Quản lý user, kênh, hồ sơ thương hiệu | ✓ | ✗ (chỉ xem kênh, hồ sơ) |

Toàn bộ kiểm tra quyền nằm ở **service layer** (dùng chung cho REST và công cụ AI).

## 3. Mô hình dữ liệu (SQLAlchemy 2.0 + Alembic)

Mọi bảng có `id` int PK, `created_at`, `updated_at` (timezone-aware UTC). Tiền tệ: `Numeric(14,0)` VND.

- **users**: email UNIQUE, full_name, password_hash (bcrypt), role ENUM(MANAGER, MARKETER), is_active bool, token_version int.
- **channels**: code UNIQUE (FACEBOOK, INSTAGRAM, TIKTOK, ZALO_OA, EMAIL, GOOGLE_ADS, WEBSITE), name, format_rules text (gợi ý định dạng cho người & AI, vd giới hạn ký tự), is_active.
- **campaigns**: name, goal ENUM(AWARENESS, TRAFFIC, LEADS, SALES), objective text, target_audience text, product text (sản phẩm/dịch vụ), key_message text NULL, start_date DATE, end_date DATE, budget Numeric ≥0, status ENUM(PLANNED, ACTIVE, PAUSED, COMPLETED, CANCELLED), owner_id FK users. CHECK end_date ≥ start_date.
- **campaign_channels**: PK(campaign_id, channel_id), planned_budget Numeric NULL ≥0.
- **contents**: campaign_id FK, channel_id FK, content_type ENUM(SOCIAL_POST, EMAIL, AD_COPY, VIDEO_SCRIPT, OTHER), title (email: subject), body text, cta text NULL, status ENUM(DRAFT, PENDING_REVIEW, APPROVED, REJECTED, PUBLISHED), origin ENUM(MANUAL, AI), ai_message_id FK ai_messages NULL, created_by FK users, published_url NULL, published_at NULL, published_by FK NULL.
- **content_reviews**: content_id FK, reviewer_id FK, decision ENUM(APPROVED, REJECTED), comment text (bắt buộc khi REJECTED).
- **schedules**: content_id FK, scheduled_at timestamptz, assignee_id FK users, status ENUM(PLANNED, DONE, CANCELLED), note NULL, done_at NULL.
- **metrics**: campaign_id FK, channel_id FK, metric_date DATE, views, clicks, conversions (int ≥0), cost Numeric ≥0, source ENUM(MANUAL, CSV, SEED), entered_by FK users NULL, import_batch str NULL. UNIQUE(campaign_id, channel_id, metric_date). CHECK clicks ≤ views (chỉ khi views>0), conversions ≤ clicks (chỉ khi clicks>0).
- **brand_profile** (1 dòng): brand_name, description, tone_of_voice, target_audience, guidelines.
- **banned_keywords**: keyword UNIQUE (lowercase), note NULL.
- **notifications**: user_id FK, type str, message, link str NULL, is_read bool.
- **ai_threads**: user_id FK, campaign_id FK NULL (ngữ cảnh gắn kèm), title, opencode_session_id NULL, pinned bool, last_message_at.
- **ai_messages**: thread_id FK, role ENUM(USER, ASSISTANT), content text (markdown), parts_json (danh sách tool call/artifact — xem §6), status ENUM(STREAMING, COMPLETE, ERROR, STOPPED), error_code NULL, model NULL, latency_ms NULL.
- **ai_actions**: thread_id FK, message_id FK, user_id FK, tool str, args_json, summary str (mô tả tiếng Việt), status ENUM(PROPOSED, EXECUTED, REJECTED, FAILED), result_json NULL, error NULL, executed_at NULL.

Seed demo: 1 MANAGER (`manager@marketflow.vn` / `Manager@123`), 2 MARKETER (`marketer@marketflow.vn` / `Marketer@123`, `marketer2@marketflow.vn` / `Marketer@123`), 7 kênh, ~5 chiến dịch của 1 chuỗi cà phê/mỹ phẩm Việt có nội dung đủ trạng thái, lịch, số liệu 30–60 ngày (`source=SEED`), hồ sơ thương hiệu, ~10 từ cấm ("cam kết 100%", "chữa khỏi", "rẻ nhất", ...). Seed chỉ chạy bằng lệnh tường minh, không tự chạy ở production.

## 4. Quy ước API

- Prefix `/api/v1`. Auth: `Authorization: Bearer <JWT>` (HS256, 8h, claim `tv`=token_version).
- Lỗi: HTTP status đúng nghĩa + body `{"detail": {"code": "SNAKE_UPPER", "message": "Thông báo tiếng Việt", "fields": {"field": "lỗi"}?}}`. 422 cũng theo format này (`code: VALIDATION_ERROR`).
- Phân trang: `?page=1&page_size=20` (max 100) → `{"items": [...], "total": n, "page": 1, "page_size": 20}`.
- Ngày: `YYYY-MM-DD`; thời điểm: ISO-8601 có timezone. Số tiền: số nguyên VND.
- Sort: `?sort=field` hoặc `?sort=-field`.

### Endpoints

**health**: `GET /health` → `{status, db, ai_runner}`.

**auth**: `POST /auth/login {email,password}` → `{access_token, token_type:"bearer", user}` · `GET /auth/me` · `POST /auth/logout` (tăng token_version) · `POST /auth/change-password {current_password,new_password}`. Rate-limit đăng nhập sai (5 lần/5 phút/email+IP → 429).

**users** (MANAGER): `GET /users` · `POST /users {email,full_name,role,password}` · `PATCH /users/{id} {full_name?,role?,is_active?}` · `POST /users/{id}/reset-password {new_password}`. Không tự hạ quyền/khoá chính mình.

**channels**: `GET /channels?include_inactive=` · `POST/PATCH /channels/{id}` (MANAGER) · `DELETE /channels/{id}` (MANAGER; nếu đã được dùng → 409 `CHANNEL_IN_USE`, gợi ý tắt is_active).

**campaigns**:
- `GET /campaigns?q=&status=&goal=&channel_id=&date_from=&date_to=&owner_id=&sort=&page=&page_size=` — lọc thời gian theo **giao nhau khoảng** [start_date,end_date] với [date_from,date_to]; lọc kênh qua campaign_channels. Item: `{id,name,goal,status,start_date,end_date,budget,owner:{id,full_name},channels:[{id,code,name,planned_budget}],spent,content_counts:{DRAFT:..,...}}`.
- `POST /campaigns {name,goal,objective,target_audience,product,key_message?,start_date,end_date,budget,status?,channels:[{channel_id,planned_budget?}]}`.
- `GET /campaigns/{id}` (kèm `stats` tổng: views, clicks, conversions, cost, ctr, cvr, cpc, cpa, budget_used_pct).
- `PATCH /campaigns/{id}` (cùng trường, channels thay thế toàn bộ nếu gửi).
- `DELETE /campaigns/{id}` — nếu đã có nội dung hoặc số liệu → 409 `CAMPAIGN_HAS_DATA` (gợi ý chuyển CANCELLED).

**contents**:
- `GET /contents?campaign_id=&channel_id=&status=&origin=&created_by=&q=&sort=&page=` · `POST /contents {campaign_id,channel_id,content_type,title,body,cta?}` (status DRAFT) · `GET/PATCH/DELETE /contents/{id}` (xoá chỉ khi DRAFT/REJECTED).
- `POST /contents/{id}/submit` (DRAFT|REJECTED → PENDING_REVIEW; trả `banned_matches` nếu có — vẫn cho gửi nhưng cảnh báo).
- `POST /contents/{id}/approve {comment?}` · `POST /contents/{id}/reject {comment}` (PENDING_REVIEW → APPROVED|REJECTED, ghi content_reviews, tạo notification cho người tạo).
- `POST /contents/{id}/mark-published {published_url?, published_at?}` (APPROVED → PUBLISHED; đánh dấu schedule liên quan DONE).
- `GET /contents/{id}/reviews`.
- `POST /contents/check-banned {text}` → `{matches:[{keyword,count}]}`.
- Chuyển trạng thái sai → 409 `INVALID_TRANSITION`.

**schedules**: `GET /schedules?date_from=&date_to=&channel_id=&campaign_id=&assignee_id=&status=` (item kèm content tóm tắt + campaign + channel) · `POST /schedules {content_id,scheduled_at,assignee_id?,note?}` (content không được REJECTED/PUBLISHED) · `PATCH /schedules/{id}` · `POST /schedules/{id}/done {published_url?}` (content phải APPROVED → content PUBLISHED) · `POST /schedules/{id}/cancel`.

**metrics**:
- `GET /metrics?campaign_id=&channel_id=&date_from=&date_to=&source=&page=` · `POST /metrics {campaign_id,channel_id,metric_date,views,clicks,conversions,cost}` (upsert theo khoá duy nhất, source=MANUAL) · `PATCH/DELETE /metrics/{id}`.
- `GET /metrics/import/template` (CSV mẫu) · `POST /metrics/import/preview` (multipart `file`, tối đa 2MB/5000 dòng; cột: `date,campaign_id|campaign_name,channel_code,views,clicks,conversions,cost`) → `{rows:[...], errors:[{row,message}], summary}` · `POST /metrics/import/commit {rows}` → `{inserted,updated,import_batch}` (source=CSV).

**stats** (mọi tham số lọc: `date_from,date_to,campaign_id,channel_id,status`):
- `GET /stats/overview` → `{totals:{views,clicks,conversions,cost}, rates:{ctr,cvr,cpc,cpa,cpm}, budget:{total_budget,spent,used_pct}, campaigns:{by_status:{...}}, contents:{by_status:{...}}, pending_reviews, schedules_today, has_seed_data}`.
- `GET /stats/timeseries?granularity=day|week|month` → `[{period,views,clicks,conversions,cost}]`.
- `GET /stats/by-channel` → `[{channel:{id,code,name},views,clicks,conversions,cost,ctr,cvr,cpc,cpa}]`.
- `GET /stats/by-campaign` → `[{campaign:{id,name,status},budget,cost,used_pct,views,clicks,conversions,ctr,cpa}]`.
- Công thức: ctr=clicks/views, cvr=conversions/clicks, cpc=cost/clicks, cpa=cost/conversions, cpm=cost/views*1000; mẫu số 0 → `null` (UI hiện "—").

**brand**: `GET /brand-profile` → `{brand_name,description,tone_of_voice,target_audience,guidelines,banned_keywords:[...]}` · `PUT /brand-profile` (MANAGER).

**notifications**: `GET /notifications?unread_only=` · `POST /notifications/{id}/read` · `POST /notifications/read-all`.

**assistant** (xem §5–§6): 
- `GET /assistant/threads?q=` · `POST /assistant/threads {title?,campaign_id?}` · `GET /assistant/threads/{id}` · `PATCH /assistant/threads/{id} {title?,campaign_id?,pinned?}` · `DELETE /assistant/threads/{id}` (chỉ chủ phiên).
- `GET /assistant/threads/{id}/messages`.
- `POST /assistant/threads/{id}/messages {content}` → **`text/event-stream`** (§6). Một phiên chỉ chạy 1 lượt tại một thời điểm (409 `THREAD_BUSY`).
- `POST /assistant/threads/{id}/stop` · `POST /assistant/messages/{id}/regenerate` → SSE.
- `GET /assistant/actions?thread_id=&status=` · `POST /assistant/actions/{id}/confirm {args?}` (cho phép người dùng sửa tham số trước khi xác nhận; thực thi qua service layer với quyền người dùng) · `POST /assistant/actions/{id}/reject`.
- `GET /assistant/status` → `{available, runner:{ok,version,model}, last_error?, queue_length}`.

## 5. Trợ lý AI — năng lực & công cụ

Trợ lý giống Claude: một **khu vực làm việc riêng** (route `/assistant`) với danh sách phiên, khung chat stream, và **panel bên phải (Artifacts)** hiển thị bản nháp, bảng số liệu, đề xuất thao tác.

AI tự biết: nó là "Trợ lý Marketing AI của MarketFlow", phục vụ một team marketing SME Việt Nam, nhiệm vụ & giới hạn (§0). Mỗi lượt backend gửi kèm khối `[NGỮ CẢNH]` ngắn: người dùng (tên, vai trò), ngày hiện tại (Asia/Ho_Chi_Minh), chiến dịch đang gắn với phiên (nếu có, tóm tắt), danh sách kênh. Dữ liệu chi tiết AI tự lấy qua công cụ.

**Công cụ (ToolRegistry trong backend — một nơi định nghĩa, dùng cho MCP):**

Đọc (thực thi ngay, theo quyền người dùng):
- `list_campaigns(q?, status?, channel_code?, date_from?, date_to?, limit?)`
- `get_campaign(campaign_id)` — chi tiết + kênh + stats tổng
- `get_stats(campaign_id?, channel_code?, date_from?, date_to?, group_by: none|channel|campaign|day|week|month)`
- `list_contents(campaign_id?, channel_code?, status?, q?, limit?)` · `get_content(content_id)`
- `list_schedules(date_from?, date_to?, campaign_id?)`
- `list_channels()` · `get_brand_profile()` (kèm từ cấm)
- `check_banned_keywords(text)`

Ghi (chỉ tạo `ai_action` PROPOSED; trả về cho AI: "Đã tạo đề xuất #id, chờ người dùng xác nhận"):
- `propose_content_drafts(items: [{campaign_id, channel_code, content_type, title, body, cta?}])` — xác nhận ⇒ tạo contents `origin=AI`, `ai_message_id`, status **PENDING_REVIEW** (hoặc DRAFT nếu người dùng chọn "Lưu nháp").
- `propose_campaign(name, goal, objective, target_audience, product, start_date, end_date, budget, channels[])`
- `propose_campaign_update(campaign_id, fields...)`
- `propose_schedule(content_id, scheduled_at, note?)`
- `propose_metrics(rows: [{campaign_id, channel_code, metric_date, views, clicks, conversions, cost}])` — dùng khi người dùng dán số liệu vào chat.

Không có công cụ approve/publish/xoá.

Giao thức với OpenCode: backend expose MCP **streamable HTTP** tại `/mcp` (Python SDK `mcp`), xác thực bằng **run-token** (JWT ngắn hạn 10 phút, claim `typ=assistant_run`, `uid`, `thread_id`, `message_id`) do backend cấp cho từng lượt và runner truyền vào tiến trình OpenCode qua env `MF_RUN_TOKEN` (`opencode.json`: `"headers": {"Authorization": "Bearer {env:MF_RUN_TOKEN}"}`). Nếu P0 spike chứng minh MCP bị Zen free tier chặn, dùng **giao thức văn bản dự phòng**: AI in khối ```` ```mf-tool {"name":..., "args":{...}}``` ```` → backend thực thi, gửi kết quả lại trong lượt kế tiếp cùng session (tối đa 6 vòng). ToolRegistry phải độc lập transport để hỗ trợ cả hai.

## 6. Luồng stream (backend → browser, SSE)

Mỗi event: `event: <type>\ndata: <json>\n\n`.

| event | data |
|---|---|
| `message_start` | `{user_message: Message, assistant_message: {id, status:"STREAMING"}}` |
| `status` | `{phase: "queued"|"thinking"|"tool"|"writing", queue_position?}` |
| `text` | `{content}` — **toàn bộ** nội dung markdown tính đến hiện tại (không phải delta) |
| `tool_call` | `{id, name, args, status: "running"|"done"|"error", summary?}` |
| `action` | `AiAction` (đề xuất mới cần xác nhận) |
| `message_end` | `{message: Message}` (bản cuối, đã lưu DB) |
| `error` | `{code, message}` — code: `AI_UNAVAILABLE`, `AI_RATE_LIMITED`, `AI_TIMEOUT`, `AI_EMPTY_RESPONSE`, `AI_INTERNAL` |

`Message.parts_json`: `[{type:"tool_call", id, name, args, status, summary}, {type:"action", action_id}]` theo thứ tự xuất hiện; `content` là văn bản markdown cuối.

## 7. ai-runner (dịch vụ nội bộ)

- `GET /health` → `{ok, opencode_version, model}`.
- `POST /run` (header `X-Runner-Token`) body `{session_id?, prompt, env:{MF_RUN_TOKEN}, timeout_s?}` → **NDJSON stream**: `{"type":"session","id"}`, `{"type":"text","text"}` (toàn văn part), `{"type":"tool","name","status","input","output"}`, `{"type":"done","model","latency_ms"}`, `{"type":"error","code","message"}`.
- `POST /abort {run_id}`. Hàng đợi tuần tự (concurrency mặc định 1), timeout cứng, kill cả process group khi hủy/timeout. Mapping lỗi: chuỗi `FreeTierError`/`Free usage limit`/429 → `AI_RATE_LIMITED`; quá hạn → `AI_TIMEOUT`; không có text → `AI_EMPTY_RESPONSE`.
- Chạy user `mfai`, `HOME=/var/lib/mfai`, cwd = thư mục sandbox rỗng chỉ đọc chứa `.opencode/agent/marketflow.md` + `opencode.json`.

## 8. Frontend

React 18 + Vite + TypeScript strict + Tailwind 3 + `react-router-dom` + `@tanstack/react-query` + `react-markdown`/`remark-gfm` + `recharts` + `lucide-react`. Font Be Vietnam Pro. Phong cách: tối giản, trung tính ấm (stone), không gradient, không emoji, mật độ thông tin vừa phải, hỗ trợ dark mode.

Routes: `/login` · `/` Tổng quan · `/campaigns`, `/campaigns/new`, `/campaigns/:id` (tab Thông tin / Nội dung & lịch / Số liệu) · `/contents`, `/contents/:id` · `/reviews` (MANAGER) · `/calendar` · `/assistant`, `/assistant/:threadId` · `/settings` (Tài khoản; MANAGER thêm Người dùng, Kênh, Hồ sơ thương hiệu, Trạng thái AI).

Trang `/assistant` (giống Claude): cột trái danh sách phiên (tìm kiếm, ghim, đổi tên, xoá, "Phiên mới"); giữa là hội thoại markdown stream, hiển thị bước dùng công cụ dạng gọn có thể mở rộng, nút Dừng / Tạo lại / Sao chép; ô soạn có chọn chiến dịch ngữ cảnh + gợi ý nhanh ("Gợi ý ý tưởng nội dung", "Viết caption theo kênh", "Viết email", "Tóm tắt hiệu quả & gợi ý cải thiện", "Lập kế hoạch nội dung tuần"); panel phải "Đề xuất & bản nháp" liệt kê ai_actions của phiên (sửa trước khi xác nhận, Xác nhận / Bỏ qua, trạng thái sau thực thi, link tới nội dung đã tạo). Có nút "Hỏi Trợ lý AI" trên trang chiến dịch/nội dung → mở phiên mới gắn chiến dịch đó. Cảnh báo cố định nhỏ: "Nội dung do AI tạo cần được kiểm tra và duyệt trước khi sử dụng."

## 9. Kiểm thử & chất lượng

- Backend: pytest (SQLite), mỗi router có test đúng/sai/biên + phân quyền; assistant test bằng **FakeRunner** (thành công, gọi tool, đề xuất, timeout, rate limit, rỗng, stop). ruff sạch.
- Frontend: `npm run typecheck`, `npm run lint` (max-warnings 0), `npm run build` sạch; Playwright e2e cho luồng chính.
- Tuân thủ `AGENTS.md` (GitNexus impact trước khi sửa/xoá symbol cũ; orchestrator chạy detect-changes trước commit).

## 10. Phụ lục A — Hình dạng response (đã chốt, bắt buộc cả backend & frontend)

1. Ref object nhúng: `UserRef={id,full_name}`, `ChannelRef={id,code,name}`, `CampaignRef={id,name}`.
2. `Content = {id,campaign_id,campaign:CampaignRef,channel_id,channel:ChannelRef,content_type,title,body,cta,status,origin,ai_message_id,created_by:UserRef,published_url,published_at,published_by:UserRef|null,created_at,updated_at}`. Lọc list `created_by=<user_id>`.
3. `POST /contents/{id}/submit` → Content đã cập nhật + `banned_matches:[{keyword,count}]` ở cấp cao nhất.
4. `ContentReview = {id,content_id,reviewer:UserRef,decision,comment,created_at}`; `GET /contents/{id}/reviews` → mảng.
5. `Schedule = {id,content_id,scheduled_at,assignee:UserRef|null,status,note,done_at,content:{id,title,status,content_type,created_by:UserRef},campaign:CampaignRef,channel:ChannelRef,created_at,updated_at}`; `GET /schedules` → mảng thường (lọc theo khoảng ngày, không phân trang).
6. `Metric = {id,campaign_id,campaign:CampaignRef,channel_id,channel:ChannelRef,metric_date,views,clicks,conversions,cost,source,entered_by:UserRef|null,import_batch,created_at,updated_at}`; `GET /metrics` phân trang.
7. CSV preview row: `{row,metric_date,campaign_id,campaign_name,channel_id,channel_code,views,clicks,conversions,cost,exists}` (exists=true nghĩa là sẽ cập nhật); `summary` = object phẳng số: `{total,valid,invalid,inserts,updates}`; commit body = `{rows: <các preview row hợp lệ như đã trả về>}` — backend **phải validate lại** khi commit.
8. Phân trang: /campaigns, /contents, /metrics, /users, /notifications (notifications thêm `unread_count`). Mảng thường: /channels, /schedules, /stats/timeseries, /stats/by-channel, /stats/by-campaign, /assistant/threads, /assistant/threads/{id}/messages, /assistant/actions, /contents/{id}/reviews.
9. `GET /brand-profile`: `banned_keywords:[{id,keyword,note}]`; `PUT /brand-profile` nhận `banned_keywords:[{keyword,note?}]` (thay thế toàn bộ).
10. `User = {id,email,full_name,role,is_active,created_at,updated_at}`. Rate-limit đăng nhập → 429 `detail.code=LOGIN_RATE_LIMITED`.
11. `AiThread = {id,user_id,campaign_id,campaign:CampaignRef|null,title,pinned,last_message_at,created_at,updated_at}`. `AiMessage = {id,thread_id,role,content,parts_json,status,error_code,model,latency_ms,created_at}`. `AiAction = {id,thread_id,message_id,user_id,tool,args_json,summary,status,result_json,error,executed_at,created_at}`.
12. Datetime trả về luôn có offset timezone (UTC `+00:00` hoặc `Z`); client gửi `scheduled_at` dạng `2026-10-24T19:30:00+07:00`, backend chuẩn hoá về UTC khi lưu.
13. Đơn vị số: `ctr`, `cvr` là **phân số** (0.0234 → UI "2,34%"). Mọi trường có hậu tố `_pct` (`budget_used_pct`, `budget.used_pct`, `used_pct`) là **phần trăm** (45.2 → "45,2%"). `cpc`, `cpa`, `cpm` là số VND (có thể lẻ, backend làm tròn 2 chữ số; UI làm tròn khi hiển thị). Mẫu số bằng 0 → `null`.
