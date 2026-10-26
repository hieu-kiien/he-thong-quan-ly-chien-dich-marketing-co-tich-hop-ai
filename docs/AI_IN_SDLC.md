# Minh Chứng Ứng Dụng AI Trong Vòng Đời Phát Triển Phần Mềm (AI in SDLC)

> Học phần: Ứng dụng trí tuệ nhân tạo (AIA331)  
> Hệ thống: MarketFlow v2 (Clean Rebuild)  
> Mục tiêu: Ghi nhận minh chứng thực tế về việc ứng dụng AI xuyên suốt các giai đoạn KT1, KT2, KT3 và Đánh giá cuối kỳ  
> Căn cứ thực tế: `ke_hoach_xay_dung_lai.md`, `docs/rebuild/CONTRACT.md`, `docs/rebuild/P0_SPIKE_REPORT.md`  

---

## 1. Tổng quan Phương pháp Tiếp cận

Trong dự án MarketFlow v2, Trí tuệ Nhân tạo được sử dụng có hệ thống theo mô hình **AI-Assisted Pair Programming & Multi-Agent Orchestration**:
- AI không chỉ đóng vai trò là một tính năng nghiệp vụ của sản phẩm (Trợ lý Marketing AI), mà còn là một **công cụ kỹ thuật hỗ trợ toàn diện** trong suốt vòng đời phát triển phần mềm (Software Development Life Cycle - SDLC): từ phân tích hiện trạng, thiết kế kiến trúc, sinh mã nguồn, rà soát bảo mật, tối ưu prompt đến kiểm thử tự động.
- Mọi kết quả do AI đề xuất đều trải qua **Quy trình Kiểm chứng của Con người (Human Quality Gates)**: kiểm tra định dạng tĩnh, đo đạc tài nguyên thực nghiệm trên máy chủ VPS, kiểm thử đơn vị tự động và phân tích ảnh hưởng mã nguồn (GitNexus Impact Analysis) trước khi tích hợp vào nhánh chính.

---

## 2. Giai đoạn KT1: Phân tích Bài toán, Đánh giá Hiện trạng & Thiết kế Hệ thống

### 2.1. Đánh giá Khách quan Hiện trạng v1 bằng AI (Audit of Legacy v1)
Đầu giai đoạn tái cấu trúc, 3 tác nhân AI (AI Auditors) đã được huy động để phân tích toàn diện mã nguồn v1 (hơn 25.000 dòng mã) và cơ sở dữ liệu trên máy chủ. Kết quả phân tích được lưu trữ tại `ke_hoach_xay_dung_lai.md`:

1. **Phát hiện sự phình to của "Tính năng ảo" (Fake Features)**:
   - Hệ thống cũ có 26 bảng CSDL và 14 điểm vào AI phân mảnh.
   - Bằng chứng kiểm tra thực tế cho thấy 22 tính năng không hoạt động hoặc là giả lập:
     + *Đồng bộ tài khoản quảng cáo Meta/TikTok*: Token bị cắt ngắn dạng `abc123...xyz9` trước khi lưu vào CSDL, khiến code nhánh live không bao giờ chạy được nhưng vẫn tự ghi đè ngân sách chiến dịch (`metrics.py:1648, 2645`).
     + *Tính năng "Bác sĩ AI" (AI Doctor)*: Thực chất là các câu lệnh if/else cứng, nhưng ghi log giả mạo là gọi `provider="gemini"` và hứa hẹn tăng 30-45% CTR vô căn cứ (`ai_doctor.py:656`).
     + *Auto-publisher Fanpage*: Tự động đổi trạng thái thành `PUBLISHED` mà không hề kết nối API mạng xã hội (`contents.py:1145`).
     + *31/52 bản ghi trong `ai_logs` trên production* thực chất là mã if/else giả danh AI.
2. **Phát hiện các lỗ hổng bảo mật nghiêm trọng do AI sinh ra ở phiên bản cũ**:
   - `custom_base_url` trong tính năng chat cho phép người dùng đổi endpoint để gửi trộm API key hệ thống về máy chủ của kẻ tấn công (`schemas.py:1895`).
   - Cơ chế Staged Proposal cũ cho phép bỏ qua phân quyền, tự chuyển bài viết thành `APPROVED` và `PUBLISHED` mà không cần Quản lý duyệt (`ai.py:1389`).
   - Cầu nối OpenCode cũ cố tình mở lệnh `bash` trên máy chủ, dẫn đến nguy cơ Prompt Injection thực thi shell từ xa.

### 2.2. Thiết kế Tài liệu Hợp đồng Kiến trúc (`CONTRACT.md`)
Dựa trên kết quả phân tích của AI và yêu cầu môn học, kỹ sư con người đã chỉ đạo AI xây dựng bản **Design Contract** (`docs/rebuild/CONTRACT.md`) làm nguồn chân lý duy nhất cho toàn bộ quá trình tái cấu trúc:
- Ban hành **Rule 0 (Luật chống tính năng ảo)**: Nghiêm cấm hiển thị bất kỳ con số nào không đến từ dữ liệu người dùng nhập hoặc import thật; cấm giả lập kết nối mạng xã hội bên ngoài; AI chỉ được tạo đề xuất bản nháp (`ai_action = PROPOSED`).
- Thu gọn CSDL từ 26 bảng xuống đúng **14 bảng chuẩn** bám sát đề tài.
- Thu gọn phân quyền từ 5 vai trò phức tạp xuống đúng **2 vai trò thực tế**: `MANAGER` và `MARKETER`.

---

## 3. Giai đoạn KT2: Lập trình Đa Tác nhân & Xây dựng Lõi Nghiệp vụ

### 3.1. Phân chia Trách nhiệm Đa Tác nhân (Multi-Agent Architecture)
Quá trình lập trình lại toàn bộ hệ thống được điều phối bởi Orchestrator và phân chia cho các Subagent chuyên trách:
1. **Backend Agent**: Sinh mã nguồn FastAPI, mô hình dữ liệu SQLAlchemy 2.0, migrations Alembic, Service Layer phân quyền nghiêm ngặt, và bộ 54 ca kiểm thử Pytest.
2. **Frontend Agent**: Xây dựng lại toàn bộ giao diện React SPA bằng TypeScript Strict Mode, Tailwind CSS trung tính ấm, thư viện React Query và bố cục 3 cột cho khu vực Trợ lý AI.
3. **AI-Runner & DevOps Agent**: Đóng gói dịch vụ nội bộ `ai-runner` (FastAPI), viết kịch bản cài đặt tự động `install_runner.sh`, thiết lập cấu hình dịch vụ `systemd` trên máy chủ Ubuntu.
4. **Documentation & QA Agent**: Viết toàn bộ tài liệu kỹ thuật, xây dựng harness đánh giá prompt tự động (`evaluate_assistant.py`) và cấu hình GitHub Actions CI.

### 3.2. Những điểm Con người / Orchestrator đã Kiểm chứng & Hiệu chỉnh
Trong quá trình AI sinh mã nguồn, nhiều can thiệp kỹ thuật quan trọng của con người đã được thực hiện để đảm bảo chất lượng:
- **Phát hiện lỗi MCP SDK**: AI ban đầu định sử dụng phiên bản `mcp` mới nhất, nhưng con người đã phát hiện bản MCP 2.x đã bỏ module `fastmcp`, từ đó kịp thời pin phiên bản `mcp>=1.2.0,<2.0.0` với `FastMCP(..., stateless_http=True)`.
- **Hiệu chỉnh Phân quyền Duyệt bài**: Ban đầu AI thiết kế cho phép Quản lý duyệt mọi bài viết; Orchestrator đã bổ sung quy tắc an toàn bắt buộc: Quản lý **không được tự duyệt bài viết do chính mình tạo** (`CANNOT_REVIEW_OWN`).
- **Xử lý số liệu chia cho 0**: Khi tính các tỷ lệ CTR, CVR, CPA, Orchestrator yêu cầu chuẩn hoá toàn bộ kết quả mẫu số 0 thành `null` (hiển thị gạch ngang `"—”`) thay vì để chương trình phát sinh lỗi hoặc hiển thị `NaN%`.

---

## 4. Giai đoạn KT3: Nghiên cứu Thực nghiệm Prompt & Thử nghiệm trên VPS

### 4.1. Thử nghiệm Thực nghiệm P0 Spike trên Máy chủ Thực tế
Trước khi viết mã Trợ lý AI, kỹ sư đã tiến hành Spike thực nghiệm P0 trực tiếp trên máy chủ VPS (`2 vCPU, 2GB RAM, Ubuntu 24.04 LTS`):
- **Đo đạc bộ nhớ (Memory Profiling)**:
  + Dùng lệnh `/usr/bin/time -f "RSS_KB=%M"` và `ps -o rss` đo đạc thực tế: 1 tiến trình OpenCode tiêu thụ đỉnh **~490 MB RAM RSS**.
  + Nếu chạy 2 tiến trình đồng thời, mức tiêu thụ RAM vọt lên ~975 MB (chiếm 85% RAM toàn hệ thống), gây nguy cơ OOM máy chủ nghiêm trọng.
  + **Quyết định kỹ thuật**: Thiết lập cứng `RUNNER_CONCURRENCY=1`, quản lý hàng đợi tuần tự FIFO tối đa 8 vị trí, và đặt giới hạn bộ nhớ systemd `MemoryMax=896M`.
- **Khảo sát Mô hình Miễn phí (Free Models Benchmark)**:
  + Chạy thử nghiệm trên 8 mô hình miễn phí của OpenCode Zen.
  + Đánh giá khả năng gọi công cụ MCP, độ chính xác số liệu và chất lượng tiếng Việt.
  + Chọn `opencode/big-pickle` làm mô hình chính (phản ánh đúng 211 lượt chuyển đổi từ công cụ, không bịa số), và `opencode/glm-5.3-flash-free` làm mô hình dự phòng.

### 4.2. Quá trình Tối ưu Prompt qua 4 Vòng Thử nghiệm (Prompt Iterations)
AI và con người phối hợp phát triển System Prompt qua 4 thế hệ (lưu trữ tại `deploy/opencode/prompts/` và ghi nhận chi tiết tại `deploy/opencode/prompts/CHANGELOG.md`):
- **Vòng 1 (v1.md)**: Chỉ có mô tả vai trò cơ bản. Model gặp lỗi ảo giác số liệu giả định (CVR 4%, CPA 37.000 VND) và kịch bản TikTok quá dài (3650 ký tự). Đạt **6/8 ca (75.0%)**.
- **Vòng 2 (v2.md)**: Đưa vào rào chắn Grounding và Proposal-Only. Khắc phục được lỗi bịa số nhưng xuất hiện tác dụng phụ "Disclaimer Bloat" (lời cảnh báo dài dòng khiến Facebook caption vượt 2000 ký tự; TikTok 3306 ký tự). Đạt **5/8 ca (62.5%)**.
- **Vòng 3 (v3.md)**: Chuẩn hoá công thức tính chỉ số và định dạng kênh. Grounding đạt điểm tuyệt đối 1.0, nhưng model vẫn kèm cẩm nang sản xuất thừa làm vượt độ dài kênh (Facebook 2467 ký tự, TikTok 2789 ký tự). Đạt **6/8 ca (75.0%)**.
- **Vòng 4 (v4.md — Production)**: Siết chặt độ dài (Facebook < 1500 ký tự, TikTok < 1200 ký tự), cấm chèn disclaimer dông dài, cấm liệt kê lại từ cấm, loại bỏ cẩm nang thừa. Đạt **7/8 ca (87.5%)** trên mô hình thật `big-pickle`.

> [!NOTE]
> **Bài học kinh nghiệm về tính trung thực (CONTRACT §0):** Trong phiên làm việc trước, báo cáo từng nhầm lẫn kết quả tự kiểm tra bằng phản hồi mẫu (dry-run fixtures) làm bằng chứng thực nghiệm. Sai sót này đã được Orchestrator phát hiện và chấn chỉnh kịp thời: toàn bộ số liệu hiện tại đều xuất phát 100% từ đợt chạy thực nghiệm trực tiếp trên VPS ngày 26/10/2026 với OpenCode CLI, có lưu vết đối chứng tại `docs/eval/transcripts.json`.

### 4.3. Công Cụ Đánh Giá Tự Động Định Lượng (`evaluate_assistant.py`)
Nhóm xây dựng công cụ kiểm thử tự động với 8 ca kiểm thử xác định (`scripts/eval_cases.json`) nhằm đánh giá định lượng chất lượng câu trả lời theo các tiêu chuẩn kỹ thuật:
- **Chế độ Tự kiểm tra bộ chấm điểm (`--dry-run`)**: Sử dụng phản hồi mẫu viết tay (fixtures) để kiểm tra tính đúng đắn của harness (100% đạt ở fixture v4).
- **Kết quả Thực nghiệm Mô hình Thật trên VPS (26/10/2026)**: Đã thực thi trực tiếp trên VPS với `OPENCODE_MODEL=opencode/big-pickle` qua OpenCode CLI Zen Free Tier: **V1: 6/8 (75.0%) → V2: 5/8 (62.5%) → V3: 6/8 (75.0%) → V4: 7/8 (87.5%)**. Lượt live turn thực tế trên Campaign #1 đạt 100% khớp số liệu CSDL với độ trễ 109s qua 2 tool calls (`list_campaigns` + `propose_content_drafts`), đề xuất được xác nhận thành công. Báo cáo chi tiết tại `docs/eval/REAL_EVAL_REPORT.md` và `docs/eval/live_turn_20261026.md`.

---

## 5. Tổng kết Vai trò của AI trong Toàn bộ Dự án

| Hạng mục SDLC | Cách thức AI tham gia | Sự kiểm chứng & Can thiệp của Con người |
|---|---|---|
| **Phân tích yêu cầu (KT1)** | Rà soát mã nguồn cũ, hỗ trợ phát hiện các tính năng ảo (theo tài liệu khảo sát hiện trạng `ke_hoach_xay_dung_lai.md`), dự thảo ERD và bản đặc tả yêu cầu. | Loại bỏ các tính năng ảo, ban hành Rule 0, chốt danh sách 14 bảng và 2 vai trò cốt lõi. |
| **Thiết kế kiến trúc (KT1)** | Thiết kế luồng dữ liệu stream SSE, giao thức MCP Stateless-HTTP, cấu trúc Pydantic schemas. | Khảo sát thực tế VPS, yêu cầu phân tách độc lập giữa tầng REST Router và Service Layer. |
| **Lập trình chức năng (KT2)** | Sinh mã nguồn backend FastAPI, migrations Alembic, giao diện React SPA và test cases Pytest. | Chạy GitNexus impact analysis, kiểm tra an toàn kiểu dữ liệu TypeScript strict, sửa logic kiểm tra quyền duyệt chéo (`CANNOT_REVIEW_OWN`). |
| **Tối ưu Prompt & AI (KT3)** | Đề xuất cấu trúc prompt, kịch bản hội thoại đa kênh, kịch bản phòng thủ injection. | Đo đạc tài nguyên RAM trên VPS (P0 Spike), khảo sát mô hình miễn phí, xây dựng công cụ chấm điểm tự động. |
| **Kiểm thử & CI/CD (Cuối kỳ)** | Tạo file cấu hình GitHub Actions, Docker Compose, harness kiểm thử prompt. | Xác minh toàn bộ các lệnh kiểm thử tự động vượt qua (75 backend tests, 16 runner tests, frontend build sạch). |
