# KỊCH BẢN THUYẾT TRÌNH BẢO VỆ ĐỒ ÁN KẾT THÚC MÔN HỌC (7 PHÚT)

- **Học phần:** AIA331 — Công nghệ phần mềm ứng dụng AI
- **Mã đề tài:** 80300 — *Hệ thống quản lý chiến dịch marketing có tích hợp AI (MarketFlow AI)*
- **Cấu trúc thời lượng:** **07:00 thuyết trình trên Slide** (tích hợp sẵn **4 Video Product Demo 60fps chạy lặp liên tục** trực tiếp trên Slide 5, 6, 8, 10) + **02:00 – 03:00 Demo tương tác trực tiếp / Trả lời Hội đồng**.
- **Phím tắt điều khiển trên Slide (`slides/index.html`):**
  - `→` / `Space` / Click phải: Chuyển slide kế tiếp
  - `←`: Quay lại slide trước
  - `F`: Bật/tắt chế độ Toàn màn hình (Fullscreen 16:9)
  - `N`: Bật/tắt khung nhắc bài (Speaker Notes & Đồng hồ đếm giờ 7 phút)
  - `T`: Bắt đầu / Tạm dừng đồng hồ bấm giờ 7 phút

---

## Phân bổ thời gian 12 Slide (Tổng: 07:00)

| Slide | Chủ đề | Thời lượng | Mốc đồng hồ | Điểm nhấn thị giác / Video chạy lặp |
| :---: | :--- | :---: | :---: | :--- |
| **01** | Trang bìa: MarketFlow AI (Đề tài 80300) | `00:25` | `00:00 – 00:25` | Editorial Cover + Thông tin học phần AIA331 |
| **02** | Bài toán thực tiễn & 3 điểm nghẽn SME | `00:35` | `00:25 – 01:00` | 3 thẻ bài toán: Phân mảnh dữ liệu, Rủi ro duyệt bài, Ảo giác AI |
| **03** | Mục tiêu & Phạm vi hệ thống | `00:30` | `01:00 – 01:30` | Ma trận RBAC 2 vai trò (`MANAGER` / `MARKETER`) & 7 kênh tiếp thị |
| **04** | Kiến trúc tổng thể & Cô lập tiến trình AI | `00:40` | `01:30 – 02:10` | Sơ đồ kiến trúc 3 tầng: React SPA $\leftrightarrow$ FastAPI/FastMCP $\leftrightarrow$ AI Runner |
| **05** | **[VIDEO LOOP 1]** Quản trị Chiến dịch & KPI đa kênh | `00:45` | `02:10 – 02:55` | `loop-01-dashboard-kpi.mp4`: Dashboard KPI + Nhập CSV 2 bước |
| **06** | **[VIDEO LOOP 2]** Luồng Phê duyệt 4 mắt (HITL) | `00:45` | `02:55 – 03:40` | `loop-02-hitl-approval.mp4`: Từ khóa cấm + Duyệt 4 mắt + Lịch đăng |
| **07** | Kiến trúc Trợ lý AI: 14 công cụ FastMCP & Proposal-Only | `00:35` | `03:40 – 04:15` | 10 công cụ Đọc + 4 công cụ Đề xuất + Token HMAC-SHA256 10 phút |
| **08** | **[VIDEO LOOP 3]** Trợ lý AI Thực chiến & Thẻ Đề xuất | `00:50` | `04:15 – 05:05` | `loop-03-ai-copilot-mcp.mp4`: SSE Streaming + MCP Tools + Bấm Xác nhận |
| **09** | Tối ưu hóa Prompt & Đánh giá thực nghiệm (20 kịch bản) | `00:35` | `05:05 – 05:40` | Biểu đồ tiến hóa 4 giai đoạn Prompt (Điểm chất lượng `54,0` $\rightarrow$ `97,1`) |
| **10** | **[VIDEO LOOP 4]** Kiểm thử tự động & Phòng thủ Red-Team | `00:35` | `05:40 – 06:15` | `loop-04-guardrails-eval.mp4`: Chặn Prompt Injection + 151 bài test |
| **11** | Ứng dụng AI có trách nhiệm trong SDLC & Đạo đức AI | `00:25` | `06:15 – 06:40` | 6 giai đoạn SDLC + Minh bạch dữ liệu & Kiểm soát GitNexus |
| **12** | Kết luận, Đóng góp & Hướng phát triển | `00:20` | `06:40 – 07:00` | Tổng kết 4 giá trị cốt lõi & Sẵn sàng chuyển sang hỏi đáp / Live Demo |

---

## Lời thoại chi tiết từng Slide

### Slide 01 — Trang bìa (`00:00 – 00:25` | 25 giây)
> "Kính chào Thầy/Cô trong Hội đồng chấm đồ án học phần Công nghệ phần mềm ứng dụng AI — AIA331. Em xin trình bày đề tài mã số **80300**: **Hệ thống quản lý chiến dịch marketing có tích hợp AI — MarketFlow AI**. Trong 7 phút tới, em xin đi xuyên suốt từ bài toán thực tiễn, kiến trúc cô lập an toàn cho AI, quy trình kiểm chứng thực nghiệm và minh họa trực quan qua 4 video sản phẩm chạy thực tế ngay trên slide."

### Slide 02 — Bài toán thực tiễn & 3 điểm nghẽn (`00:25 – 01:00` | 35 giây)
> "Khi khảo sát quy trình vận hành marketing tại các doanh nghiệp vừa và nhỏ tại Việt Nam, nhóm nhận thấy 3 điểm nghẽn lớn:
> 1. **Phân mảnh công cụ:** Kế hoạch nằm trên bảng tính, bài viết trên Docs, còn số liệu quảng cáo nằm rời rạc ở nhiều tệp CSV khác nhau.
> 2. **Thiếu rào chắn kiểm duyệt:** Nhân sự dễ sử dụng từ ngữ phóng đại vi phạm quy định quảng cáo hoặc tự đăng bài khi chưa qua cấp quản lý.
> 3. **Ảo giác khi dùng AI rời rạc:** Khi dùng công cụ trò chuyện AI bên ngoài, mô hình không nắm được số liệu KPI thực tế của chiến dịch và có nguy cơ bịa đặt con số."

### Slide 03 — Mục tiêu & Phạm vi hệ thống (`01:00 – 01:30` | 30 giây)
> "Để giải quyết triệt để 3 vấn đề trên, **MarketFlow AI** được xây dựng như một nền tảng quản trị tập trung trên **7 kênh tiếp thị** chuẩn hóa gồm Facebook, Instagram, TikTok, Google Ads, Email, Website/Blog và Zalo OA. Hệ thống phân quyền chặt chẽ theo 2 vai trò: **Nhân viên Marketing (MARKETER)** phụ trách soạn thảo, đề xuất; và **Quản lý Marketing (MANAGER)** chịu trách nhiệm phê duyệt, kiểm soát ngân sách và cấu hình hồ sơ thương hiệu."

### Slide 04 — Kiến trúc tổng thể & Cô lập tiến trình AI (`01:30 – 02:10` | 40 giây)
> "Điểm cốt lõi trong thiết kế kiến trúc của đồ án là **tách biệt hoàn toàn tiến trình AI Runner** khỏi máy chủ nghiệp vụ FastAPI:
> - Tầng giao diện **React 18 TypeScript** giao tiếp với **FastAPI** qua REST API và luồng sự kiện thời gian thực **Server-Sent Events (SSE)**.
> - Tiến trình **AI Runner** chạy trong một hộp cát độc lập, bị tắt toàn bộ quyền thực thi lệnh hệ thống (`bash: false`, `write: false`, `edit: false`), và chỉ được phép truy xuất dữ liệu nghiệp vụ thông qua giao thức chuẩn **FastMCP** với mã xác thực **HMAC-SHA256** tự hủy sau 10 phút."

### Slide 05 — [VIDEO LOOP 1] Quản trị Chiến dịch & Nhập số liệu CSV 2 bước (`02:10 – 02:55` | 45 giây)
> *(Video `loop-01-dashboard-kpi.mp4` tự động chạy lặp trên khung phải)*
> "Trên màn hình là video vận hành thực tế của phân hệ Quản lý Chiến dịch và KPI:
> - Hệ thống tự động tổng hợp Lượt hiển thị, Lượt bấm, Chuyển đổi và Chi phí thực tế từ cơ sở dữ liệu, đồng thời tự động suy diễn các chỉ số dẫn xuất **CTR, CVR, CPC và CPA** để loại bỏ sai số nhập liệu.
> - Đặc biệt, quy trình **Nhập CSV 2 bước (Preview $\rightarrow$ Commit)** giúp kiểm tra ràng buộc logic `Conversions <= Clicks <= Views` trên từng dòng, tự động bóc tách và cảnh báo các dòng lỗi trước khi Quản lý bấm xác nhận ghi vào cơ sở dữ liệu."

### Slide 06 — [VIDEO LOOP 2] Luồng Phê duyệt 4 mắt & Rào chắn Thương hiệu (`02:55 – 03:40` | 45 giây)
> *(Video `loop-02-hitl-approval.mp4` tự động chạy lặp trên khung phải)*
> "Tiếp theo là luồng kiểm duyệt nội dung có sự tham gia của con người (**Human-in-the-Loop**):
> - Ngay khi nhân sự bấm **Gửi duyệt**, hệ thống tự động quét đối chiếu với danh mục **Từ khóa cấm** của thương hiệu như *'cam kết 100%'* hay *'trị dứt điểm'* để cảnh báo tức thì.
> - Tại **Hàng đợi duyệt bài**, hệ thống áp dụng quy tắc **Kiểm soát 4 mắt (Four-Eyes Principle)**: chặn tuyệt đối hành vi tự duyệt bài do chính mình tạo (`CANNOT_REVIEW_OWN`) và ghi lại toàn bộ lịch sử phê duyệt vào bảng **Nhật ký kiểm toán bất biến (Audit Logs)**."

### Slide 07 — Kiến trúc Trợ lý AI: 14 công cụ FastMCP & Ranh giới Chỉ Đề Xuất (`03:40 – 04:15` | 35 giây)
> "Thay vì để mô hình ngôn ngữ lớn tự ý ghi vào cơ sở dữ liệu, MarketFlow AI thiết kế máy chủ **FastMCP gồm đúng 14 công cụ**:
> - **10 công cụ chỉ đọc (Read-only)** giúp AI tra cứu Hồ sơ thương hiệu, KPI thực tế của từng chiến dịch và quét từ khóa cấm.
> - **4 công cụ khởi tạo đề xuất (`propose_*`)** chỉ được phép tạo các bản ghi ở trạng thái `PROPOSED`. AI tuyệt đối không có bất kỳ công cụ nào để xóa dữ liệu, tự duyệt bài hay tự xuất bản."

### Slide 08 — [VIDEO LOOP 3] Trợ lý AI Thực chiến & Thẻ Đề xuất (`04:15 – 05:05` | 50 giây)
> *(Video `loop-03-ai-copilot-mcp.mp4` tự động chạy lặp trên khung phải)*
> "Video trên slide minh họa trọn vẹn một lượt tương tác với Trợ lý AI từ chiến dịch **Cold Brew**:
> - Khi người dùng yêu cầu phân tích KPI và soạn bài đăng Facebook, giao diện hiển thị trực tiếp tiến trình AI gọi lần lượt các công cụ `get_brand_profile`, `get_stats`, `check_banned_keywords` và `propose_content_drafts` qua luồng SSE.
> - Kết quả đề xuất xuất hiện dưới dạng **Thẻ Đề Xuất (`PROPOSED`)** ở cột bên phải. Người dùng có thể chỉnh sửa trực tiếp tiêu đề hoặc lời kêu gọi hành động, sau đó bấm **Xác nhận** để chính thức chuyển thành bản nháp trong hệ thống."

### Slide 09 — Tối ưu hóa Prompt & Đánh giá thực nghiệm (`05:05 – 05:40` | 35 giây)
> "Để đảm bảo chất lượng đầu ra của AI, nhóm đã thực hiện **4 giai đoạn tối ưu hóa System Prompt** trên bộ **20 kịch bản kiểm thử chuẩn**:
> - Ở **Bản 1 (Cơ sở)**, điểm chất lượng tổng hợp chỉ đạt **54,0/100** do mô hình còn tự bịa số liệu KPI và vi phạm từ khóa cấm.
> - Sau khi bổ sung rào chắn công cụ MCP, quy tắc tính chỉ số dẫn xuất và ép kiểm tra `check_banned_keywords` ở **Bản 4 (Production)**, tỷ lệ gọi đúng công cụ đạt **100%**, tỷ lệ chặn từ khóa cấm và chống Prompt Injection đạt **100%**, nâng điểm tổng hợp lên **97,1/100**."

### Slide 10 — [VIDEO LOOP 4] Kiểm thử tự động 3 tầng & Phòng thủ Red-Team (`05:40 – 06:15` | 35 giây)
> *(Video `loop-04-guardrails-eval.mp4` tự động chạy lặp trên khung phải)*
> "Về kiểm thử phần mềm, toàn bộ hệ thống đã vượt qua **151 kịch bản kiểm thử tự động** gồm **104 bài kiểm thử Backend Pytest**, **18 bài kiểm thử AI-Runner** và **29 kịch bản Playwright E2E** trên trình duyệt thật.
> - Như Thầy/Cô thấy trên video bên phải, khi thử nghiệm tấn công **Prompt Injection** yêu cầu đọc tệp `/etc/passwd` và tự động duyệt bài, Trợ lý AI lập tức từ chối nhờ cơ chế **No-Shell Sandbox** và ranh giới **Proposal-Only**."

### Slide 11 — Ứng dụng AI có trách nhiệm trong SDLC & Đạo đức AI (`06:15 – 06:40` | 25 giây)
> "Xuyên suốt 6 giai đoạn phát triển phần mềm (SDLC), nhóm áp dụng nguyên tắc **Con người làm chủ kiến trúc**: sử dụng đồ thị mã nguồn **GitNexus** để phân tích phạm vi ảnh hưởng trước khi chỉnh sửa, viết kiểm thử tự động cho mọi định tuyến API, và tuân thủ nghiêm ngặt đạo đức AI — không gửi mật khẩu hay khóa bí mật sang mô hình ngôn ngữ lớn."

### Slide 12 — Kết luận & Chuyển sang Demo trực tiếp (`06:40 – 07:00` | 20 giây)
> "Tóm lại, **MarketFlow AI** đã hoàn thành trọn vẹn mục tiêu kết hợp quản trị chiến dịch marketing đa kênh với Trợ lý AI có rào chắn an toàn cấp doanh nghiệp, hiện đang vận hành ổn định trên môi trường Production. Em xin cảm ơn Thầy/Cô đã lắng nghe và rất mong nhận được câu hỏi cũng như yêu cầu Demo trực tiếp từ Hội đồng ạ!"
