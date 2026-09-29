# Hướng Dẫn & Tài Liệu Căn Chỉnh Khung Đánh Giá Đồ Án Đại Học
## (University Defense & Rubric Alignment Guide)

**Tên đề tài**: Hệ thống quản lý chiến dịch marketing có tích hợp AI (MarketFlow AI)  
**Sản phẩm trực tiếp (Live)**: https://marketing.kienhieu.id.vn  
**Mã nguồn (Repository)**: https://github.com/hieu-kiien/he-thong-quan-ly-chien-dich-marketing-co-tich-hop-ai  
**Phiên bản cải tổ vận hành**: `refactor/marketflow-operations` (B2B SaaS Marketing Operations Platform)

---

## I. Tổng Quan Sự Chuyển Dịch Kiến Trúc & Giá Trị Đề Tài

### 1. Phá vỡ định kiến "AI Prompt Demo"
Hầu hết các đồ án tốt nghiệp tích hợp AI hiện nay thường dừng lại ở mức **"AI Wrapper"** (chỉ có vài ô input gửi prompt sang OpenAI/Gemini rồi in văn bản ra màn hình). Hệ thống đó thiếu giá trị nghiệp vụ thực tiễn, không thể triển khai cho doanh nghiệp và dễ bị hội đồng đánh giá thấp về hàm lượng công nghệ phần mềm.

**MarketFlow AI** được cải tổ toàn diện theo định vị **Nền tảng Vận hành Tiếp thị B2B SaaS (Marketing Operations Platform)**:
- **Trung tâm Điều hành (Command Center)**: Trả lời tức thì 4 câu hỏi sống còn mỗi ngày của đội ngũ tiếp thị:
  1. *Việc gì cần chú ý ngay? (What Needs Attention)* — Cảnh báo tự động về chiến dịch thâm hụt ngân sách, tỷ lệ hoàn vốn ROAS thấp, tác vụ quá hạn.
  2. *Hôm nay tôi phải làm gì? (My Work Today)* — Danh sách tác vụ ưu tiên cao trong ngày của cá nhân, tích hợp thao tác 1-click chuyển trạng thái.
  3. *Tác vụ nào bị trễ hạn? (Overdue Alert)* — Phân loại tác vụ theo mức độ khẩn cấp (URGENT, HIGH, MEDIUM, LOW).
  4. *Sức khỏe chiến dịch có đang gặp rủi ro? (Campaign Health)* — Tính điểm sức khỏe xác định 100% từ dữ liệu thực nghiệm.
- **Vận hành Toàn trình (End-to-End Workflow)**: Từ Brief chiến dịch định lượng $\rightarrow$ Phân bổ ngân sách kênh $\rightarrow$ Quản trị tác vụ Marketing đa năng $\rightarrow$ Duyệt nội dung đa cấp $\rightarrow$ Phân rã hiệu suất doanh thu $\rightarrow$ Bác sĩ AI chẩn đoán điểm nghẽn.

---

## II. Bảng Ánh Xạ Chi Tiết Với Khung Đánh Giá Điểm (Rubrics Mapping)

| Chuẩn Đầu Ra / Đợt Đánh Giá | Yêu Cầu Của Hội Đồng & Giảng Viên | Giải Pháp Hiện Thực Hóa Trong MarketFlow AI | Bằng Chứng / Vị Trí Trong Mã Nguồn |
| :--- | :--- | :--- | :--- |
| **BTTX1: Phân Tích & Thiết Kế Hệ Thống** | • Phân tích yêu cầu bài toán thực tế.<br>• Biểu đồ ca sử dụng (Use Case), luồng nghiệp vụ (BPMN).<br>• Phân tích kiến trúc phần mềm chuẩn mực. | • Kiến trúc Module hoá 3 tầng: React SPA $\leftrightarrow$ FastAPI Async RESTful $\leftrightarrow$ SQLAlchemy/SQLite Multi-Tenant DB.<br>• Quy trình phê duyệt nội dung Marketing 5 trạng thái (DRAFT $\rightarrow$ IN_REVIEW $\rightarrow$ APPROVED $\rightarrow$ PUBLISHED / REJECTED).<br>• Bảng điều phối Kanban & Lịch phát sóng đa kênh. | • `docs/ARCHITECTURE.md`<br>• `frontend/src/components/WorkflowCanvas.tsx`<br>• `backend/app/api/v1/contents.py` |
| **BTTX2: Cơ Sở Dữ Liệu & Backend API** | • Thiết kế lược đồ CSDL chuẩn hóa (3NF).<br>• Toàn vẹn dữ liệu, khoá ngoại, Check Constraints.<br>• Phân quyền người dùng (RBAC), Multi-tenancy.<br>• API RESTful chuẩn OpenAPI/Swagger. | • Bổ sung bảng thực thể vận hành: `campaign_tasks`, `campaign_budget_allocations`, `campaign_kpi_targets`.<br>• Ràng buộc `chk_task_type`, `chk_task_status`, `chk_task_priority`.<br>• Phân quyền 5 vai trò: ADMIN, MANAGER, AGENCY_MANAGER, MARKETER, CLIENT_APPROVER.<br>• Cơ chế Tenant Workspace Boundary cách ly dữ liệu nhiều doanh nghiệp. | • `backend/app/models/entities.py`<br>• `backend/app/core/database.py` (idempotent migration)<br>• `backend/app/api/v1/tasks.py`<br>• `backend/tests/test_tasks_and_operations.py` |
| **BTTX3: Tích Hợp AI & Xử Lý Nghiệp Vụ Chuyên Sâu** | • Sử dụng mô hình AI có kiểm soát.<br>• Prompt Engineering bài bản, có versioning.<br>• Chống ảo giác (Anti-hallucination).<br>• Cơ chế dự phòng khi API ngoại vi gián đoạn. | • Bộ sinh Prompt đa phiên bản `v1/v2/v3` (`prompts/prompts.json`).<br>• Ràng buộc Schema 100% qua Pydantic (`AIIdeaResponse`, `AIDraftResponse`, `AISummaryResponse`, `OmnichannelResponse`).<br>• **Zero Hallucination**: AI trích dẫn 100% số liệu thực nghiệm từ database, cảnh báo `is_sparse_data` khi dữ liệu bằng 0.<br>• **Smart Fallback Engine**: Tự động sinh dữ liệu mẫu hợp lệ khi mất mạng/hết quota. | • `backend/app/services/ai/prompt_engine.py`<br>• `backend/app/services/ai/ai_service.py`<br>• `backend/app/services/ai/ai_doctor.py`<br>• `scripts/evaluate_ai_grounding.py`<br>• `docs/AI_EVALUATION_REPORT.md` |
| **Đồ Án Tốt Nghiệp: Kiểm Thử, Bảo Mật & Triển Khai** | • Kiểm thử tự động (Unit, Integration, E2E).<br>• Đánh giá hiệu năng và độ trễ (Performance Latency).<br>• Tiêu chuẩn bảo mật (OWASP, BYOK Encryption, Sanitization).<br>• Khả năng tiếp cận người dùng (WCAG Accessibility). | • 1.263 automated backend tests (1.262 pass + 1 skip hợp lệ do runner CI không có live DB bị `.gitignore`), độ phủ câu lệnh 86% (ngưỡng CI 80%).<br>• Benchmark độ trễ non-AI p95 = 6.84 ms (vượt xa chuẩn 800ms SLA).<br>• Benchmark AI Grounding: 100% schema adherence, 0.00% hallucination rate, p95 = 3.36 ms.<br>• Playwright E2E: 38/38 mock + 7/7 live-backend; WCAG 2.2 AA: 25/25 với 0 lỗi Critical/Serious.<br>• Mã hóa khóa API người dùng chuẩn AES-256 (Fernet) BYOK.<br>• Lọc bỏ nhạy cảm API Key khỏi log hệ thống (`_sanitize_ai_error`).<br>• Tương phản màu sắc đạt chuẩn WCAG 2.1 AA (tỷ lệ 4.5:1). | • `.github/workflows/ci.yml`<br>• `scripts/measure_api_latency.py`<br>• `backend/tests/test_tasks_and_operations.py`<br>• `frontend/tests/a11y/wcag.spec.ts` |

---

## III. 5 Câu Hỏi "Hóc Búa" Của Hội Đồng & Cách Trả Lời Thuyết Phục

### Câu hỏi 1: *"Nếu nhà cung cấp AI (Google Gemini / OpenAI) bị sập mạng hoặc hết quota, toàn bộ hệ thống của bạn có bị tê liệt không?"*
**Trả lời:**
> "Thưa Thầy/Cô, hệ thống MarketFlow AI được thiết kế theo nguyên lý **Graceful Degradation** với kiến trúc **Smart Fallback Engine hai lớp**:
> 1. Toàn bộ các chức năng cốt lõi của hệ thống (Quản lý chiến dịch, Điều phối tác vụ Kanban, Tính toán phân bổ ngân sách, Lịch phát sóng đa kênh, Phân rã kinh tế ROI/ROAS) đều chạy hoàn toàn độc lập với LLM ngoại vi trên nền tảng FastAPI và SQLite/PostgreSQL.
> 2. Đối với các tác vụ AI (Sáng tạo nội dung, Chẩn đoán sức khỏe): Khi hệ thống phát hiện mất mạng ngoại vi, hết hạn quota (HTTP 429), lỗi dịch vụ (HTTP 500) hoặc timeout quá 15 giây, hệ thống tự động bẫy lỗi an toàn và kích hoạt **Động cơ Dự phòng Cục bộ (Local Fallback Engine)**. Động cơ này tự động sinh ra bản nháp nội dung hoặc bản chẩn đoán xác định chuẩn 100% cấu trúc schema Pydantic, đồng thời đánh dấu minh bạch `is_fallback: True` và ghi nhật ký vào bảng `ai_logs` để người dùng nhận biết."

### Câu hỏi 2: *"Mô hình AI của bạn có bị 'ảo giác' (hallucination), tự bịa ra số liệu chi phí, doanh thu hoặc đưa ra lời khuyên sai sự thật không?"*
**Trả lời:**
> "Thưa Thầy/Cô, đây chính là trọng tâm cải tổ của đề tài ở Sprint 4. Chúng em thiết lập **Rào chắn chống ảo giác 2 lớp**:
> 1. **Lớp Xác định (Deterministic Evidence Grounding)**: Động cơ Bác sĩ AI (`AIDoctorEngine`) tính toán các chỉ số kinh tế (ROAS, CTR, CVR, CPC, ROI) trực tiếp từ các bản ghi đo lường thực nghiệm trong bảng `campaign_metrics`. Mọi khuyến nghị (Tăng ngân sách, Cắt lỗ, Tối ưu hóa) bắt buộc phải trích dẫn chính xác con số từ cơ sở dữ liệu (ví dụ: 'Kênh Facebook đạt ROAS 3.50x, chi phí 10,000,000 VNĐ').
> 2. **Lớp Bảo vệ Dữ liệu Thưa Thớt (Sparse Data Guardrail)**: Đối với chiến dịch mới chưa có số liệu (0 views, 0 clicks), hệ thống tự động kích hoạt cờ `is_sparse_data: True` và phát cảnh báo rõ ràng rằng 'chưa đủ dữ liệu thực nghiệm để suy luận nhân quả', tuyệt đối cấm đưa ra kết luận vội vàng hay bịa đặt số liệu.
> Đề tài đã chạy thực nghiệm benchmark tự động (`scripts/evaluate_ai_grounding.py`) trên 40 kịch bản dữ liệu cực biên và đạt **Tỷ lệ ảo giác bằng 0.00%**."

### Câu hỏi 3: *"Cách phân quyền trong hệ thống được hiện thực như thế nào? Nhân viên (Marketer) có thể sửa hoặc xóa dữ liệu của Quản lý (Manager) không?"*
**Trả lời:**
> "Thưa Thầy/Cô, hệ thống áp dụng **Phân quyền dựa trên vai trò kết hợp kiểm soát cấp bản ghi (Record-Level RBAC)**:
> 1. **Phân cấp vai trò**: Gồm 5 vai trò hệ thống với ma trận quyền hạn rõ ràng: `ADMIN`, `MANAGER`, `AGENCY_MANAGER`, `MARKETER`, `CLIENT_APPROVER`.
> 2. **Quy tắc cấp bản ghi**: Tại API quản lý tác vụ (`/api/v1/tasks/{id}`), nhân viên được giao việc (Assignee) chỉ có quyền cập nhật trạng thái (`status`: TODO $\rightarrow$ IN_PROGRESS $\rightarrow$ DONE) và mức độ ưu tiên (`priority`). Quyền chỉnh sửa tiêu đề, phân công người khác, thay đổi hạn chót hoặc xóa tác vụ chỉ thuộc về Quản lý (Manager) hoặc người trực tiếp tạo ra tác vụ đó.
> 3. **Phân ranh giới Workspace (Tenant Boundary)**: Áp dụng cơ chế **Fail-closed**. Mọi truy vấn nếu không thuộc cùng workspace hợp lệ của người dùng đều bị từ chối truy cập bằng mã lỗi HTTP 403 Forbidden."

### Câu hỏi 4: *"Điểm sức khỏe chiến dịch (Health Score 0-100) trên Dashboard được tính như thế nào? Có phải do AI chấm điểm cảm tính không?"*
**Trả lời:**
> "Thưa Thầy/Cô, Điểm sức khỏe chiến dịch trên Dashboard được tính theo **Công thức toán học xác định 100% (Deterministic Health Scoring)**, hoàn toàn không phụ thuộc vào cảm tính của LLM:
> - Điểm cơ sở bắt đầu từ 100 điểm.
> - **Trừ điểm tác vụ trễ hạn**: Mỗi tác vụ quá hạn chưa hoàn thành bị trừ 10 điểm (tối đa trừ 40 điểm).
> - **Trừ điểm vượt ngân sách**: Nếu tổng ngân sách các kênh đã phân bổ vượt ngân sách cho phép, bị trừ 25 điểm.
> - **Cộng điểm tiến độ**: Tỷ lệ phần trăm tác vụ hoàn thành mang lại tối đa 20 điểm cộng.
> - Điểm số được giới hạn chuẩn trong khoảng $[0, 100]$ và phân loại thành 3 trạng thái trực quan: `HEALTHY` ($\ge 75$), `NEEDS_ATTENTION` ($50 - 74$), và `CRITICAL` ($< 50$). Nhờ đó, người quản lý có thể tin cậy 100% vào số liệu hiển thị mà không lo sợ AI đưa ra điểm số ngẫu nhiên."

### Câu hỏi 5: *"Đề tài đã kiểm thử những gì và đảm bảo chất lượng phần mềm ra sao?"*
**Trả lời:**
> "Thưa Thầy/Cô, đề tài xây dựng quy trình kiểm thử toàn diện tích hợp trong pipeline CI/CD GitHub Actions với 6 Cổng kiểm soát (Quality Gates):
> 1. **Unit & Integration Tests**: 1.263 test cases tự động bằng Pytest bao phủ toàn bộ luồng Auth, RBAC, Multi-tenancy, Task Operations, và Bác sĩ AI.
> 2. **Performance Benchmark**: Đo lường 50 lần liên tục mỗi endpoint, đạt độ trễ p95 = 6.84 ms (vượt chuẩn SLA 800ms của môn học).
> 3. **AI Grounding Benchmark**: 100% Schema Adherence trên 60 mẫu thử nghiệm; 0.00% Hallucination Rate; 3.36 ms độ trễ chẩn đoán Bác sĩ AI.
> 4. **Frontend Typecheck & Build**: TypeScript Strict Mode với Vite, 0 lỗi biên dịch, main chunk 108 kB (ngưỡng < 500 kB).
> 5. **Bảo mật & Chuẩn WCAG**: Quét rò rỉ mã bí mật bằng Gitleaks; kiểm tra độ tương phản màu sắc đạt chuẩn WCAG 2.1 AA."

---

## IV. Danh Sách Tài Liệu & Minh Chứng Đính Kèm Đồ Án
1. Báo cáo kiến trúc hệ thống: `docs/ARCHITECTURE.md`
2. Báo cáo thực nghiệm đo lường AI: `docs/AI_EVALUATION_REPORT.md`
3. Kịch bản benchmark độ trễ: `scripts/measure_api_latency.py`
4. Kịch bản benchmark kiểm định AI: `scripts/evaluate_ai_grounding.py`
5. Pipeline CI/CD tự động: `.github/workflows/ci.yml`
6. Bộ kiểm thử chức năng & adversarial: `backend/tests/test_tasks_and_operations.py`, `backend/tests/test_adversarial_v3.py`
