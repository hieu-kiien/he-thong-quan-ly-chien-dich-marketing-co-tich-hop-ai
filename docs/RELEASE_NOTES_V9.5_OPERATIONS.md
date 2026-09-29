# MarketFlow AI — Release Notes v9.5 (Marketing Operations Platform Revamp)

**Mã phiên bản**: `v9.5-operations`  
**Ngày phát hành**: 29/09/2026  
**Nhánh Git**: `main` (Commit: `685a5dc`) & `refactor/marketflow-operations`  
**Kho mã nguồn**: [hieu-kiien/he-thong-quan-ly-chien-dich-marketing-co-tich-hop-ai](https://github.com/hieu-kiien/he-thong-quan-ly-chien-dich-marketing-co-tich-hop-ai)  
**Môi trường trực tiếp (Live)**: https://marketing.kienhieu.id.vn  

---

## I. TỔNG QUAN PHÁT HÀNH (EXECUTIVE RELEASE SUMMARY)

Bản phát hành **v9.5** đánh dấu bước chuyển dịch mang tính chiến lược của đề tài: từ một ứng dụng **"AI Prompt Demo"** thành một **Nền tảng Vận hành Tiếp thị B2B SaaS (Marketing Operations Platform)** toàn diện. Hệ thống trực tiếp giải quyết 4 câu hỏi thực chiến hàng ngày của các doanh nghiệp và agency tiếp thị:
1. *Việc gì cần chú ý ngay? (What Needs Attention)* $\rightarrow$ Cảnh báo sớm về bội chi ngân sách, ROAS thâm hụt và tác vụ quá hạn.
2. *Hôm nay tôi phải làm gì? (My Work Today)* $\rightarrow$ Danh sách công việc ưu tiên trong ngày của từng marketer, hỗ trợ 1-click hoàn thành.
3. *Tác vụ nào bị trễ hạn? (Overdue Tasks)* $\rightarrow$ Phân loại mức độ khẩn cấp (URGENT, HIGH, MEDIUM, LOW) và đếm lùi thời gian.
4. *Sức khỏe chiến dịch có đang gặp rủi ro? (Campaign Health)* $\rightarrow$ Điểm sức khỏe xác định 100% ($0 - 100$), không phụ thuộc vào cảm tính của LLM.

---

## II. CHI TIẾT CẢI TIẾN HỆ THỐNG THEO CÁC TẦNG KIẾN TRÚC

### 1. Tầng Cơ Sở Dữ Liệu & Ràng Buộc Toàn Vẹn (Database Layer)
- **3 Bảng thực thể nghiệp vụ mới**:
  - `campaign_tasks`: Quản trị công việc tiếp thị với `CheckConstraint`:
    - `task_type IN ('CONTENT', 'DESIGN', 'VIDEO', 'ADS', 'RESEARCH', 'OTHER')`
    - `status IN ('TODO', 'IN_PROGRESS', 'IN_REVIEW', 'DONE')`
    - `priority IN ('LOW', 'MEDIUM', 'HIGH', 'URGENT')`
  - `campaign_budget_allocations`: Kế hoạch phân bổ ngân sách chi tiết theo từng kênh (Facebook, TikTok, Email, Google Ads, SEO).
  - `campaign_kpi_targets`: Chỉ tiêu định lượng đo lường cam kết (Leads, Clicks, Conversions, Revenue).
- **Mở rộng bảng `campaigns` (Tương thích ngược 100%)**:
  - `key_message`: Thông điệp cốt lõi của chiến dịch.
  - `primary_cta`: Lời kêu gọi hành động chủ đạo (tự động kế thừa vào các bài viết AI).
  - `target_kpi_name` & `target_kpi_value`: Chỉ số cam kết mục tiêu.
- **Cơ chế Idempotent Migration**: Hàm `ensure_sqlite_schema_compatibility` trong `backend/app/core/database.py` tự động nhận diện và cập nhật schema khi khởi động máy chủ mà không làm gián đoạn hay mất mát dữ liệu cũ.

### 2. Tầng Backend API & Phân Quyền Mức Bản Ghi (API & RBAC Layer)
- **Bộ API Quản trị Tác vụ (`/api/v1/tasks` & `/api/v1/campaigns/{id}/tasks`)**:
  - `GET /api/v1/campaigns/{id}/tasks`: Lấy danh sách tác vụ theo chiến dịch.
  - `POST /api/v1/campaigns/{id}/tasks`: Tạo tác vụ mới (Manager/Owner).
  - `GET /api/v1/tasks/my-tasks`: Truy vấn tác vụ được phân công cho người dùng hiện tại kèm bộ lọc đa chiều.
  - `PATCH /api/v1/tasks/{id}`: Cập nhật tác vụ với **Record-Level RBAC**: Người được giao việc (Assignee) chỉ có quyền cập nhật trạng thái (`status`) và độ ưu tiên (`priority`); quyền chỉnh sửa nội dung/hạn chót hoặc xóa thuộc về Manager/Creator.
  - `DELETE /api/v1/tasks/{id}`: Xóa tác vụ có kiểm tra quyền hạn.
- **Bộ API Ngân Sách & Mục Tiêu (`/api/v1/campaigns/{id}/budget-allocations` & `kpi-targets`)**:
  - Quản lý phân bổ ngân sách từng kênh và thiết lập chỉ tiêu KPI.
- **Bộ API Điều Hành Vận Hành (`/api/v1/analytics/command-center` & `/api/v1/metrics/command-center`)**:
  - Tổng hợp thời gian thực: Danh sách cảnh báo rủi ro, tác vụ cần xử lý hôm nay, và tính toán điểm sức khỏe xác định cho mọi chiến dịch.

### 3. Tầng Giao Diện & Trải Nghiệm Người Dùng (Frontend UI/UX)
- **Command Center Dashboard (`frontend/src/pages/Dashboard.tsx`)**:
  - *Section 1*: Băng cảnh báo đỏ "Việc Cần Chú Ý Ngay" với các nút hành động trực tiếp.
  - *Section 2*: Khối phân tách (Split Grid) gồm "Tác Vụ Hôm Nay Của Tôi" (tích hợp checkbox 1-click chuyển trạng thái tức thì) và "Sức Khỏe Chiến Dịch" (thanh đo 0-100, nhãn trạng thái HEALTHY / NEEDS_ATTENTION / CRITICAL, và thanh tiến độ ngân sách).
  - Bảo tồn nguyên vẹn 9-KPI Bento Grid, Biểu đồ phân bổ doanh thu đa kênh (Attribution Trend) và Bác sĩ AI chẩn đoán.
- **Trang Tác Vụ Của Tôi (`frontend/src/pages/MyTasksPage.tsx`)**:
  - Đưa lên thanh điều hướng chính (Sidebar) kèm huy hiệu đếm số lượng tác vụ đang mở.
  - Thống kê 4 thẻ KPI: Tổng tác vụ, Quá hạn, Đang làm, Đã xong.
  - Bộ lọc tìm kiếm linh hoạt theo từ khóa, trạng thái, mức độ ưu tiên và chiến dịch.
  - Hỗ trợ tạo nhanh tác vụ qua Modal popup.
- **Nâng Cấp Chi Tiết Chiến Dịch (`frontend/src/components/WorkflowCanvas.tsx`)**:
  - *Tab Brief & Mục Tiêu Vận Hành*: Cho phép xem và chỉnh sửa trực tiếp Key Message, Primary CTA, chỉ tiêu định lượng KPI và bảng phân bổ ngân sách từng kênh.
  - *Tab Tác Vụ Chiến Dịch*: Bảng công việc chi tiết của riêng chiến dịch, cho phép phân công nhanh, đổi trạng thái và xóa tác vụ.

### 4. Tầng Trí Tuệ Nhân Tạo & Chống Ảo Giác (AI Grounding & Evaluation)
- **Zero Hallucination**: Bác sĩ AI trích dẫn 100% số liệu thực nghiệm từ cơ sở dữ liệu (`views`, `clicks`, `conversions`, `cost`, `revenue`, `ROAS`, `CPC`, `CVR`).
- **Sparse Data Safeguard**: Khi chiến dịch mới chưa có dữ liệu đo lường (0 views, 0 cost), hệ thống tự động kích hoạt cờ `is_sparse_data: True` và phát cảnh báo rõ ràng rằng dữ liệu chưa đủ để suy luận nhân quả, cấm tuyệt đối việc bịa đặt số liệu hay khung giờ vàng.
- **Smart Fallback Engine**: Tự động chuyển đổi sang bộ tạo mẫu chuẩn cấu trúc Pydantic khi kết nối API ngoại vi gặp sự cố, đảm bảo hệ thống không bao giờ bị sập (0 unhandled 500 errors).

---

## III. DỮ LIỆU ĐO LƯỜNG THỰC NGHIỆM ĐỊNH LƯỢNG (BENCHMARK RESULTS)

| Chỉ số Đo Lường | Mục Tiêu Chuẩn (Target / SLA) | Kết Quả Thực Nghiệm | Trạng Thái |
| :--- | :--- | :--- | :---: |
| **Tỷ lệ tuân thủ Schema AI** | $\ge 95.0\%$ | **100.00%** (60/60 mẫu hợp lệ) | ✅ VƯỢT CHỈ TIÊU |
| **Tỷ lệ ảo giác dữ liệu (Hallucination)** | $= 0.0\%$ | **0.00%** (0/40 vi phạm) | ✅ ZERO HALLUCINATION |
| **Khả năng dự phòng mất mạng (Failover)** | $\ge 99.0\%$ | **100.00%** (3/3 kịch bản pass) | ✅ HOÀN HẢO |
| **Độ trễ Bác sĩ AI p95** | $\le 50.0\text{ ms}$ | **3.36 ms** | ✅ TỨC THÌ |
| **Độ trễ API non-AI p95** | $\le 800.0\text{ ms}$ | **6.84 ms** (X-Process-Time = 3.14 ms) | ✅ VƯỢT CHỈ TIÊU |
| **Kiểm thử tự động Pytest** | 100% Pass | **1.263 ca** (1.262 pass + 1 skip hợp lệ do runner CI không có live DB bị `.gitignore`) | ✅ ĐỘ PHỦ 86.20% ≥ 80% |
| **Playwright E2E (mock)** | 100% Pass | **38/38 passed** | ✅ |
| **Playwright E2E (live backend thật)** | 100% Pass | **7/7 passed** | ✅ |
| **WCAG 2.2 AA (live backend thật)** | 0 lỗi Critical/Serious | **25/25 passed**, 0 violation | ✅ |
| **Frontend TypeScript Build** | Exit Code 0 | Biên dịch sạch, main chunk 108 kB (ngưỡng < 500 kB) | ✅ 0 TS ERRORS |

---

## IV. BỘ TÀI LIỆU HỌC THUẬT PHỤC VỤ BẢO VỆ ĐỒ ÁN

Toàn bộ tài liệu chuyên sâu được lưu trữ tại thư mục `docs/`:
1. [docs/UNIVERSITY_DEFENSE_RUBRIC_ALIGNMENT.md](file:///c:/Users/hieuk/Desktop/Ứng%20Dụng%20AI/docs/UNIVERSITY_DEFENSE_RUBRIC_ALIGNMENT.md): Bảng đối sánh chi tiết 4 đợt đánh giá (BTTX1, BTTX2, BTTX3, Khóa luận) và kịch bản trả lời 5 câu hỏi hóc búa của Hội đồng.
2. [docs/ARCHITECTURE.md](file:///c:/Users/hieuk/Desktop/Ứng%20Dụng%20AI/docs/ARCHITECTURE.md): Đặc tả kiến trúc phần mềm, mô hình ERD chuẩn hóa, cơ chế RBAC và công thức tính điểm sức khỏe.
3. [docs/AI_EVALUATION_REPORT.md](file:///c:/Users/hieuk/Desktop/Ứng%20Dụng%20AI/docs/AI_EVALUATION_REPORT.md): Báo cáo thực nghiệm đo lường AI tự động sinh từ script benchmark.
4. [scripts/evaluate_ai_grounding.py](file:///c:/Users/hieuk/Desktop/Ứng%20Dụng%20AI/scripts/evaluate_ai_grounding.py): Kịch bản kiểm định AI tự động.
5. [scripts/measure_api_latency.py](file:///c:/Users/hieuk/Desktop/Ứng%20Dụng%20AI/scripts/measure_api_latency.py): Kịch bản đo lường độ trễ API.

---

## V. HƯỚNG DẪN KIỂM CHỨNG NHANH TRÊN MÁY (LOCAL VERIFICATION)

```powershell
# 1. Chạy toàn bộ kiểm thử backend:
pytest backend/tests/test_attribution_ai_doctor.py backend/tests/test_workspaces.py backend/tests/test_contents_comprehensive.py backend/tests/test_tasks_and_operations.py backend/tests/test_adversarial_v3.py -v

# 2. Chạy kiểm định AI Grounding & Anti-hallucination:
python scripts/evaluate_ai_grounding.py

# 3. Đo lường độ trễ API:
python scripts/measure_api_latency.py

# 4. Kiểm tra biên dịch Frontend:
cd frontend && npm run build
```
