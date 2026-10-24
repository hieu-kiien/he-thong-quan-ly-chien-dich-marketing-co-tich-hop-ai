# MarketFlow AI Runner Service

Dịch vụ nội bộ (Internal Service) thực thi OpenCode CLI cho Trợ lý Marketing AI MarketFlow v2.
Tuân thủ chặt chẽ đặc tả thiết kế tại `docs/rebuild/CONTRACT.md` (§7 & §11).

---

## 1. Vai trò trong kiến trúc

```
Browser (React SPA)
  │  REST JSON + SSE (/api/v1/assistant/threads/:id/messages)
  ▼
FastAPI Backend (marketflow-api, :8000) ── PostgreSQL
  │  ▲
  │  │ MCP streamable-HTTP /mcp (Bearer run-token, OpenCode gọi ngược)
  ▼  │
ai-runner (marketflow-ai-runner, :8100, user mfai)
  │ spawn mỗi lượt: opencode run --agent marketflow [-s <session>] --format json
  ▼
OpenCode CLI → OpenCode Zen (Model miễn phí: big-pickle / glm-5.3-flash-free)
```

1. **Quản lý hàng đợi & Bộ nhớ**: Giới hạn số lượng tiến trình OpenCode đồng thời (`RUNNER_CONCURRENCY=1`, mặc định) nhằm bảo vệ máy chủ VPS 2 vCPU / 2GB RAM khỏi cạn kiệt bộ nhớ (mỗi tiến trình OpenCode chiếm ~490 MB RSS).
2. **Quản lý vòng đời tiến trình**: Khởi tạo tiến trình với process group riêng, xử lý timeout cứng và hủy ngay toàn bộ nhóm tiến trình (`SIGKILL`) khi client ngắt kết nối hoặc có yêu cầu abort.
3. **Chuyển đổi giao thức**: Nhận JSON stream từ stdout của OpenCode (`--format json`), phân tích cú pháp và chuẩn hóa thành luồng NDJSON (`application/x-ndjson`) với các mã sự kiện: `run`, `queued`, `session`, `text`, `tool`, `done`, `error`.
4. **Phân loại lỗi chuẩn hóa**: Tự động nhận diện lỗi `FreeTierError` / 429 → `AI_RATE_LIMITED`, lỗi timeout → `AI_TIMEOUT`, phản hồi rỗng → `AI_EMPTY_RESPONSE`, lỗi kết nối → `AI_UNAVAILABLE`.
5. **Cơ chế Fallback & Tự phục hồi**:
   - Khi gặp lỗi rate-limit hoặc lỗi model, tự động chuyển sang model dự phòng tiếp theo trong danh sách `OPENCODE_FALLBACK_MODELS`.
   - Khi phiên làm việc không tồn tại (`Session not found`), tự động thử lại 1 lần mà không kèm session_id và phát session_id mới.

---

## 2. Biến môi trường cấu hình (Configuration)

| Tên biến | Mặc định | Mô tả |
|---|---|---|
| `RUNNER_TOKEN` | `""` | Mã bí mật chia sẻ; nếu cấu hình, mọi request tới `/run` và `/abort` bắt buộc gửi header `X-Runner-Token`. |
| `OPENCODE_BIN` | `opencode` | Đường dẫn tới tệp thực thi OpenCode (hoặc script Python giả lập trong unit tests). |
| `RUNNER_SANDBOX_DIR` | `.` | Thư mục làm việc cách ly, chỉ đọc, chứa `.opencode/agent/marketflow.md` và `opencode.json`. |
| `OPENCODE_AGENT` | `marketflow` | Tên agent được chỉ định khi chạy (`--agent marketflow`). |
| `OPENCODE_MODEL` | `""` | Model OpenCode chỉ định (ví dụ: `opencode/big-pickle`). Bỏ trống để dùng mặc định của OpenCode. |
| `OPENCODE_FALLBACK_MODELS` | `""` | Danh sách model dự phòng cách nhau bởi dấu phẩy (ví dụ: `opencode/glm-5.3-flash-free,opencode/deepseek-v4.1-flash-free`). |
| `RUNNER_TIMEOUT_S` | `180.0` | Thời gian tối đa (giây) cho một lượt phản hồi trước khi bị ngắt. |
| `RUNNER_CONCURRENCY` | `1` | Số lượt chạy đồng thời tối đa (khuyến nghị 1 trên VPS 2GB RAM). |
| `RUNNER_MAX_QUEUE` | `8` | Số lượng request tối đa trong hàng đợi chờ trước khi trả về lỗi `AI_BUSY`. |
| `RUNNER_MAX_PROMPT_CHARS` | `60000` | Giới hạn số ký tự tối đa của prompt gửi lên. |
| `RUNNER_KILL_GRACE_S` | `3.0` | Thời gian chờ từ khi gửi `SIGTERM` đến khi cưỡng chế bằng `SIGKILL`. |
| `RUNNER_HOST` | `127.0.0.1` | Địa chỉ IP dịch vụ lắng nghe (nội bộ). |
| `RUNNER_PORT` | `8100` | Cổng HTTP của dịch vụ runner. |

---

## 3. Chi tiết API Endpoints

### 3.1. `GET /health`
Kiểm tra tình trạng hoạt động nhanh (không gọi tới mô hình LLM).

**Response (200 OK):**
```json
{
  "ok": true,
  "opencode_version": "1.19.0",
  "model": "opencode/big-pickle",
  "queue_length": 0,
  "active": 0,
  "last_error": null
}
```

### 3.2. `POST /run`
Khởi chạy một lượt tương tác với OpenCode và stream kết quả dưới dạng NDJSON.

**Headers:**
- `X-Runner-Token`: `<RUNNER_TOKEN>` (nếu được thiết lập)
- `X-Run-Id`: `<run_id>` (tùy chọn)

**Request Body:**
```json
{
  "prompt": "Cho tôi số liệu chiến dịch #5",
  "session_id": "ses_abc123",
  "env": {
    "MF_RUN_TOKEN": "<jwt_token_10m>"
  },
  "timeout_s": 120,
  "model": "opencode/big-pickle"
}
```

**Stream NDJSON Events:**
- `{"type": "run", "run_id": "..."}`
- `{"type": "queued", "position": 1}`
- `{"type": "session", "id": "ses_..."}`
- `{"type": "text", "text": "Số liệu chiến dịch..."}` (toàn bộ nội dung part hoàn chỉnh)
- `{"type": "tool", "id": "call_1", "name": "get_campaign_stats", "status": "done", "input": {"campaign_id": 5}, "output": "..."}` (đã bỏ tiền tố `marketflow_`)
- `{"type": "done", "model": "opencode/big-pickle", "latency_ms": 3200, "tokens": {"total": 2048}}`
- `{"type": "error", "code": "AI_RATE_LIMITED", "message": "Dịch vụ AI miễn phí đang bị giới hạn...", "detail": "..."}`

### 3.3. `POST /abort`
Dừng khẩn cấp một lượt chạy đang hoạt động hoặc đang chờ trong hàng đợi.

**Headers:**
- `X-Runner-Token`: `<RUNNER_TOKEN>`

**Request Body:**
```json
{
  "run_id": "run_xyz456"
}
```

**Response (200 OK):**
```json
{
  "ok": true,
  "run_id": "run_xyz456"
}
```

---

## 4. Chạy kiểm thử (Unit Tests)

Bộ kiểm thử sử dụng kịch bản Python giả lập OpenCode (`fake_opencode.py`), phát lại các fixture JSONL thực tế ghi nhận từ máy chủ:

```bash
pytest ai-runner/tests -v
```
