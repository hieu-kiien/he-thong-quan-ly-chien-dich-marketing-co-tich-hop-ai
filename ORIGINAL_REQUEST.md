# Original User Request

## 2026-09-22T15:46:06Z

Requested team: chia team ra test kĩ và 1 team giám sát và check lại test

Yêu cầu phân công nhóm làm việc theo cấu trúc: "chia team ra test kĩ và 1 team giám sát và check lại test".
- Nhóm Kiểm thử & Xử lý (Testing & Execution Team): Tiến hành nghiên cứu sâu mã nguồn MarketFlow AI (FastAPI + React 18 + SQLite + Docker), săn bug đa góc độ, sửa lỗi triệt để, tối ưu UI/UX và thiết lập pipeline CI/CD GitHub Actions.
- Nhóm Giám sát & Thẩm định Độc lập (Supervisory & QA Audit Team): Đóng vai trò Auditor độc lập, giám sát quá trình test, kiểm tra chéo (double-check) toàn bộ test suites và kết quả sửa lỗi, thực hiện adversarial testing (kiểm thử đối nghịch) để đảm bảo không có tình trạng tự chứng nhận kết quả (self-certification) lỏng lẻo.

Working directory: c:/Users/hieuk/Desktop/Ứng Dụng AI
Integrity mode: development

## Requirements

### R1. Rà soát Mã nguồn, Săn Bug & Sửa Lỗi Toàn Diện (Backend & AI Service)
Kiểm toán toàn bộ backend gồm API endpoints, mô hình dữ liệu SQLAlchemy, Pydantic schemas, cơ chế xác thực JWT, phân quyền, CORS, và các dịch vụ AI (Prompt Engine, AI service fallback). Phát hiện các lỗi logic, rò rỉ dữ liệu, lỗi ngoại lệ chưa bắt (unhandled exceptions), xung đột kiểu dữ liệu và thực hiện sửa lỗi trực tiếp trên mã nguồn.

### R2. Đánh giá & Tối ưu Trải nghiệm UI/UX (Frontend)
Rà soát giao diện web client (React 18 + Vite + Tailwind CSS), các trang chức năng (Dashboard Bento Grid, Review Queue, Campaign Management, Workflow Canvas, AI Drawer). Khắc phục toàn bộ các lỗi hiển thị, responsive layout trên các thiết bị, tối ưu trạng thái tải (loading skeletons, empty states, error boundaries), và đảm bảo thông báo phản hồi (feedback/toast) rõ ràng khi người dùng thao tác.

### R3. Thiết lập & Kiểm thử Quy trình CI/CD Hoàn chỉnh
Xây dựng pipeline tích hợp liên tục (CI) qua GitHub Actions (`.github/workflows/ci.yml`) để tự động hóa: kiểm tra định dạng và chất lượng code (linting/type-check), chạy bộ kiểm thử tự động backend với pytest, kiểm tra build frontend (`npm run build`), và kiểm tra tính hợp lệ của cấu hình container (`docker-compose.yml` / Dockerfiles).

### R4. Mở rộng Bộ Kiểm thử Tự động & Giám sát Thẩm định Độc lập (QA Audit)
- Nhóm Testing xây dựng bộ test tự động mở rộng bao phủ các bug được phát hiện và các edge cases.
- Nhóm Giám sát (Supervisory Team) trực tiếp thẩm định lại toàn bộ các test cases, chạy thử nghiệm độc lập, kiểm tra tính xác thực của các ca kiểm thử (kiểm tra xem test có thực sự fail khi có bug và pass khi đã sửa hay không), và lập biên bản đánh giá khách quan.

## Acceptance Criteria

### Bug Remediation & Backend Verification
- [ ] Tất cả endpoints trong `backend/app/api/v1/` xử lý dữ liệu đầu vào chặt chẽ, không sinh lỗi HTTP 500 khi gặp dữ liệu không hợp lệ hoặc thiếu dữ liệu.
- [ ] Các vấn đề bảo mật (quản lý session, JWT expiry, xử lý password hashing, CORS) được rà soát và khắc phục triệt để.
- [ ] Bộ kiểm thử backend hiện tại và các ca kiểm thử mới chạy thành công 100% thông qua lệnh `pytest backend/tests`.

### UI/UX Quality & Frontend Verification
- [ ] Lệnh `npm run build` trong thư mục `frontend` thực thi thành công, không có lỗi biên dịch TypeScript hay cảnh báo xung đột gói.
- [ ] Giao diện hiển thị đúng layout, thân thiện với người dùng, hỗ trợ đầy đủ các trạng thái: đang tải (loading), dữ liệu trống (empty), và thông báo lỗi rõ ràng khi mất kết nối backend.
- [ ] Luồng duyệt nội dung (Human-in-the-loop review queue) và gọi AI Drawer hoạt động mượt mà, phản hồi trực quan.

### CI/CD Pipeline Verification
- [ ] File cấu hình GitHub Actions workflow (`.github/workflows/ci.yml`) được tạo với cú pháp chuẩn, cấu hình đầy đủ các stage: Backend Test, Frontend Build & Typecheck, và Docker Compose Verification.
- [ ] File `docker-compose.yml` và các Dockerfile (`backend/Dockerfile`, `frontend/Dockerfile`) được kiểm tra cú pháp và build thử nghiệm thành công mà không phát sinh lỗi cấu hình.

### Supervisory & Independent Audit Verification
- [ ] Nhóm giám sát hoàn thành việc kiểm tra chéo (double-check), xác nhận 100% test cases là hợp lệ, có giá trị kiểm thử thực tế và không bị bypass.
- [ ] Có báo cáo nghiệm thu độc lập từ Nhóm giám sát tổng kết chi tiết: danh mục bug đã phát hiện, kết quả thẩm định sửa lỗi, đánh giá UI/UX và xác nhận pipeline CI/CD sẵn sàng hoạt động.

## 2026-09-23T07:13:39Z

Requested team: chia đội phối hợp xử lý từng vấn đề chuẩn team phát triển, tự lên kế hoạch, lựa chọn phương án xử lý xử lý toàn bộ đi, chia riêng ra 1 team giám sát các team còn lại, hãy làm việc theo loop và graph

Tổ chức các đội phát triển theo đúng yêu cầu: "chia đội phối hợp xử lý từng vấn đề chuẩn team phát triển, tự lên kế hoạch, lựa chọn phương án xử lý xử lý toàn bộ đi, chia riêng ra 1 team giám sát các team còn lại, hãy làm việc theo loop và graph".
- **Các đội Phát triển Tác nghiệp (Development Teams)**: Gồm các nhóm chuyên trách (Backend & AI Services, Frontend & UI/UX, DevOps & Automation), vận hành theo mô hình đồ thị phụ thuộc công việc (Task Dependency Graph / DAG) và vòng lặp phản hồi (Iterative Loop: Plan ➔ Execute ➔ Validate ➔ Refine) để tự động lên kế hoạch và xử lý triệt để toàn bộ các bài toán kỹ thuật của hệ thống MarketFlow AI.
- **Nhóm Giám sát Độc lập (Supervisory & QA Audit Team)**: Hoạt động song song và độc lập hoàn toàn với các đội phát triển, chịu trách nhiệm giám sát tiến độ trên từng node của đồ thị, thực hiện kiểm thử đối kháng (Adversarial Testing) sau mỗi vòng lặp, ngăn chặn việc tự xác nhận kết quả và phát hành chứng chỉ nghiệm thu độc lập.

Working directory: c:/Users/hieuk/Desktop/Ứng Dụng AI
Integrity mode: development

## Requirements

### R1. Điều phối Đồ thị Công việc (DAG) & Vòng lặp Phản hồi (Feedback Loop)
Xây dựng đồ thị phụ thuộc nhiệm vụ (Task Dependency Graph) phân rã toàn bộ hệ sinh thái MarketFlow AI. Các nhóm phối hợp triển khai theo chu trình lặp khép kín: Lập kế hoạch phân tích ➔ Lựa chọn giải pháp tối ưu ➔ Triển khai thực thi ➔ Kiểm định tại chỗ ➔ Chuyển giao node kế tiếp trên đồ thị.

### R2. Tự chủ Xử lý Toàn diện Mã nguồn, AI Service & UI/UX
- **Backend & AI Track**: Tối ưu hóa kiến trúc FastAPI, SQLAlchemy 2.0 ORM, chuẩn hóa mô hình dữ liệu Pydantic v2, tăng cường độ chịu lỗi tầng AI (Smart Fallback), siết chặt bảo mật JWT và phân quyền RBAC.
- **Frontend & UX Track**: Hoàn thiện toàn diện trải nghiệm web React 18 / Vite / Tailwind, tối ưu luồng Human-in-the-loop (từ AI Drawer sang Review Queue), loại bỏ các điểm nghẽn giao diện và đảm bảo 0 lỗi biên dịch TypeScript.
- **DevOps & CI/CD Track**: Tự động hóa kiểm thử liên tục qua GitHub Actions, tối ưu hóa container Dockerfile đa tầng và cấu hình Nginx SPA proxy.

### R3. Giám sát Đối kháng & Thẩm định Độc lập Đa tầng
Nhóm Giám sát độc lập thực hiện audit chéo trên từng node hoàn thành:
- Kiểm tra tính xác thực của mã nguồn (Anti-deception / Zero hardcoded mocks).
- Chạy kiểm thử đối kháng (Adversarial attack suites) thử thách độ bền hệ thống.
- Chạy kiểm thử đột biến (Mutation Testing) để xác thực độ tin cậy của các bộ test trước khi xác nhận nghiệm thu.

## Acceptance Criteria

### Task Graph & Execution Loop
- [ ] Đồ thị nhiệm vụ (DAG) được thiết lập rõ ràng và hoàn thành 100% các node công việc từ phân tích, triển khai đến nghiệm thu.
- [ ] Vòng lặp phản hồi (Loop) tự động ghi nhận và sửa chữa ngay bất kỳ sai lệch nào phát sinh trong quá trình chạy.

### Codebase & Quality Standards
- [ ] Backend: Toàn bộ các bộ test tự động (tối thiểu 149+ test cases) chạy vượt qua 100% không có lỗi (`0 errors, 0 failures, 0 warnings`).
- [ ] Frontend: Lệnh `npm run build` thực thi thành công sạch sẽ (Exit Code 0, 0 TypeScript errors).
- [ ] CI/CD: Pipeline GitHub Actions (`.github/workflows/ci.yml`) và cấu hình `docker-compose.yml` đạt chuẩn cú pháp và vận hành ổn định.

### Independent Supervisory Verification
- [ ] Nhóm Giám sát độc lập hoàn thành bộ kiểm thử đối kháng (Adversarial Tests) đạt tỷ lệ kháng cự 100%.
- [ ] Bộ kiểm thử đột biến (Mutation Testing) đạt tỷ lệ tiêu diệt 100% (100% Oracle Effectiveness).
- [ ] Có biên bản nghiệm thu độc lập từ Nhóm Giám sát xác nhận toàn bộ hệ thống sẵn sàng vận hành.

## 2026-09-23T14:19:00Z

Đồng bộ hóa toàn diện hệ thống quản lý chiến dịch marketing có tích hợp AI (MarketFlow AI): sửa lỗi bảo mật phân quyền record-level và lỗ hổng state machine trong backend, khắc phục ảo giác trong AI fallback, thực nghiệm đánh giá mô hình AI định lượng, cập nhật ma trận truy xuất nguồn gốc (Traceability Matrix) và nâng cấp toàn bộ tài liệu thành Báo cáo Hoàn thiện & Đánh giá V9 cùng Biên bản nghiệm thu trung thực chuẩn doanh nghiệp.

Working directory: c:\Users\hieuk\Desktop\Ứng Dụng AI
Integrity mode: development

## Architecture & Team Topology

- **Model Constraint Directive**: TUYỆT ĐỐI KHÔNG sử dụng các mô hình Claude 3.7, Claude 3.6, Sonnet, và các dòng GPT (OpenAI). Tối ưu hóa hiệu năng cao nhất bằng hệ sinh thái mô hình Gemini (Gemini 3.8 Pro/Flash, Gemini Flash-Lite).
- **Team Scrum 1 (Backend Core & Security Engineering)**:
  - Sử dụng GitNexus Graph Engineering (`impact`, `context`, `query`) để phân tích đồ thị luồng thực thi trước khi chỉnh sửa.
  - Sửa lỗi phân quyền mức bản ghi (Record-level authorization - NFR01) cho Campaign, Marketing Content, Metrics Dashboard và AI Context. Marketer chỉ được thao tác trên tài nguyên được phân công (`owner_id` hoặc `CampaignMember`).
  - Sửa triệt để lỗ hổng State Machine (Human-in-the-loop): Không cho phép tạo bài viết trực tiếp ở trạng thái `APPROVED` hoặc `PUBLISHED` qua `POST /contents` hay `PUT /contents/{id}`. Mọi phê duyệt/xuất bản bắt buộc qua endpoint nghiệp vụ chuyên biệt (`/submit`, `/approve`, `/publish`).
  - Đồng bộ `RoleChecker` với trạng thái người dùng trong CSDL (`user.status == 'ACTIVE'`).
  - Khắc phục AI Fallback trong `ai_service.py`: Loại bỏ các nhận định ảo giác (hallucination về khung giờ, cuối tuần khi dữ liệu đầu vào chỉ có metric tổng). Tách biệt rõ ràng log/flag giữa AI LLM thật và Fallback Mock.
- **Team Scrum 2 (AI Evaluation & Verification Engineering)**:
  - Thiết lập kịch bản thực nghiệm định lượng cho 3 tác vụ AI (Ý tưởng, Bản nháp, Tóm tắt).
  - Thu thập số liệu thực nghiệm: Schema validation rate, Grounding score, P50/P95 Latency, Cost estimation.
  - Xây dựng bộ test đối kháng (adversarial tests) kiểm tra chặn vượt quyền record-level và chặn bypass state machine.
- **Team Scrum 3 (Documentation & Academic Traceability)**:
  - Cập nhật toàn diện `requirements-traceability.csv`: Chuyển trạng thái từ `DESIGNED` sang `IMPLEMENTED`, `TESTED`, `MEASURED`, liên kết trực tiếp mã nguồn và test case ID.
  - Tái cấu trúc và soạn thảo Báo cáo V9 (8 chương chuẩn mực: Giới thiệu, Cơ sở kỹ thuật, Phân tích yêu cầu, Thiết kế hệ thống, Hiện thực hóa, Kiểm thử thực nghiệm, Đánh giá AI định lượng, Kết luận & Giới hạn).
  - Cập nhật `README.md` phản ánh đúng số liệu test suite hiện tại.
- **Team 4: Giám sát Độc lập (Supervisory Oversight Team)**:
  - Giám sát chéo quá trình thực hiện của các Scrum team.
  - Kiểm tra tính tuân thủ quy tắc Graph Engineering (kiểm tra impact trước khi sửa, phân tích thay đổi đồ thị trước khi commit).
  - Ngăn chặn tự chứng nhận (anti-self-certification), phát hiện mã giả (facade mock/dummy), kiểm toán tính toàn vẹn của dữ liệu thực nghiệm.
- **Team 5: Duyệt Cuối Chuẩn Doanh Nghiệp (Enterprise Final Acceptance Team)**:
  - Đóng vai trò Hội đồng nghiệm thu kỹ thuật (Quality Gatekeeper).
  - Biên soạn lại `BIEN_BAN_NGHIEM_THU.md`: Thay thế các tuyên bố thổi phồng ("100% production ready", "audit độc lập giả định") bằng báo cáo nghiệm thu kỹ thuật nội bộ có đối chứng định lượng, ghi nhận đầy đủ giới hạn đã biết và bằng chứng thực tế.
  - Ra quyết định ký duyệt phát hành chính thức (Release Gate).

## Requirements

### R1. Backend Core & State Machine Hardening
Thực hiện sửa đổi an toàn mã nguồn backend sử dụng GitNexus impact analysis: khóa chặt phân quyền phạm vi bản ghi (record scope), đóng kín các điểm bypass của state machine duyệt nội dung, đồng bộ kiểm tra trạng thái tài khoản đang hoạt động, và loại bỏ ảo giác trong AI fallback logic.

### R2. Empirical AI Quality & Robustness Verification
Xây dựng và chạy bộ thực nghiệm đánh giá năng lực AI định lượng (độ trễ, tính đúng đắn cấu trúc schema, độ liên quan dữ liệu) và bộ kiểm thử bảo mật đối kháng (ngăn chặn leo quyền, dữ liệu ngoại lai).

### R3. Traceability Ledger & Report V9 Synthesis
Đồng bộ hóa 100% ma trận RTM (Requirements Traceability Matrix) với mã nguồn và kiểm thử thực tế. Nâng cấp bộ tài liệu LaTeX thành Báo cáo V9 phản ánh chính xác trạng thái cài đặt và kết quả kiểm thử thực nghiệm của hệ thống.

### R4. Independent Oversight & Enterprise Release Gate
Duy trì giám sát độc lập liên tục giữa các nhóm công tác và thực hiện quy trình nghiệm thu chuẩn doanh nghiệp với các chỉ số đo lường thực chứng không thổi phồng.

## Acceptance Criteria

### Technical & Security Gate
- [ ] Mọi endpoint `/campaigns`, `/contents`, `/metrics`, `/schedules` đều xác minh phạm vi sở hữu của người dùng (Record-level access control).
- [ ] Không có cách nào tạo hoặc sửa đổi trực tiếp Marketing Content sang trạng thái `APPROVED` hoặc `PUBLISHED` ngoài quy trình duyệt hợp lệ.
- [ ] `RoleChecker` từ chối các token của tài khoản có trạng thái khác `ACTIVE`.
- [ ] AI Fallback Summary chỉ nhận xét dựa trên các trường số liệu thực sự có trong context.

### Verification & Empirical Data Gate
- [ ] Toàn bộ test suite backend (unit tests, integration tests, adversarial tests) chạy thành công (Exit Code 0).
- [ ] Có bảng số liệu thực nghiệm đo lường AI định lượng (Latency, Schema Valid Rate, Grounding) có thể tái lập.
- [ ] Không sử dụng các mô hình bị cấm (Claude 3.7, Claude 3.6, Sonnet, GPT).

### Documentation & Compliance Gate
- [ ] File `requirements-traceability.csv` không còn mục nào ở trạng thái "CHƯA CÓ - trước code" / `DESIGNED` đối với các tính năng đã cài đặt; chuyển sang `IMPLEMENTED` / `TESTED` kèm artifact path cụ thể.
- [ ] Báo cáo V9 phản ánh hệ thống ở thì hiện tại (đã lập trình, có mã nguồn, có kết quả đo lường), xóa bỏ hoàn toàn các câu văn "chưa lập trình" từ V8.
- [ ] `BIEN_BAN_NGHIEM_THU.md` được viết lại theo chuẩn doanh nghiệp thực chứng, loại bỏ các xưng danh giả định hoặc tuyên bố 100% không có bằng chứng.
- [ ] Báo cáo Giám sát Độc lập và Biên bản Ký duyệt Cuối xác nhận toàn bộ quy trình đạt chuẩn.

## 2026-09-24T16:50:34Z

# Teamwork Project Prompt — Official Release

> Status: Launched
> Goal: Execute multi-agent development loop → deliver enterprise-grade omnichannel martech SaaS
> Requested team: Full Teamwork Multi-Agent System (Backend Core, Frontend UI/UX, AI Prompt Engineering, DevOps, Independent QA & Adversarial Auditor)

Tái cấu trúc và phát triển toàn diện hệ thống MarketFlow AI thành Nền tảng Điều phối Tiếp thị Tinh gọn chuẩn Doanh nghiệp & Agency (Enterprise Agency Omnichannel MarTech SaaS), ưu tiên trải nghiệm người dùng trơn tru vượt trội, tối ưu chuyên sâu 3 kênh chủ lực (Facebook, TikTok, Email), hỗ trợ quản lý đa khách hàng/workspace độc lập kèm Brand Kit, mô phỏng Social Preview chân thực, trung tâm Cài đặt tùy biến cao cấp tích hợp tính năng tự cấu hình Custom AI API Key (BYOK), và quy trình kiểm thử đối kháng vòng lặp đạt chuẩn chất lượng thực chứng.

Working directory: c:\Users\hieuk\Desktop\Ứng Dụng AI
Integrity mode: development

## Requirements

### R1. Kiến trúc Đa không gian làm việc & Quản trị Khách hàng Agency (Multi-Workspace & Brand Kit)
- Cho phép Agency/Doanh nghiệp tạo và quản lý nhiều Workspace/Khách hàng độc lập, cách ly hoàn toàn dữ liệu giữa các thương hiệu.
- Mỗi Workspace tích hợp một Brand Kit chuyên biệt: Tên thương hiệu, Định vị sản phẩm/USP, Giọng văn chuẩn (Tone of Voice), Bộ quy tắc cấm kỵ (Banned Keywords / Blacklist từ ngữ vi phạm).
- Loại bỏ hoàn toàn cơ chế tự động đăng nhập demo; cung cấp luồng Đăng ký / Đăng nhập (Auth) và phân quyền chuẩn vai trò: Agency Manager, Marketer/Creator, Client Approver.

### R2. Động cơ Sáng tạo AI Đa kênh Chuyên sâu (Deep 3-Channel AI Orchestrator)
Từ 1 bản Brief chiến dịch duy nhất, AI tự động kế thừa Brand Kit và sinh ra trọn bộ tài sản tiếp thị chuẩn form cho 3 kênh cốt lõi:
1. **Facebook Feed & Ads**: Tiêu đề giật tít, thân bài ngắt nhịp kích thích tương tác, CTA hành động, danh sách hashtag tối ưu.
2. **TikTok / Reels Script**: Kịch bản video ngắn phân cảnh chi tiết (Hook 3 giây đầu giữ chân, Visual action mô tả hành động, Voiceover lời thoại nhân vật, Âm thanh gợi ý).
3. **Email Marketing Sequence**: Đề xuất tiêu đề A/B Testing, lời chào cá nhân hóa, nội dung nuôi dưỡng/bán hàng có cấu trúc, nút kêu gọi hành động chuyển đổi cao.

### R3. Hệ thống Thẩm định & An toàn Thương hiệu Đa tầng (Enterprise Brand Safety & Compliance)
- Cơ chế kiểm tra tuân thủ tự động (Compliance & Policy Guardrail): Quét phát hiện trước các từ khóa bị cấm trong Brand Kit và chính sách quảng cáo (cam kết sai sự thật, từ ngữ nhạy cảm y tế/tài chính, từ ngữ giật gân thái quá) và hiển thị cảnh báo trực quan trước khi gửi duyệt.
- Quy trình duyệt bài phân cấp bắt buộc (Strict Human-in-the-loop Gate): Khóa cứng không cho phép bài viết tự động chuyển sang `APPROVED` hay `PUBLISHED` nếu chưa được tài khoản có quyền Quản lý/Client phê duyệt trên Hàng đợi duyệt (Review Queue).

### R4. Bộ Mô phỏng Giao diện Xuất bản Thực tế (High-Fidelity Social Preview Engine)
- Tích hợp bộ Social Preview trực quan cho 3 kênh (Facebook Post Card đầy đủ avatar, tên fanpage, thẻ sponsored, tương tác Like/Comment/Share; TikTok Phone Mockup hiển thị video layout; Email Inbox Preview).
- Cho phép người dùng gắn ảnh sản phẩm/banner thực tế hoặc link ảnh minh họa vào bài viết trước khi gửi duyệt.
- Bổ sung công cụ thao tác nhanh: Nút "1-Click Copy chuẩn format (giữ trọn icon và ngắt dòng)" và nút "Xuất kế hoạch chiến dịch ra Excel/PDF".

### R5. Trung tâm Đo lường & AI Cố vấn Chiến lược (Attribution Analytics & Actionable AI Doctor)
- Ghi nhận và trực quan hóa các chỉ số hiệu suất: Views, Clicks, Conversions, Cost, Revenue.
- Tự động tính toán các chỉ số kinh tế tiếp thị: CTR (%), CPC (VNĐ), CVR (%), ROAS và ROI (%).
- Tích hợp "Bác sĩ Chiến dịch AI" (AI Doctor) phân tích dữ liệu thực tế, chỉ ra điểm nghẽn, cảnh báo kênh kém hiệu quả và đưa ra khuyến nghị hành động chiến lược cụ thể.

### R6. Trung tâm Cài đặt & Tùy biến Doanh nghiệp (Settings & Custom AI API Key - BYOK)
- Trang Cài đặt (Settings) trực quan: Quản lý thông tin tài khoản, cài đặt tùy biến giao diện, cấu hình thông số mặc định của chiến dịch.
- Tính năng **Bring Your Own Key (BYOK)**: Cho phép người dùng tự điền API Key riêng của họ (Google Gemini, OpenRouter, OpenAI, v.v.), lựa chọn model AI mong muốn, kiểm tra tính hợp lệ của key ngay lập tức (Test API Connection) và mã hóa lưu trữ an toàn.

## Acceptance Criteria

### Kiến trúc & Trải nghiệm Người dùng Chuẩn Doanh nghiệp
- [ ] Không còn bất kỳ mã lệnh đăng nhập tự động ngầm nào (`manager@ictu.edu.vn`); hỗ trợ màn hình Login/Register thực tế và lưu session an toàn.
- [ ] Hỗ trợ tạo và chuyển đổi giữa các Workspace/Client riêng biệt; dữ liệu chiến dịch và nội dung được cô lập chính xác theo từng Workspace.
- [ ] Giao diện Brand Kit cho phép cấu hình USP, Tone of Voice và danh sách từ khóa cấm; dữ liệu này được inject thành công vào context gọi AI.
- [ ] Trải nghiệm người dùng trơn tru, có phản hồi trực quan (loading skeletons, empty states, error boundaries, toast notifications chuẩn xác).

### Năng lực Sáng tạo Đa kênh & Hiển thị Trực quan
- [ ] Tính năng "1-Click Sáng tạo Đa kênh" sinh thành công trọn bộ nội dung cho Facebook, TikTok (kịch bản phân cảnh) và Email từ 1 đề bài duy nhất.
- [ ] Component Social Preview hiển thị trung thực bài viết dưới dạng Facebook Mockup Card và Email Preview với đầy đủ các thành phần giao diện mạng xã hội.
- [ ] Hỗ trợ đính kèm hình ảnh sản phẩm/banner vào bài viết và hiển thị trực tiếp trên Social Preview.
- [ ] Nút sao chép 1 chạm (Copy to Clipboard) hoạt động chính xác, giữ nguyên cấu trúc dòng và biểu tượng cảm xúc.

### Cài đặt Tùy biến & Custom API Key
- [ ] Trang Cài đặt (Settings) hoạt động đầy đủ, cho phép người dùng tùy biến và kiểm tra kết nối API Key AI riêng (Custom API Key) thành công trước khi lưu.
- [ ] Khi người dùng thiết lập Custom API Key, hệ thống ưu tiên sử dụng Key này cho các tác vụ AI tương ứng.

### An toàn & Luồng Duyệt Bài
- [ ] Hệ thống tự động cảnh báo khi bài viết chứa từ khóa nằm trong danh sách đen của Brand Kit.
- [ ] Bài viết tạo mới bắt buộc ở trạng thái `DRAFT` hoặc `AI_DRAFT`; chỉ tài khoản Quản lý mới có quyền bấm `Approve` để chuyển sang `APPROVED`.
- [ ] Lịch đăng (Marketing Calendar) chỉ cho phép lên lịch đối với các nội dung đã được phê duyệt.

### Đo lường & Độ tin cậy Kỹ thuật (Quy trình Vòng lặp Thực chứng)
- [ ] AI Doctor đưa ra nhận định dựa trên số liệu thực tế của chiến dịch (Views, Clicks, Conversions, Cost, Revenue), không ảo giác bịa đặt số liệu.
- [ ] Lệnh `npm run build` trong thư mục frontend thực thi thành công (Exit Code 0, không có lỗi TypeScript).
- [ ] Toàn bộ bộ test tự động backend chạy thành công (Exit Code 0, 100% pass, không bypass, không hardcode mock).
- [ ] Đội ngũ Giám sát Độc lập (QA Auditor) hoàn thành kiểm thử đối kháng (Adversarial Testing) và cấp chứng chỉ nghiệm thu xác nhận hệ thống hoàn chỉnh.

