# Phân Hệ Trợ Lý AI — Kiến Trúc, Công Cụ & Tối Ưu Prompt (KT3)

> Học phần: Ứng dụng trí tuệ nhân tạo (AIA331)  
> Hệ thống: MarketFlow v2  
> Đối tượng: Trợ lý Marketing AI (`marketflow`)  
> Căn cứ kỹ thuật: `docs/rebuild/CONTRACT.md`, `docs/rebuild/P0_SPIKE_REPORT.md`, `deploy/opencode/prompts/*`  

---

## 1. Tổng quan & Nguyên tắc cốt lõi

Trợ lý AI trong MarketFlow v2 được thiết kế như một không gian làm việc hội thoại chuyên biệt (route `/assistant`, tương tự Claude.ai), phục vụ đội ngũ tiếp thị của doanh nghiệp vừa và nhỏ (SME) tại Việt Nam.

Hệ thống tuân thủ nghiêm ngặt **Bộ quy tắc chống tính năng ảo (CONTRACT §0)**:
1. **Chỉ gọi là AI khi thực sự gọi LLM**: Toàn bộ phản hồi của Trợ lý AI đều được sinh trực tiếp từ mô hình ngôn ngữ lớn (OpenCode Zen) thông qua OpenCode CLI. Không sử dụng các luật if/else giả danh AI.
2. **Nguyên tắc Chỉ Đề Xuất (Proposal-Only)**: AI **không bao giờ** tự ý ghi dữ liệu vào cơ sở dữ liệu nghiệp vụ. Mọi hành động ghi do AI đề xuất đều được lưu dưới dạng `ai_action` ở trạng thái `PROPOSED`. Người dùng bắt buộc phải bấm **Xác nhận** trên giao diện thì hành động mới được thực thi (thực thi thông qua Service Layer bằng chính quyền hạn của người dùng đó). AI không có quyền tự phê duyệt hay tự đánh dấu xuất bản bài viết.
3. **Trung thực về lỗi**: Khi LLM gặp lỗi (hết hạn mức, quá thời gian, lỗi kết nối), hệ thống báo lỗi thực tế bằng tiếng Việt, không dùng câu trả lời mẫu (template fallback) để giả vờ AI hoạt động.
4. **Không bịa số liệu (Grounding)**: AI chỉ sử dụng dữ liệu được cung cấp trong ngữ cảnh hoặc lấy từ các công cụ tra cứu CSDL. Nếu không có số liệu, AI phải nói rõ là "chưa có dữ liệu", không dự đoán số liệu bịa.

---

## 2. Kiến trúc End-to-End & Giao thức truyền thông

Luồng giao tiếp giữa Trình duyệt, Backend, AI Runner và OpenCode:

```
[ Trình duyệt (React SPA) ]
       │  ▲
       │  │  1. REST POST /api/v1/assistant/threads/:id/messages
       │  │  2. Server-Sent Events (text/event-stream)
       ▼  │
[ FastAPI Backend (:8000) ]
       │  ▲
       │  │  3. POST /run (Header X-Runner-Token, Stream NDJSON)
       ▼  │
[ ai-runner (:8100, user `mfai`) ]
       │
       │  4. Subprocess: opencode run --agent marketflow --format json
       ▼
[ OpenCode CLI ]  ────── 5. Gọi Model ──────>  [ OpenCode Zen (Free LLM) ]
       │                                                 │
       │  6. Gọi MCP Tool (Stateless-HTTP /mcp)           │
       │     (Header Bearer: MF_RUN_TOKEN)               │
       └─────────────────────────────────────────────────┘
```

### 2.1. Xác thực Run-Token cho MCP Server
Để cho phép OpenCode CLI gọi ngược lại các công cụ của Backend một cách an toàn và đúng quyền:
- Khi có request chat từ người dùng, Backend sinh một mã **Run-Token** ngắn hạn (JWT có hiệu lực 10 phút, claim `typ="assistant_run"`, `uid=<user_id>`, `thread_id=<thread_id>`).
- Backend truyền Run-Token này sang `ai-runner` trong trường `env.MF_RUN_TOKEN`.
- Runner thiết lập biến môi trường `MF_RUN_TOKEN` cho tiến trình OpenCode.
- Cấu hình OpenCode (`opencode.json`) khai báo MCP Server dạng HTTP với header uỷ quyền:
  ```json
  {
    "mcpServers": {
      "marketflow": {
        "url": "http://127.0.0.1:8000/mcp",
        "headers": {
          "Authorization": "Bearer {env:MF_RUN_TOKEN}"
        }
      }
    }
  }
  ```
- Khi OpenCode gọi vào `/mcp`, MCP Server giải mã Run-Token, xác định chính xác danh tính người dùng và phiên làm việc, từ đó thực thi công cụ với đúng quyền hạn của người dùng đó.

### 2.2. Khóa bảo mật môi trường (Permission Lockdown)
Để ngăn chặn hoàn toàn nguy cơ Prompt Injection chiếm quyền điều khiển máy chủ VPS, cấu hình agent tại `deploy/opencode/agent/marketflow.md` áp dụng mẫu khoá phân quyền nghiêm ngặt đã kiểm chứng tại Spike P0:
```yaml
---
description: Trợ lý Marketing AI của MarketFlow
mode: primary
permission:
  "*": deny
  read: {"*": deny, "/__mf_never__/x": allow}
  glob: {"*": deny, "/__mf_never__/x": allow}
  grep: {"*": deny, "/__mf_never__/x": allow}
  list: {"*": deny, "/__mf_never__/x": allow}
  external_directory: deny
  "marketflow_*": allow
---
```
- Khóa toàn bộ các công cụ built-in nguy hiểm: `bash`, `edit`, `webfetch`, `websearch`, `task`.
- Các công cụ đọc tệp (`read`, `glob`, `grep`, `list`) được chuyển hướng tới đường dẫn giả lập `/__mf_never__/x` để vô hiệu hoá hoàn toàn việc đọc tệp hệ thống (`/etc/passwd`, file cấu hình `.env`, mã nguồn) mà không kích hoạt lỗi `FreeTierError` của Zen.
- Chỉ duy nhất các công cụ có tiền tố `marketflow_*` được phép thực thi.

---

## 3. Danh mục Công cụ MCP (Tool Registry)

Các công cụ được khai báo tại `backend/app/assistant/tools.py` và đăng ký vào MCP Server:

### 3.1. Nhóm công cụ Đọc (Read Tools - Thực thi ngay lập tức)

| Tên công cụ | Tham số đầu vào | Mô tả & Ràng buộc bảo mật |
|---|---|---|
| `list_campaigns` | `q`, `status`, `channel_code`, `date_from`, `date_to`, `limit` | Tra cứu danh sách chiến dịch theo quyền người dùng. Lọc theo khoảng thời gian giao nhau. |
| `get_campaign` | `campaign_id` | Lấy chi tiết chiến dịch, danh sách kênh phân bổ và tổng hợp chỉ số hiệu quả (views, clicks, conversions, cost, CTR, CPA). |
| `get_stats` | `campaign_id`, `channel_code`, `date_from`, `date_to`, `group_by` | Lấy số liệu thống kê tổng quan (`overview`), theo kênh (`channel`), theo chiến dịch (`campaign`), hoặc chuỗi thời gian (`day`, `week`, `month`). |
| `list_contents` | `campaign_id`, `channel_code`, `status`, `q`, `limit` | Liệt kê các bài viết và trạng thái kiểm duyệt trong hệ thống. |
| `get_content` | `content_id` | Xem chi tiết nội dung, lịch sử phê duyệt và liên kết xuất bản. |
| `list_schedules` | `date_from`, `date_to`, `campaign_id` | Xem danh sách lịch đăng bài theo khoảng thời gian. |
| `list_channels` | Không | Lấy danh mục 7 kênh tiếp thị kèm quy tắc định dạng ký tự. |
| `get_brand_profile` | Không | Lấy thông tin hồ sơ thương hiệu (giọng văn, khách hàng mục tiêu, tôn chỉ) và danh sách từ cấm. |
| `check_banned_keywords` | `text` | Kiểm tra nhanh một đoạn văn bản có vi phạm danh sách từ cấm hay không. |

### 3.2. Nhóm công cụ Ghi (Propose Tools - Chỉ tạo Đề xuất)

Mọi công cụ ghi chỉ tạo bản ghi `ai_action` ở trạng thái `PROPOSED` và trả về thông báo cho AI: *"Đã tạo đề xuất #id, chờ người dùng xác nhận trên giao diện"*.

| Tên công cụ | Tham số đầu vào | Kết quả đề xuất (`args_json`) |
|---|---|---|
| `propose_content_drafts` | `items: [{campaign_id, channel_code, content_type, title, body, cta, status}]` | Đề xuất một hoặc nhiều bản nháp nội dung. `status` cho phép chọn `PENDING_REVIEW` (Gửi duyệt - mặc định) hoặc `DRAFT` (Lưu nháp). |
| `propose_campaign` | `name, goal, objective, target_audience, product, start_date, end_date, budget, channels` | Đề xuất tạo chiến dịch tiếp thị mới kèm ngân sách phân bổ từng kênh. |
| `propose_campaign_update` | `campaign_id, fields...` | Đề xuất cập nhật thông tin hoặc ngân sách chiến dịch đã có. |
| `propose_schedule` | `content_id, scheduled_at, note` | Đề xuất lên lịch xuất bản cho một bài viết đã duyệt. |
| `propose_metrics` | `rows: [{campaign_id, channel_code, metric_date, views, clicks, conversions, cost}]` | Đề xuất nhập số liệu hiệu quả khi người dùng dán số liệu thô vào khung chat. |

---

## 4. Giao thức Luồng sự kiện SSE (Server-Sent Events)

Kết nối giữa Trình duyệt và Backend tại `POST /api/v1/assistant/threads/{id}/messages` sử dụng chuẩn SSE định dạng `event: <type>\ndata: <json>\n\n`:

| Sự kiện (`event`) | Dữ liệu (`data`) | Ý nghĩa & Phản hồi giao diện |
|---|---|---|
| `message_start` | `{user_message, assistant_message}` | Khởi tạo tin nhắn người dùng và tin nhắn AI tạm thời (`status: STREAMING`). |
| `status` | `{phase, queue_position?}` | Thông báo trạng thái xử lý trực tiếp (`queued`, `thinking`, `tool`, `writing`). |
| `text` | `{content}` | Toàn bộ văn bản markdown tích luỹ đến hiện tại (hỗ trợ hiệu ứng Typing Reveal phía client). |
| `tool_call` | `{id, name, args, status, summary}` | Hiển thị hàng công cụ rút gọn: biểu tượng xoay khi `running`, dấu tích khi `done`, cho phép mở rộng xem JSON. |
| `action` | `AiAction` | Đề xuất hành động mới. Tự động xuất hiện thẻ hành động trên panel bên phải để người dùng xem và bấm Xác nhận. |
| `message_end` | `{message}` | Hoàn tất lượt sinh, lưu trữ tin nhắn cuối cùng vào cơ sở dữ liệu. |
| `error` | `{code, message}` | Báo lỗi chuẩn hoá (`AI_RATE_LIMITED`, `AI_TIMEOUT`, `AI_EMPTY_RESPONSE`, `AI_UNAVAILABLE`). |

---

## 5. Kỹ thuật Prompt Engineering qua 3 Vòng Thử Nghiệm (Rubric KT3)

Quá trình phát triển Prompt được lưu trữ tại `deploy/opencode/prompts/` và đánh giá tự động bằng kịch bản `scripts/evaluate_assistant.py`:

```
deploy/opencode/prompts/
├── CHANGELOG.md          # Nhật ký chi tiết sự thay đổi qua các phiên bản
├── v1.md                 # Phiên bản 1 (Baseline)
├── v2.md                 # Phiên bản 2 (Guardrails & Grounding)
└── v3.md                 # Phiên bản 3 (Production-Ready)
```

### 5.1. So sánh chi tiết 3 phiên bản Prompt

| Tiêu chí | Phiên bản 1 (v1.md) | Phiên bản 2 (v2.md) | Phiên bản 3 (v3.md) |
|---|---|---|---|
| **Định danh & Vai trò** | Trợ lý Marketing AI chung chung. | Trợ lý Marketing AI của MarketFlow phục vụ SME Việt Nam. | Trợ lý Marketing AI chuyên nghiệp, nhận biết ngữ cảnh người dùng và chiến dịch liên kết. |
| **Kiểm soát ảo giác số liệu (Grounding)** | Không có ràng buộc. Tự bịa số liệu tăng trưởng (+25%, +300%) khi thiếu dữ liệu. | Rào chắn cấm bịa số. Chỉ dùng số liệu do công cụ trả về; thiếu thì báo "chưa có dữ liệu". | Chuẩn hoá công thức tính toán (CTR, CVR, CPC, CPA), xử lý mẫu số 0 thành "—", căn cứ vào dữ liệu thật từ công cụ. |
| **Ranh giới đề xuất (Proposal Boundary)** | Nhầm lẫn: Tự tuyên bố đã duyệt bài và đã đăng bài thành công lên Facebook. | Quy định rõ AI chỉ tạo bản ghi `PROPOSED`, yêu cầu người dùng xác nhận. | Hướng dẫn rõ ràng người dùng xem và chỉnh sửa tại panel "Đề xuất & bản nháp" bên phải màn hình. |
| **Rào chắn từ cấm (Banned Keywords)** | Hay dùng từ giật gân ("cam kết 100%", "đẳng cấp số 1", "rẻ nhất thị trường"). | Nhắc nhở tuân thủ từ cấm thương hiệu. | Tích hợp kiểm tra từ cấm tự động qua công cụ và tránh dùng từ ngữ cam kết sai sự thật. |
| **Quy chuẩn định dạng kênh** | Không phân biệt định dạng giữa các kênh; bài TikTok viết dài dòng như bài blog. | Bắt đầu phân biệt kênh nhưng cấu trúc còn sơ sài. | Quy chuẩn chuyên sâu: Facebook (hook 2 dòng đầu, CTA, 3-5 hashtag), TikTok (kịch bản video [Hook 0-3s], [Nội dung], [CTA]), Email (subject < 60 ký tự, 1 CTA duy nhất). |

### 5.2. Công Cụ Đánh Giá Tự Động & Trạng Thái Thực Nghiệm

Để đánh giá chất lượng prompt một cách khách quan, hệ thống xây dựng công cụ `scripts/evaluate_assistant.py` cùng bộ 8 ca kiểm thử tại `scripts/eval_cases.json`.

1. **Chế độ Tự kiểm tra bộ chấm điểm (`--dry-run`)**:
   - `scripts/evaluate_assistant.py --dry-run` sử dụng các chuỗi phản hồi mẫu viết tay (fixtures) nhằm mục đích tự kiểm tra bộ chấm điểm (harness self-test): xác minh các hàm kiểm tra từ cấm, ảo giác số liệu, giới hạn ký tự và phòng thủ injection hoạt động chính xác.
   - **Lưu ý về tính trung thực (CONTRACT §0)**: Các chuỗi phản hồi trong `--dry-run` là phản hồi mẫu viết tay phục vụ CI và test harness, **KHÔNG PHẢI là kết quả đo lường từ mô hình AI thật**.
2. **Đánh giá Thực nghiệm trên Mô hình Thật (VPS)**:
   - **Trạng thái:** *Chưa chạy — sẽ cập nhật sau khi triển khai thực tế trên VPS*.
   - Kịch bản chạy live trực tiếp với OpenCode CLI trên máy chủ VPS:
     ```bash
     python3 scripts/evaluate_assistant.py --engine opencode --all-versions --no-tools
     ```
   - Số liệu đo lường thực tế từ mô hình (tỷ lệ đạt, văn phong tiếng Việt, khả năng grounding số liệu) sẽ được ghi nhận và cập nhật vào bảng kết quả sau khi thực thi trên môi trường VPS.

---

## 6. Xử lý Lỗi & Giới hạn của Hệ thống AI

Hệ thống thiết kế cơ chế bọc lỗi toàn diện, ánh xạ các sự cố kỹ thuật thành mã lỗi chuẩn hoá và thông báo tiếng Việt rõ ràng:

| Tình huống sự cố | Mã lỗi hệ thống | Cách thức xử lý & Phản hồi |
|---|---|---|
| **Vượt quá thời gian (Timeout)** | `AI_TIMEOUT` | Runner áp dụng timeout cứng 180s (`RUNNER_TIMEOUT_S`). Nếu quá hạn, tiến trình OpenCode bị huỷ ngay lập tức bằng `SIGKILL` theo process group. Giao diện hiển thị: *"Yêu cầu xử lý vượt quá thời gian cho phép. Bạn vui lòng thử lại với yêu cầu ngắn hơn."* |
| **Hết hạn mức gọi AI (Rate Limit)** | `AI_RATE_LIMITED` | Runner bắt chuỗi `FreeTierError` / HTTP 429 từ OpenCode Zen. Tự động chuyển đổi sang mô hình dự phòng (`glm-5.3-flash-free`). Nếu tất cả đều bận, trả về lỗi: *"Dịch vụ AI miễn phí đang tạm thời quá tải hoặc hết hạn mức. Vui lòng thử lại sau vài phút."* |
| **Phản hồi rỗng (Empty Response)** | `AI_EMPTY_RESPONSE` | Khi OpenCode kết thúc mà không sinh ra nội dung văn bản nào. Giao diện hiển thị thông báo yêu cầu thử lại kèm nút Tạo lại (Regenerate). |
| **Mất kết nối Runner** | `AI_UNAVAILABLE` | Khi Backend không thể kết nối tới cổng 8100 của `ai-runner`. Backend ghi log cảnh báo và trả về lỗi: *"Dịch vụ AI Runner nội bộ hiện không khả dụng."* |
| **Phiên đang bận** | `THREAD_BUSY` | Mỗi phiên chat chỉ cho phép 1 lượt sinh tại một thời điểm (HTTP 409). Ngăn chặn xung đột trạng thái dữ liệu. |

---

## 7. Quy trình Phê duyệt của Con người (Human-in-the-Loop)

1. Khi AI sinh đề xuất (ví dụ `propose_content_drafts`), một thẻ đề xuất trực quan xuất hiện tại panel bên phải của giao diện.
2. Thẻ đề xuất cho phép người dùng:
   - Xem trước tiêu đề, nội dung, kênh đăng, lời kêu gọi hành động (CTA).
   - Kiểm tra bộ đếm ký tự so với giới hạn định dạng của kênh.
   - **Chỉnh sửa trực tiếp** các tham số (sửa tiêu đề, viết lại đoạn văn) ngay trên thẻ.
   - Chọn chế độ gửi: **Gửi duyệt** (`PENDING_REVIEW` - mặc định) hoặc **Lưu nháp** (`DRAFT`).
3. Khi người dùng bấm **Xác nhận**:
   - Trình duyệt gửi `POST /api/v1/assistant/actions/{id}/confirm { args: <tham_số_đã_sửa> }`.
   - Backend gọi `content_service.create_content` bằng thông tin xác thực của chính người dùng đó.
   - Bản ghi nội dung thật được tạo trong bảng `contents` với nhãn `origin=AI` và liên kết tới tin nhắn AI (`ai_message_id`).
   - Thẻ đề xuất chuyển trạng thái thành `EXECUTED` kèm đường dẫn trực tiếp tới bài viết mới tạo.
4. Khi người dùng bấm **Bỏ qua**:
   - Trình duyệt gửi `POST /api/v1/assistant/actions/{id}/reject`. Thẻ chuyển trạng thái `REJECTED` và không có dữ liệu nào được ghi vào bảng nghiệp vụ.

---

## 8. Những hạn chế thực tế (Honest Limitations)

1. **Hạn mức tài nguyên miễn phí (Free Tier Rate Limits)**: Hệ thống sử dụng hạ tầng OpenCode Zen miễn phí, có thể bị giới hạn tần suất gọi vào các khung giờ cao điểm.
2. **Không tự động đăng bài lên mạng xã hội**: Hệ thống không tích hợp API tự động đăng bài (tránh rủi ro tài khoản bị khoá và tuân thủ nguyên tắc không giả lập bên ngoài). Lịch đăng bài đóng vai trò kế hoạch và nhắc việc; nhân viên tự đăng bài và cập nhật liên kết xác nhận.
3. **Giới hạn đồng thời trên máy chủ đơn**: Do mỗi tiến trình OpenCode tiêu thụ ~490 MB RAM RSS, máy chủ VPS (2GB RAM) được cấu hình giới hạn đồng thời `RUNNER_CONCURRENCY=1`. Nếu nhiều người cùng gửi yêu cầu, các yêu cầu sau sẽ phải xếp hàng chờ trong hàng đợi tuần tự (tối đa 8 vị trí).
