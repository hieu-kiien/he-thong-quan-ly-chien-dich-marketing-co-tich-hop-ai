# Khu vực Trợ lý AI (MarketFlow Assistant Workspace)

Tài liệu kỹ thuật mô tả kiến trúc, luồng sự kiện SSE, quản lý trạng thái và các quy ước cho khu vực làm việc Trợ lý AI tại các đường dẫn `/assistant` và `/assistant/:threadId`.

---

## 1. Tổng quan & Thiết kế

Khu vực Trợ lý AI được thiết kế theo mô hình không gian làm việc AI hiện đại (tương tự Claude.ai), tối ưu cho người dùng marketing tại Việt Nam:
- **Ngôn ngữ UI & Thông báo:** 100% tiếng Việt.
- **Phong cách:** Bảng màu trung tính ấm (Warm Stone), phông chữ Be Vietnam Pro, hỗ trợ giao diện sáng/tối (Dark Mode), không dùng gradient, không dùng emoji, không có buzzword.
- **Bố cục 3 cột toàn màn hình (Full-bleed):**
  1. **Cột trái (~260px):** Danh sách phiên làm việc, phân nhóm (Đã ghim, Hôm nay, 7 ngày qua, Cũ hơn), tìm kiếm, đổi tên inline, ghim/bỏ ghim, xoá phiên với hộp thoại xác nhận.
  2. **Cột giữa:** Không gian trò chuyện chính. Bong bóng tin nhắn người dùng căn phải, phản hồi của AI hiển thị toàn chiều rộng bằng markdown chuẩn (`react-markdown` + `remark-gfm`), hỗ trợ bảng dữ liệu, danh sách, và khối mã nguồn có nút sao chép. Khung soạn thảo tự co giãn kèm bộ chọn ngữ cảnh chiến dịch và 5 mẫu gợi ý nhanh.
  3. **Cột phải (~380px):** Panel "Đề xuất & bản nháp", hiển thị danh sách các `ai_action` của phiên theo thời gian thực (live-updated từ SSE). Cho phép người dùng chỉnh sửa tham số (nội dung, kênh, tiêu đề, mục tiêu, số liệu) trước khi bấm **Xác nhận** hoặc **Bỏ qua**.

---

## 2. Giao thức Luồng sự kiện SSE (Server-Sent Events)

Theo quy ước tại `CONTRACT.md` §6 và §11:
- Client sử dụng `fetch` + `ReadableStream` với phương thức `POST`, header `Authorization: Bearer <JWT>` và body JSON (do chuẩn `EventSource` của trình duyệt không hỗ trợ POST).
- Endpoint gửi tin nhắn: `POST /api/v1/assistant/threads/{id}/messages`
- Endpoint tạo lại phản hồi: `POST /api/v1/assistant/messages/{id}/regenerate`
- Hỗ trợ dừng luồng bằng `AbortController` (khi người dùng bấm nút **Dừng**, client đồng thời abort fetch và gọi `POST /api/v1/assistant/threads/{id}/stop`).

### Định dạng các sự kiện SSE:

Mỗi khung sự kiện tuân thủ format: `event: <type>\ndata: <json>\n\n`.

| Event | Data Payload | Ý nghĩa & Xử lý phía Frontend |
|---|---|---|
| `message_start` | `{ user_message: AiMessage \| null, assistant_message: { id, status: "STREAMING" } }` | Khởi tạo tin nhắn người dùng và tin nhắn AI tạm thời trong cache. |
| `status` | `{ phase: "queued" \| "thinking" \| "tool" \| "writing", queue_position?: number }` | Cập nhật dòng trạng thái trực tiếp ("Đang chờ đến lượt...", "Đang suy nghĩ...", "Đang tra cứu dữ liệu...", "Đang viết..."). Có thuộc tính `aria-live="polite"` cho trợ năng (a11y). |
| `text` | `{ content: string }` | **Toàn bộ** nội dung văn bản tích luỹ đến hiện tại (OpenCode phát theo từng part hoàn chỉnh, không phải token delta). Client dùng hook `useTypingReveal` để chỉ hiển thị mượt mà phần đuôi mới thêm vào. |
| `tool_call` | `{ id, name, args, status: "running" \| "done" \| "error", summary? }` | Hiển thị compact row inline trong tin nhắn trợ lý. Có nhãn tiếng Việt (`ASSISTANT_TOOL_LABELS`), biểu tượng xoay khi `running`, dấu tích khi `done`, và accordion mở rộng xem JSON chi tiết. |
| `action` | `AiAction` | Đề xuất hành động mới phát sinh từ tool ghi. Tự động đẩy vào panel "Đề xuất & bản nháp" và hiển thị chip liên kết ngay trong tin nhắn. |
| `message_end` | `{ message: AiMessage }` | Kết thúc lượt sinh. Ghi đè tin nhắn hoàn chỉnh đã lưu DB vào React Query cache, làm mới danh sách phiên. |
| `error` | `{ code: string, message: string }` | Báo lỗi AI (`AI_UNAVAILABLE`, `AI_RATE_LIMITED`, `AI_TIMEOUT`, `AI_EMPTY_RESPONSE`, `AI_INTERNAL`, `THREAD_BUSY`). Hiển thị Callout màu đỏ tiếng Việt kèm nút **Thử lại**. |

---

## 3. Hiệu ứng gõ chữ phía Client (`useTypingReveal`)

- Do backend gửi văn bản tích luỹ (accumulated text) thay vì từng token riêng lẻ, hook `useTypingReveal` đảm nhiệm việc chuyển đổi sự xuất hiện đột ngột của một đoạn văn bản thành hiệu ứng hiển thị từng ký tự mượt mà.
- **Tôn trọng tuỳ chọn người dùng:** Tự động phát hiện `window.matchMedia('(prefers-reduced-motion: reduce)')`. Nếu người dùng bật tuỳ chọn giảm chuyển động trong hệ điều hành, hiệu ứng gõ chữ sẽ được bỏ qua và hiển thị văn bản ngay lập tức.
- Khi luồng stream kết thúc (`message_end` hoặc `stop`), hook lập tức hiển thị 100% văn bản để không làm trễ thao tác đọc của người dùng.

---

## 4. Cơ chế Đề xuất & Duyệt (Human-in-the-Loop)

Tuân thủ nguyên tắc chống "tính năng ảo" (§0):
- AI **không bao giờ** tự ý ghi dữ liệu vào hệ thống.
- Khi AI gọi các công cụ ghi (`propose_content_drafts`, `propose_campaign`, `propose_schedule`, `propose_metrics`), backend tạo bản ghi `ai_action` ở trạng thái `PROPOSED`.
- Trên panel "Đề xuất & bản nháp":
  - `propose_content_drafts`: Hiển thị từng bản nháp với badge kênh, loại nội dung, ô nhập tiêu đề, vùng soạn thảo có bộ đếm ký tự so sánh với gợi ý định dạng của kênh (VD: Facebook < 2.000 ký tự, TikTok < 300 ký tự), lời kêu gọi hành động (CTA), và lựa chọn chế độ gửi: **Gửi duyệt** (`PENDING_REVIEW` - mặc định) hoặc **Lưu nháp** (`DRAFT`).
  - `propose_campaign`: Cho phép sửa tên, mục tiêu, sản phẩm, khoảng thời gian và ngân sách dự kiến.
  - `propose_schedule`: Cho phép chỉnh sửa ngày giờ đăng bài (`datetime-local`) và ghi chú phân công.
  - `propose_metrics`: Cho phép sửa bảng số liệu views, clicks, conversions, cost.
- Khi bấm **Xác nhận**: Client gửi `POST /assistant/actions/{id}/confirm { args: <tham_số_đã_sửa> }`. Sau khi thực thi thành công, thẻ hiển thị liên kết trực tiếp tới thực thể vừa tạo (VD: `/contents/:id`, `/campaigns/:id`, `/calendar`).
- Khi bấm **Bỏ qua**: Client gửi `POST /assistant/actions/{id}/reject`.

---

## 5. Chế độ Mô phỏng khi phát triển (Dev-Only Simulator)

- **Vị trí:** `src/features/assistant/simulator.ts`.
- **Cơ chế kích hoạt:** Chỉ chạy khi:
  ```ts
  import.meta.env.DEV && import.meta.env.VITE_ASSISTANT_SIMULATOR === 'true'
  ```
- **Không rò rỉ dữ liệu giả:** Trong môi trường production build (`import.meta.env.DEV === false`), toàn bộ mã lệnh mô phỏng và dữ liệu mẫu được Rollup / Terser loại bỏ hoàn toàn (tree-shake), không tồn tại trong gói xuất bản `dist/`.
- **Chỉ báo trực quan:** Khi simulator được kích hoạt, thanh tiêu đề hiển thị huy hiệu màu hổ phách: `"Mô phỏng (chỉ dùng khi phát triển)"`.
- **Kịch bản mô phỏng:** Replay đầy đủ chu kỳ: `message_start` → `status (queued)` → `status (thinking)` → `tool_call (running)` → `tool_call (done)` → `action` → `status (writing)` → `text` (3 đợt tích luỹ) → `message_end`.

---

## 6. Cây Thư mục & Cấu trúc Component

```
frontend/src/features/assistant/
├── README.md                     # Tài liệu kiến trúc này
├── types.ts                      # Kiểu dữ liệu UI, nhãn công cụ, mẫu prompt, thông báo lỗi
├── sseClient.ts                  # Typed client SSE (fetch + ReadableStream + abort)
├── simulator.ts                  # Bộ mô phỏng sự kiện dành riêng cho môi trường DEV
├── useTypingReveal.ts            # Hook hiển thị gõ chữ mượt mà phía client
├── useAssistantStream.ts         # Hook điều phối stream, đồng bộ cache React Query
├── AssistantPage.tsx             # Trang chính (bố cục 3 cột full-bleed + responsive drawers)
└── components/
    ├── HeaderBar.tsx             # Thanh tiêu đề, đổi tên phiên, chip chiến dịch, AI status dot
    ├── ThreadList.tsx            # Cột trái: danh sách phiên theo nhóm, tìm kiếm, rename, pin, delete
    ├── ChatView.tsx              # Cột giữa: danh sách tin nhắn, empty state, tự cuộn, nút "Xuống cuối"
    ├── MessageItem.tsx           # Tin nhắn markdown, khối mã có nút sao chép, tool calls, action chips
    ├── ToolCallRow.tsx           # Hàng hiển thị công cụ rút gọn, spinner, accordion JSON chi tiết
    ├── Composer.tsx              # Ô nhập liệu tự co giãn, chọn ngữ cảnh, menu "/" gợi ý nhanh, nút Dừng
    ├── ActionCards.tsx           # Thẻ hiển thị chuyên biệt cho từng loại đề xuất (drafts, campaign, schedule, metrics)
    └── ActionsPanel.tsx          # Panel bên phải / Drawer: danh sách đề xuất, đếm số chờ duyệt
```
