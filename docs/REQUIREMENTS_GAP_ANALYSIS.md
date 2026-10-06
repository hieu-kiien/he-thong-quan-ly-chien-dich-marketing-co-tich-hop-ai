# Phân tích khoảng cách: yêu cầu viết ↔ rubric ↔ mã nguồn

**Mục đích.** Tài liệu này đối chiếu ba nguồn yêu cầu với nhau, chỉ ra chỗ nào đã
làm, chỗ nào chưa làm, và chỗ nào chúng **mâu thuẫn nhau**.

**Nguyên tắc.** Ưu tiên khi hai nguồn xung đột là rubric chính thức, vì đó là thứ
được chấm. Nhưng xung đột không được giấu — phải nêu ra để giảng viên hỏi thì
trả lời được.

---

## 1. Các nguồn đã đọc

| Nguồn | Loại | Phạm vi | Đã đọc |
|---|---|---|---|
| `yêu cầu của môn học.png` | **Rubric chính thức** | 4 phần × 10 tiêu chí | Đầy đủ |
| `ORIGINAL_REQUEST.md` | Yêu cầu viết, 4 đợt (22/23/23/24-09) | R1–R6 mỗi đợt + acceptance criteria | Đầy đủ, 230 dòng |
| `BIEN_BAN_NGHIEM_THU.md` | Biên bản nghiệm thu | Tự ghi rõ là hồ sơ lịch sử | Đầy đủ |
| `Bao_Cao_AIA331_80300_ICTU_V9/research_pack/requirements-traceability.csv` | Ma trận truy vết | 20 dòng, 12 cột | Đầy đủ |
| `docs/`, `README.md`, `cloudflare/README.md`, `render.yaml` | Tài liệu kỹ thuật | — | Đầy đủ |
| `it-thesis-research-documentation-engineer/` | Gói skill hỗ trợ | Xem `README-VI.md` | Đủ để kết luận |

**Kết luận về `it-thesis-research-documentation-engineer/`:** đây **không phải** một
phần của bài nộp. Nó là một gói *agent skill* dùng để hướng dẫn quy trình nghiên cứu
và soạn báo cáo (đọc yêu cầu môn học → lập evidence map → traceability → kiến trúc
→ kế hoạch eval → compile LaTeX). Nó là **công cụ**, không phải sản phẩm. Không cần
đưa vào thuyết trình; có thể nhắc là "quy trình đã dùng để sinh ra báo cáo".

---

## 2. XUNG ĐỘT QUAN TRỌNG NHẤT: cấm Claude/GPT vs rubric bắt buộc Claude

Đây là xung đột duy nhất giữa các nguồn, và nó là xung đột ngược ý.

| Nguồn | Nội dung |
|---|---|
| `ORIGINAL_REQUEST.md` (đợt 2026-09-23), dòng 101 | *"TUYỆT ĐỐI KHÔNG sử dụng các mô hình Claude 3.7, Claude 3.6, Sonnet, và các dòng GPT (OpenAI). Tối ưu hóa bằng Gemini."* |
| Cùng đó, acceptance criteria dòng 150 | *"Không sử dụng các mô hình bị cấm (Claude 3.7, Claude 3.6, Sonnet, GPT)."* |
| `yêu cầu của môn học.png`, Bài 3 mục 2 | *"Kết nối API/model AI đa dạng: Gọi được OpenAI/Gemini/**Claude**/HuggingFace/**Ollama**"* |

**Vì sao vẫn phải hỗ trợ Claude và GPT:** rubric là thứ được chấm điểm, và nó yêu
cầu tên đích danh Claude. Yêu cầu viết lại đến từ một đợt cấu hình trước, không phải
từ đề bài.

**Cách đã giải quyết:** hỗ trợ đủ provider theo rubric, và **không** dùng model bị
cấm ở bất kỳ đâu. Cụ thể:

- Registry có `anthropic`, nhưng model mặc định là `claude-3-5-haiku-latest`, không
  phải 3.7/3.6/Sonnet.
- Không có model GPT nào được chọn làm mặc định; `openai` là tuỳ chọn theo cấu hình.
- Production đang chạy `opencode / space-bunny-free` (`render.yaml`), không thuộc
  danh sách cấm.

**Cách trình bày khi bị hỏi:** nói thẳng là có hai văn bản yêu cầu mâu thuẫn nhau,
rubric được ưu tiên, và ràng buộc "không dùng model bị cấm" vẫn được tôn trọng.
Đây là câu trả lời được cả điểm về sự trung thực lẫn điểm về kỹ thuật.

**Việc còn làm:** cập nhật `ORIGINAL_REQUEST.md` không — đó là hồ sơ lịch sử của
người yêu cầu, không sửa. Ghi chú này trong tài liệu là đủ.

---

## 3. Đối chiếu từng yêu cầu viết

### 3.1 Đợt 2026-09-22 (rà soát mã nguồn, UI/UX, CI/CD, QA độc lập)

| Yêu cầu | Trạng thái | Bằng chứng |
|---|---|---|
| R1 Rà soát backend: API, SQLAlchemy, Pydantic, JWT, RBAC, CORS, AI fallback | Đã có | 19 bảng, 13 router; sửa lỗi tầng AI và phân quyền |
| R2 Đánh giá & tối ưu UI/UX | Đã có | ErrorBoundary, Skeleton, Toast, responsive; CI Gate 4 chạy axe |
| R3 Thiết lập CI/CD | Đã có + mở rộng | `.github/workflows/ci.yml` — 8 gate |
| R4 Mở rộng test + giám sát độc lập | Đã có | Bộ test lớn; test adversarial chống leo quyền và bypass state machine |
| AC: không endpoint nào trả 500 khi dữ liệu thiếu | Đã có + test | Validate Pydantic; test adversarial |
| AC: `npm run build` sạch | Đã có | CI Gate 2 |
| AC: 3 trạng thái loading / empty / lỗi | Đã có | `Skeleton.tsx`, `ErrorBoundary.tsx`, `ServerAwakeningIndicator.tsx` |
| AC: review queue + AI Drawer mượt | Đã có | Playwright golden-journey |
| AC: Docker Compose build được | Đã có | CI Gate 6 |

### 3.2 Đợt 2026-09-23 (DAG + feedback loop; rồi bảo mật + AI evaluation)

| Yêu cầu | Trạng thái | Bằng chứng |
|---|---|---|
| R1 Phân quyền mức bản ghi | Đã có + test | `check_campaign_access*`; `test_multi_tenant_hardening.py` |
| R1 Vá state machine duyệt nội dung | Đã có + test | Không tạo/sửa thẳng sang `APPROVED`/`PUBLISHED`; `test_adversarial_v3.py` |
| R1 `RoleChecker` theo trạng thái CSDL | Đã có + test | `test_v3_security_and_state_machine.py` |
| R1 Khửa ảo giác AI fallback | Đã có + test | `is_fallback`, `model_provider`, cảnh báo; [tài liệu đạo đức](AI_ETHICS_AND_HUMAN_OVERSIGHT.md) mục 2 |
| R2 Đo định lượng: latency, schema rate, grounding | Đã có + đo được | `docs/AI_EVALUATION_REPORT.md`; schema rate đo bằng harness prompt |
| R2 Test đối kháng chống leo quyền | Đã có | `test_adversarial_v3.py` |
| R3 RTM không còn mục `DESIGNED` | Đã có | CSV V9: 12 `TESTED`, 5 `MEASURED`, 3 `IMPLEMENTED` |
| R3 Báo cáo V9 8 chương | Đã có | `Bao_Cao_AIA331_80300_ICTU_V9/` |
| R4 `BIEN_BAN_NGHIEM_THU.md` bỏ tuyên bố thổi phồng | Đã có | Biên bản ghi rõ là hồ sơ lịch sử |
| AC: **Mutation testing đạt 100% Oracle Effectiveness** | **CHƯA LÀM** | Không có `mutmut`, không có cấu hình mutation trong repo. Đợt này mới chỉ tự kiểm chứng từng guard bằng cách gỡ bản vá rồi xem test có đỏ không |
| AC: ít nhất 149 test, 0 lỗi | Vượt | 1397 test |

### 3.3 Đợt 2026-09-24 (multi-workspace, AI 3 kênh, brand safety, social preview, đo lường, BYOK)

| Yêu cầu | Trạng thái | Bằng chứng |
|---|---|---|
| R1 Multi-workspace cách ly dữ liệu | Đã có + test | `workspace_members`; `test_multi_tenant_hardening.py` |
| R1 Brand Kit: USP, tone, từ cấm | Đã có + test | `brand_kits`; `test_brand_kit.py` |
| R1 Luồng đăng ký / đăng nhập thật | Đã có | `auth.py`; chặn tự đăng ký vai trò đặc quyền |
| R1 **Loại bỏ đăng nhập demo tự động** | **ĐÃ SỬA** | Xem mục 4.1 |
| R2 AI 3 kênh: Facebook / TikTok / Email | Đã có + test | `/ai/omnichannel`; mockup cả 3 kênh |
| R3 Guardrail tuân thủ | Đã có + test | `ComplianceScanner`, 38 quy tắc `AD_POLICY` |
| R3 Cổng duyệt bắt buộc | Đã có + test | `can_submit` chặn mức HIGH |
| R4 Social Preview 3 kênh | Đã có | `FacebookPreviewCard`, `TikTokPhoneMockup`, `EmailInboxPreview` |
| R4 Đính kèm ảnh vào bài | Đã có | Trường ảnh trên nội dung, hiển thị trong mockup |
| R4 1-Click Copy giữ định dạng | Đã có | `ExportActions.tsx` (`handleCopyAllContents`) |
| R4 **Xuất kế hoạch chiến dịch ra Excel/PDF** | **MỘT PHẦN** | Có CSV và in trình duyệt (`ExportActions.tsx`). **Không có** xuất file Excel hay PDF kế hoạch. Endpoint `/export/data` là JSON cứu hộ cho ADMIN, không phải xuất kế hoạch |
| R5 Metrics + CTR/CPC/CVR/ROAS/ROI | Đã có + test | `metrics.py` có cả ROI (`roi_percent`) |
| R5 AI Doctor | Đã có + test | `ai_doctor.py`, quy tắc tất định, không gọi LLM |
| R6 Settings + BYOK + Test API Connection | Đã có + test | `settings.py`; `test_settings_byok.py` |
| AC: **Xuất Excel/PDF** | **CHƯA LÀM** | Như trên |

---

## 4. Khoảng cách còn lại, xếp theo mức độ

### 4.1 Đã sửa trong đợt này

| # | Vấn đề | Mức độ | Cách sửa |
|---|---|---|---|
| 1 | Ba nút "chọn nhanh tài khoản" trên trang đăng nhập chứa sẵn `Manager@123`, `Marketer@123`, `Approver@123`, **luôn hiển thị** | Cao | Chỉ render khi `VITE_ENABLE_OFFLINE_DEMO=true`. Vì Vite bake biến môi trường vào bundle, chuỗi mật khẩu từng nằm trong JavaScript gửi tới mọi trình duyệt. Có test `test_seed_credentials_not_shipped.py` chặn gỡ bản vá |

### 4.2 Chưa làm — nên nói thẳng, không giấu

| # | Khoảng cách | Ảnh hưởng rubric | Vì sao chưa làm | Đề xuất |
|---|---|---|---|---|
| 1 | **Phân trang** cho `/campaigns`, `/contents`, `/tasks` | Bài 2 mục 4 | Tốn công đụng cả contract API và UI | Thêm `limit`/`offset` + tổng số. Đây là việc nên làm nhất |
| 2 | **Mutation testing** 100% | AC của đợt 23-09 | Cần thêm công cụ (`mutmut`) và thời gian chạy lớn | Chạy `mutmut` cho `compliance_service` và `contents.py` — hai module quyết định an toàn |
| 3 | **Xuất Excel/PDF** kế hoạch | AC của đợt 24-09 | Cần thư viện tạo file và thiết kế định dạng | `openpyxl` cho Excel là rẻ nhất; PDF khó hơn |
| 4 | **Diễn tập backup/restore** Postgres | Thiết kế mục 3 | Cần môi trường thật | Neon có backup theo thời gian; cần chứng minh khôi phục được |
| 5 | **Đo tải đồng thời** | Thiết kế mục 7 | Cần môi trường và kịch bản | Chạy kịch bản N người ghi đồng thời, ghi lại P95 |
| 6 | **Kiểm thử thiên lệch đầu ra AI** | Bài 3 mục 10; Thiết kế mục 5 | Cần bộ ca đánh giá có người chấm | Bộ ca tiếng Việt soạn thủ công, chấm theo tiêu chí giọng thương hiệu |
| 7 | **Đo chất lượng văn phong** bằng mô hình thật | Bài 3 mục 4 | Harness hiện dùng stub tất định | Chạy 3 phiên bản trên một provider thật, ghi latency + chi phí |

### 4.3 Nợ kỹ thuật nhỏ

| Nợ | Ảnh hưởng |
|---|---|
| `metrics.py` có cặp route trùng nghĩa | Rối tài liệu API |
| `config.py` còn biến `*_BASE_URL` không dùng | Dễ gây hiểu nhầm khi đọc cấu hình |
| Chưa có công cụ migration (`create_all()` không sửa bảng cũ) | Rủi ro khi thêm cột ở production |
| Chưa có connector gửi email/xã hội thật | `PUBLISHED` chỉ là trạng thái nội bộ |

---

## 5. Những chỗ yêu cầu viết tự mâu thuẫn

Ngoài xung đột Claude ở mục 2, còn hai chỗ:

| Chỗ | Vấn đề | Xử lý |
|---|---|---|
| Yêu cầu "0 errors, 0 warnings" cho pytest (đợt 22-09) | Câu chữ không khả thi tuyệt đối: mọi dự án đều có cảnh báo thiểu | Chạy `-p no:warnings` khi cần; CI không cấu hình `-W error` |
| Yêu cầu "adversarial tests đạt 100% kháng cự" và "mutation 100%" | Ngôn ngữ không định nghĩa rõ mẫu số, dễ dẫn tới tuyên bố vô căn cứ | Không tuyên bố con số này. Báo cáo số test thật và giới hạn đo được |

---

## 6. Thứ tự nên làm tiếp

| Ưu tiên | Việc | Lý do |
|---|---|---|
| 1 | Thêm phân trang cho 3 danh sách chính | Bắt một tiêu chí rubric đang để trống, và sửa được trong một lần làm gọn |
| 2 | Chốt `DATABASE_URL` production + diễn tập restore | Rủi ro mất dữ liệu thật lớn hơn mọi thứ khác |
| 3 | Chạy `mutmut` trên 2 module an toàn | Đáp ứng AC còn nợ, mà không cần làm cho cả dự án |
| 4 | Đo tải đồng thời | Bổ sung con số cho Thiết kế mục 7 |
| 5 | Xuất Excel kế hoạch | Đáp ứng AC của đợt 24-09 |
| 6 | Bộ ca đánh giá thiên lệch AI | Cần thời gian chuẩn bị; nên làm sau khi 5 việc trên xong |
