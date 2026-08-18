---
document_id: AIA331-REPORT-NHOM25
document_type: project-analysis-and-design-report
project_id: AIA331-80300-MARKETING-AI
project_title: Hệ thống quản lý chiến dịch marketing có tích hợp AI
course: Ứng dụng trí tuệ nhân tạo - AIA331
assignment_code: "80300"
priority: P1
status: SUBMISSION_CANONICAL
version: 1.0
authors: [Nguyễn Hải Đăng, Vũ Hiếu Kiên]
class: CNTTK23C
last_reviewed: 2026-08-18
---

# BÁO CÁO DỰ ÁN

## HỆ THỐNG QUẢN LÝ CHIẾN DỊCH MARKETING CÓ TÍCH HỢP AI

**Học phần:** Ứng dụng trí tuệ nhân tạo - AIA331
**Mã số:** 80300
**Hình thức:** Dự án
**Nhóm:** 25
**Lớp:** CNTTK23C
**Khoa:** Công nghệ thông tin
**Trường:** Trường Đại học Công nghệ Thông tin và Truyền thông Thái Nguyên
**Thành viên:** Nguyễn Hải Đăng (`dtc2451200051`); Vũ Hiếu Kiên (`dtc245200244`)
**Cấp ưu tiên hồ sơ:** P1 / HIGH — metadata quản lý nội bộ của nhóm

> Tài liệu này là báo cáo phân tích và thiết kế theo đề bài `source-materials/DỰ ÁN.png`.
> Nội dung chưa có code/test được đánh dấu `PROPOSED` hoặc `OPEN`, không trình bày
> như kết quả đã nghiệm thu.

## Tóm tắt

Doanh nghiệp cần quản lý tập trung chiến dịch marketing, kênh truyền thông, nội
dung, ngân sách, lịch đăng và các chỉ số lượt xem, click, chuyển đổi, chi phí.
Báo cáo đề xuất hệ thống Django + SQLite có phân quyền, CRUD chiến dịch, luồng
duyệt nội dung và lớp AI sinh bản nháp. AI được đặt sau adapter có prompt version,
fallback offline và cảnh báo; người phụ trách phải duyệt trước khi sử dụng.

Baseline trong repo đã kiểm chứng model `Campaign`, `Channel`, `Content`,
`Metric`, thống kê CTR/chi phí/chuyển đổi, approval gate, CRUD tra cứu chiến dịch
và fallback AI. Provider ngoài, báo cáo AI đầy đủ trong UI và RAG nghiệp vụ là
phần mở rộng `PROPOSED`.

---

## 1. Nguồn và phạm vi

### 1.1. Nguồn chính

| ID | Nguồn | Trạng thái | Vai trò |
|---|---|---|---|
| SRC-001 | `source-materials/DỰ ÁN.png` | CANONICAL | Đề tài, học phần, mã và yêu cầu |
| SRC-002 | `project.md` | CANONICAL | Bản yêu cầu có ID truy vết |
| SRC-003 | `informember.md` | CANONICAL | Thành viên, lớp, khoa, trường |
| SRC-004 | `marketing_management/` | IMPLEMENTED_BASELINE | Mã nguồn baseline |
| SRC-005 | `marketing_management/campaigns/tests.py` | IMPLEMENTED_BASELINE | Test hành vi |

### 1.2. Ranh giới

Phạm vi chính là quản lý chiến dịch marketing và AI hỗ trợ nội dung/phân tích.
Các module sản phẩm, hóa đơn, tồn kho, nhập hàng trong thư mục lịch sử thuộc một
đề tài khác và không được dùng để kết luận về dự án này.

---

## 2. Phân tích bài toán quản lý

### 2.1. Bối cảnh và vấn đề

Thông tin marketing thường bị phân tán ở bảng tính, mạng xã hội, email và các
file báo cáo. Hệ quả là:

- khó biết chiến dịch nào đang chạy, mục tiêu và ngân sách bao nhiêu;
- nội dung không gắn chặt với kênh và lịch đăng;
- số liệu lượt xem, click, chuyển đổi, chi phí khó tổng hợp;
- việc lên ý tưởng và viết caption/email lặp lại;
- nội dung AI có thể chứa claim chưa kiểm chứng nếu không có quy trình duyệt.

### 2.2. Mục tiêu

1. Tập trung hóa campaign, channel, content, schedule, budget và metric.
2. Cho phép tìm kiếm, lọc và thống kê hiệu quả chiến dịch.
3. Dùng AI để sinh ý tưởng/caption/email nháp, tóm tắt metric và gợi ý cải thiện.
4. Bảo đảm người dùng kiểm duyệt nội dung AI trước khi dùng.
5. Lưu được prompt version, trạng thái và bằng chứng kiểm thử.

### 2.3. Actor

| Actor | Use case chính | Quyền dự kiến |
|---|---|---|
| Marketing Manager | Quản lý campaign, xem metric, duyệt content, xem AI summary | Đọc/ghi theo phạm vi quản lý |
| Marketing Staff | Nhập content, lịch đăng, metric, gọi AI sinh nháp | Đọc/ghi nghiệp vụ được giao |
| AI Service | Sinh ý tưởng, draft, summary | Không tự ghi/publish; chỉ nhận context đã lọc |

---

## 3. Yêu cầu chức năng

| ID | Mô tả | Input | Output | Trạng thái |
|---|---|---|---|---|
| FR-001 | Đăng nhập/phân quyền | username/password/role | phiên đăng nhập, quyền | IMPLEMENTED_BASELINE một phần |
| FR-002 | Quản lý campaign | tên, objective, audience, product, dates, budget, status | bản ghi campaign | IMPLEMENTED_BASELINE |
| FR-003 | Quản lý channel | tên, loại, active | bản ghi channel | IMPLEMENTED_BASELINE model/admin |
| FR-004 | Quản lý content/schedule | channel, title/body/type/scheduled_at | content gắn campaign | IMPLEMENTED_BASELINE create |
| FR-005 | Ghi metric | ngày, views, clicks, conversions, cost | metric theo campaign/channel | IMPLEMENTED_BASELINE model |
| FR-006 | Duyệt content | content, approver, action | approved/rejected/published | IMPLEMENTED_BASELINE guard |
| FR-007 | Tìm kiếm/lọc | tên/status | danh sách campaign | IMPLEMENTED_BASELINE |
| FR-008 | Thống kê | metric | totals, CTR, conversion rate, CPA | IMPLEMENTED_BASELINE |
| AI-001 | Sinh ý tưởng | brief/objective/audience/product/channel/tone | 5 ideas | IMPLEMENTED_BASELINE fallback |
| AI-002 | Sinh caption/email | brief/channel/tone | draft theo kênh | PROPOSED mở rộng UI |
| AI-003 | Tóm tắt/gợi ý | metrics/budget/period | summary/recommendations | PROPOSED |

### 3.1. Acceptance criteria cốt lõi

- `start_date` không sau `end_date`.
- `clicks <= impressions`, `conversions <= clicks`.
- Không trùng metric cùng campaign/channel/ngày.
- Nội dung AI ở trạng thái draft/pending không được publish.
- Không có API key trong repository.
- Khi không có provider, fallback trả đúng 5 ý tưởng và luôn có warning human review.

---

## 4. Yêu cầu phi chức năng

| ID | Nhóm | Yêu cầu | Cách xác minh |
|---|---|---|---|
| NFR-001 | Security | authentication, authorization, CSRF, env secret | code review + test quyền |
| NFR-002 | AI safety | không bịa claim, không tự đăng, có warning | unit/integration test + review |
| NFR-003 | Data integrity | validation và unique constraint | model test/migration |
| NFR-004 | Availability | migrate/seed/run từ môi trường sạch | runbook |
| NFR-005 | UX | status/filter/error message rõ | manual/browser check |
| NFR-006 | Maintainability | module hóa app, prompt tách khỏi view | structure review |

---

## 5. Use case

### UC-01 — Tạo chiến dịch

- **Actor:** Marketing Manager/Staff.
- **Tiền điều kiện:** đã đăng nhập và có quyền.
- **Luồng chính:** mở form → nhập objective/audience/product/dates/budget → hệ
  thống validate → lưu campaign → hiển thị chi tiết.
- **Ngoại lệ:** ngày sai hoặc ngân sách âm → báo lỗi, không lưu.
- **Hậu điều kiện:** campaign có status và người tạo.

### UC-02 — Sinh nội dung AI và duyệt

- **Actor:** Staff yêu cầu; Manager duyệt.
- **Luồng chính:** chọn brief/kênh/giọng → AI adapter tạo draft → lưu/hiển thị
  warning → Manager kiểm tra → approve → mới cho publish.
- **Ngoại lệ:** provider lỗi/thiếu key → fallback; thiếu dữ liệu → warning.
- **Hậu điều kiện:** content có source AI, prompt version và trạng thái duyệt.

### UC-03 — Theo dõi hiệu quả

- **Actor:** Manager/Staff được cấp quyền.
- **Luồng chính:** nhập metric theo ngày/kênh → hệ thống validate → aggregate →
  hiển thị views/clicks/conversions/cost/CTR/CPA.
- **Ngoại lệ:** click vượt view hoặc conversion vượt click → từ chối.

---

## 6. Thiết kế dữ liệu

### 6.1. Bảng chính

| Bảng | Khóa chính | Khóa ngoại | Ràng buộc |
|---|---|---|---|
| `campaigns_channel` | id | — | name unique |
| `campaigns_campaign` | id | created_by → User | budget >= 0, date range |
| `campaigns_content` | id | campaign, channel, approved_by | status workflow |
| `campaigns_metric` | id | campaign, channel | unique campaign/channel/date; nonnegative |

### 6.2. Quan hệ

- Campaign 1–N Content.
- Campaign 1–N Metric.
- Channel 1–N Content.
- Channel 1–N Metric.
- User 1–N Campaign qua `created_by` và 1–N Content qua `approved_by`.

Sơ đồ nguồn: [`../../docs/diagrams/erd.dot`](../../docs/diagrams/erd.dot).

---

## 7. Kiến trúc hệ thống

```text
Browser
  -> Django URLs/Views + auth/RBAC
  -> Forms/Services/validation
  -> Django ORM + SQLite
  -> Campaign/Channel/Content/Metric
  -> AI adapter (prompt version + provider/fallback)
```

### 7.1. Mapping code

| Layer | File | Trách nhiệm | Trạng thái |
|---|---|---|---|
| Config | `marketing_management/config/settings.py` | Django/SQLite/env | IMPLEMENTED_BASELINE |
| Model | `campaigns/models.py` | entity, validation, aggregate, approval | IMPLEMENTED_BASELINE |
| Form | `campaigns/forms.py` | input form | IMPLEMENTED_BASELINE |
| Service | `campaigns/services.py` | create campaign transaction | IMPLEMENTED_BASELINE |
| View | `campaigns/views.py` | auth/list/create/detail/AI endpoint | IMPLEMENTED_BASELINE |
| AI | `campaigns/ai_service.py` | prompt/provider/fallback | IMPLEMENTED_BASELINE |
| Test | `campaigns/tests.py` | hành vi cốt lõi | IMPLEMENTED_BASELINE |

---

## 8. Định vị AI

### 8.1. AI trong sản phẩm

AI-001/002 hỗ trợ tạo draft; AI-003 có thể tóm tắt metric. AI không phải nguồn
sự thật của ngân sách/metric và không tự thay đổi dữ liệu.

### 8.2. AI trong SDLC

| Giai đoạn | Cách sử dụng | Minh chứng |
|---|---|---|
| KT1 | phân tích actor, FR/NFR, ERD, vị trí AI | prompt + bản review |
| KT2 | sinh model/CRUD/test/debug | commit + test output |
| KT3 | thử prompt caption/summary, kiểm tra overclaim | prompt versions + evaluation |
| Cuối kỳ | tạo README/report/slide và review | artifacts + checklist |

---

## 9. Prompt và AI contract

### 9.1. Prompt system

```text
Bạn là trợ lý marketing. Tạo nội dung nháp để con người duyệt; chỉ dùng thông
tin được cung cấp; không bịa cam kết, số liệu, giải thưởng hoặc chứng nhận; không
tự đăng. Nếu thiếu dữ liệu, nêu warning.
```

### 9.2. Prompt user

```text
Campaign brief: {{campaign_brief}}
Objective: {{objective}}
Audience: {{audience}}
Product: {{product}}
Channel: {{channel}}
Tone: {{tone}}
Hãy đề xuất đúng 5 ý tưởng, mỗi ý tưởng gồm title, hook, draft và CTA.
```

### 9.3. Output contract

```json
{
  "provider": "fallback|provider-name",
  "prompt_version": "AI-CAM-001-v1",
  "ideas": [{"title": "...", "channel": "...", "hook": "...", "draft": "...", "cta": "..."}],
  "needs_human_approval": true,
  "warning": "..."
}
```

---

## 10. Kiểm thử và minh chứng

Lệnh đã dùng:

```powershell
cd marketing_management
.venv\Scripts\python.exe manage.py makemigrations campaigns
.venv\Scripts\python.exe manage.py migrate --noinput
.venv\Scripts\python.exe manage.py test campaigns -v 1
.venv\Scripts\python.exe manage.py check
```

Các test hiện có:

1. Aggregate metric và tính CTR/conversion rate/cost per conversion.
2. Chặn publish khi content AI chưa được duyệt; cho publish sau approve.
3. Fallback AI trả 5 ý tưởng, provider/fallback và warning/approval flag.
4. User staff xem được danh sách chiến dịch.

Kết quả gần nhất: **4 tests, OK; Django system check không có lỗi**. Đây là
bằng chứng baseline tại thời điểm báo cáo, không phải cam kết production.

---

## 11. Rủi ro và điểm mở

| ID | Rủi ro/điểm mở | Mức | Cách xử lý |
|---|---|---|---|
| RISK-001 | Provider ngoài chưa có integration test | Cao | dùng fallback; thêm test mock/contract |
| RISK-002 | AI overclaim hoặc prompt injection | Cao | grounding, warning, approval, redaction |
| RISK-003 | Quyền Manager/Staff cần chốt với giảng viên | Trung bình | ghi decision log, test ma trận quyền |
| RISK-004 | Báo cáo AI UI chưa hoàn thiện | Trung bình | làm sau baseline, giữ PROPOSED |
| RISK-005 | Tài liệu bán hàng cũ trong repo | Cao | manifest loại khỏi canonical, đánh dấu LEGACY |

---

## 12. Kế hoạch triển khai tiếp

1. Hoàn thiện channel/metric CRUD và filter theo kênh/thời gian.
2. Thêm màn hình AI ideas và tạo Content từ draft với audit record.
3. Thêm AI performance summary từ metric đã kiểm quyền.
4. Thêm test integration provider mock, injection, PII, timeout và schema lỗi.
5. Sinh DOCX/PDF/ZIP sau khi nội dung canonical ổn định.

## Kết luận

Đề tài đúng của nhóm là **Hệ thống quản lý chiến dịch marketing có tích hợp AI**,
không phải hệ thống quản lý bán hàng. Thiết kế đã xác định rõ bối cảnh, actor,
FR/NFR, dữ liệu, kiến trúc, vị trí AI, prompt và cơ chế duyệt. Baseline code chứng
minh các phần cốt lõi ở mức học tập; các phần chưa có bằng chứng được giữ nhãn
`PROPOSED/OPEN` để bảo đảm trung thực học thuật.
