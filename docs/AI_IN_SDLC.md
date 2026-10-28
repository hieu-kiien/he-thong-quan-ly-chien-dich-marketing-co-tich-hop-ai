# Minh Chứng Ứng Dụng AI Trong Vòng Đời Phát Triển Phần Mềm (AI in SDLC)

> Học phần: Ứng dụng trí tuệ nhân tạo (AIA331)  
> Hệ thống: MarketFlow  
> Mục tiêu: Ghi nhận minh chứng thực tế về việc ứng dụng AI xuyên suốt các giai đoạn KT1, KT2, KT3 và Đánh giá cuối kỳ  

---

## 1. Tổng quan Phương pháp Tiếp cận

Trong dự án MarketFlow, Trí tuệ Nhân tạo được sử dụng có hệ thống theo mô hình **AI-Assisted Pair Programming & Multi-Agent Orchestration**:
- AI không chỉ đóng vai trò là một tính năng nghiệp vụ của sản phẩm (Trợ lý Marketing AI), mà còn là một **công cụ kỹ thuật hỗ trợ toàn diện** trong suốt vòng đời phát triển phần mềm (Software Development Life Cycle - SDLC): từ phân tích yêu cầu, thiết kế kiến trúc, sinh mã nguồn, rà soát bảo mật, tối ưu prompt đến kiểm thử tự động.
- Mọi kết quả do AI đề xuất đều trải qua **Quy trình Kiểm chứng của Con người (Human Quality Gates)**: kiểm tra định dạng tĩnh, đo đạc tài nguyên thực nghiệm trên máy chủ VPS, kiểm thử đơn vị tự động và phân tích ảnh hưởng mã nguồn (GitNexus Impact Analysis) trước khi tích hợp vào nhánh chính.

---

## 2. Giai đoạn KT1: Phân tích Bài toán, Đánh giá Rủi ro & Thiết kế Hệ thống

### 2.1. Phân tích Rủi ro Kiến trúc & Phản biện Thiết kế bằng AI (Architecture & Security Review)
Ở giai đoạn khởi tạo thiết kế, 3 tác nhân AI chuyên trách (Architecture & Security Reviewers) đã được huy động để phân tích các rủi ro tiềm ẩn khi tích hợp LLM vào hệ thống quản trị chiến dịch marketing:

1. **Ngăn chặn rủi ro "Tính năng ảo" và Ảo giác Số liệu (Hallucination & Fake Metrics)**:
   - Nếu cho phép AI tự sinh số liệu dự báo mà không gắn với dữ liệu thực trong CSDL, hoặc giả lập việc đẩy bài tự động lên mạng xã hội khi chưa có tài khoản đối tác xác minh, hệ thống sẽ làm sai lệch báo cáo kinh doanh.
   - Giải pháp thiết kế: Mọi số liệu KPI (`views`, `clicks`, `conversions`, `cost`, CTR, CVR, CPC, CPA, CPM) chỉ được tính toán từ dữ liệu thực do người dùng nhập hoặc import CSV 2 bước; bước xuất bản cuối cùng sử dụng xác nhận liên kết thực tế (`/mark-published` kèm `published_url`).
2. **Phát hiện và loại bỏ sớm các lỗ hổng bảo mật trong thiết kế tích hợp AI**:
   - *Rủi ro lộ khóa API qua tùy chỉnh URL (`custom_base_url`)*: Nếu cho phép người dùng đổi endpoint từ giao diện trình duyệt, kẻ tấn công có thể đổi URL để thu thập API key hệ thống $\rightarrow$ Cố định cấu hình 13 mô hình ở phía máy chủ `ai-runner`.
   - *Rủi ro AI tự ý ghi đè dữ liệu nghiệp vụ*: Nếu công cụ MCP thực hiện `INSERT/UPDATE` trực tiếp vào bảng `campaigns`/`contents`, một lần ảo giác của LLM sẽ làm mất bước phê duyệt của Quản lý $\rightarrow$ Thiết kế bảng trung gian `ai_actions` (`status = PROPOSED`) chờ con người bấm Xác nhận (`/confirm`).
   - *Rủi ro thực thi lệnh hệ thống (Shell Injection)*: Khóa chặt toàn bộ quyền `bash`, `edit`, `write`, `webfetch` của tiến trình `opencode run`, chỉ cho phép gọi 14 công cụ MCP nội bộ.

### 2.2. Thiết kế Tài liệu Hợp đồng Kiến trúc (Design Contract)
Dựa trên kết quả phân tích của AI và yêu cầu môn học, kỹ sư con người đã chỉ đạo AI xây dựng bản **Design Contract** làm nguồn chân lý duy nhất cho toàn bộ quá trình phát triển:
- Ban hành **Rule 0 (Luật chống tính năng ảo)**: Nghiêm cấm hiển thị bất kỳ con số nào không đến từ dữ liệu người dùng nhập hoặc import thật; cấm giả lập kết nối mạng xã hội bên ngoài; AI chỉ được tạo đề xuất bản nháp (`ai_action = PROPOSED`).
- Thiết kế CSDL gồm đúng **14 bảng chuẩn 3NF** bám sát đề tài 80300.
- Thiết kế phân quyền gồm đúng **2 vai trò thực tế**: `MANAGER` và `MARKETER`.

---

## 3. Giai đoạn KT2: Lập trình Đa Tác nhân & Xây dựng Lõi Nghiệp vụ

### 3.1. Phân chia Trách nhiệm Đa Tác nhân (Multi-Agent Architecture)
Quá trình phát triển toàn bộ hệ thống được điều phối bởi Orchestrator và phân chia cho các Subagent chuyên trách:
1. **Backend Agent**: Sinh mã nguồn FastAPI, mô hình dữ liệu SQLAlchemy 2.0, migrations Alembic, Service Layer phân quyền nghiêm ngặt, và bộ kiểm thử Pytest.
2. **Frontend Agent**: Xây dựng toàn bộ giao diện React SPA bằng TypeScript Strict Mode, Tailwind CSS trung tính ấm, thư viện React Query và bố cục ngăn kéo Trợ lý AI.
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
Trước khi viết mã Trợ lý AI, kỹ sư đã tiến hành Spike thực nghiệm P0 trực tiếp trên máy chủ VPS (`2 vCPU, 2.5GB RAM, Ubuntu 24.04 LTS`):
- **Đo đạc bộ nhớ (Memory Profiling)**:
  + Dùng lệnh `/usr/bin/time -f "RSS_KB=%M"` và `ps -o rss` đo đạc thực tế: 1 tiến trình OpenCode tiêu thụ đỉnh **~490 MB RAM RSS**.
  + Nếu chạy 2 tiến trình đồng thời, mức tiêu thụ RAM vọt lên ~975 MB, gây nguy cơ OOM máy chủ nghiêm trọng.
  + **Quyết định kỹ thuật**: Thiết lập cứng `RUNNER_CONCURRENCY=1`, quản lý hàng đợi tuần tự FIFO tối đa 8 vị trí, và đặt giới hạn bộ nhớ systemd `MemoryMax=896M`.
- **Khảo sát Mô hình Miễn phí (Free Models Benchmark)**:
  + Chạy thử nghiệm trên các mô hình miễn phí thuộc 5 nền tảng (OpenCode Zen, Groq LPU, OpenRouter, Google AI Studio).
  + Đánh giá khả năng gọi công cụ MCP, độ chính xác số liệu và chất lượng tiếng Việt để cấu hình chuỗi 13 mô hình tự động chuyển đổi dự phòng.

### 4.2. Quá trình Tối ưu Prompt qua 4 Giai đoạn Thử nghiệm (Prompt Iterations)
AI và con người phối hợp phát triển System Prompt qua 4 giai đoạn cải tiến (lưu trữ tại `deploy/opencode/prompts/`):
- **Giai đoạn 1 — Bản Cơ sở (Baseline)**: Chỉ có mô tả vai trò cơ bản. Model gặp lỗi ảo giác số liệu giả định (CVR 4%, CPA 37.000 VND) và kịch bản TikTok quá dài (3650 ký tự). Đạt **6/8 ca (75.0%)**.
- **Giai đoạn 2 — Bản Rào chắn (Guardrails & Grounding)**: Đưa vào rào chắn Grounding và Proposal-Only. Khắc phục được lỗi bịa số nhưng xuất hiện tác dụng phụ "Disclaimer Bloat" (lời cảnh báo dài dòng khiến Facebook caption vượt 2000 ký tự; TikTok 3306 ký tự). Đạt **5/8 ca (62.5%)**.
- **Giai đoạn 3 — Bản Chuẩn hóa KPI & Kênh**: Chuẩn hoá công thức tính chỉ số và định dạng kênh. Grounding đạt điểm tuyệt đối 1.0, nhưng model vẫn kèm cẩm nang sản xuất thừa làm vượt độ dài kênh (Facebook 2467 ký tự, TikTok 2789 ký tự). Đạt **6/8 ca (75.0%)**.
- **Giai đoạn 4 — Bản Production**: Siết chặt độ dài (Facebook < 1500 ký tự, TikTok < 1200 ký tự), cấm chèn disclaimer dông dài, cấm liệt kê lại từ cấm, loại bỏ cẩm nang thừa. Đạt **7/8 ca (87.5%)**.

### 4.3. Công Cụ Đánh Giá Tự Động Định Lượng (`evaluate_assistant.py`)
Nhóm xây dựng công cụ kiểm thử tự động với 8 ca kiểm thử xác định (`scripts/eval_cases.json`) nhằm đánh giá định lượng chất lượng câu trả lời theo các tiêu chuẩn kỹ thuật:
- **Kết quả Thực nghiệm Mô hình Thật trên VPS**: Đã thực thi trực tiếp trên VPS qua OpenCode CLI: **Bản 1: 6/8 (75.0%) → Bản 2: 5/8 (62.5%) → Bản 3: 6/8 (75.0%) → Bản 4 (Production): 7/8 (87.5%)**. Lượt live turn thực tế trên Campaign #1 đạt 100% khớp số liệu CSDL với độ trễ 109s qua 2 tool calls (`list_campaigns` + `propose_content_drafts`), đề xuất được xác nhận thành công. Báo cáo chi tiết tại `docs/eval/REAL_EVAL_REPORT.md` và `docs/eval/live_turn_20261026.md`.

---

## 5. Tổng kết Vai trò của AI trong Toàn bộ Dự án

| Hạng mục SDLC | Cách thức AI tham gia | Sự kiểm chứng & Can thiệp của Con người |
|---|---|---|
| **Phân tích yêu cầu (KT1)** | Phân tích yêu cầu nghiệp vụ, phản biện rủi ro ảo giác số liệu và an ninh, dự thảo ERD và bản đặc tả yêu cầu. | Ban hành Rule 0 chống số liệu giả, chốt danh sách 14 bảng và 2 vai trò cốt lõi (`MANAGER`, `MARKETER`). |
| **Thiết kế kiến trúc (KT1)** | Thiết kế luồng dữ liệu stream SSE, giao thức MCP Stateless-HTTP, cấu trúc Pydantic schemas. | Khảo sát thực tế VPS, yêu cầu phân tách độc lập giữa tầng REST Router và Service Layer. |
| **Lập trình chức năng (KT2)** | Sinh mã nguồn backend FastAPI, migrations Alembic, giao diện React SPA và test cases Pytest. | Chạy GitNexus impact analysis, kiểm tra an toàn kiểu dữ liệu TypeScript strict, sửa logic kiểm tra quyền duyệt chéo (`CANNOT_REVIEW_OWN`). |
| **Tối ưu Prompt & AI (KT3)** | Đề xuất cấu trúc prompt, kịch bản hội thoại đa kênh, kịch bản phòng thủ injection. | Đo đạc tài nguyên RAM trên VPS (P0 Spike), khảo sát mô hình miễn phí, xây dựng công cụ chấm điểm tự động. |
| **Kiểm thử & CI/CD (Cuối kỳ)** | Tạo file cấu hình GitHub Actions, Docker Compose, harness kiểm thử prompt. | Xác minh toàn bộ các lệnh kiểm thử tự động vượt qua (104 backend tests, 18 runner tests, 29 E2E tests, frontend build sạch). |
