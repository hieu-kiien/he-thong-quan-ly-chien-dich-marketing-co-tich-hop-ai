# Đối chiếu rubric AIA331 — 40 tiêu chí

**Nguồn rubric:** `yêu cầu của môn học.png` — 4 phần, mỗi phần 10 tiêu chí.
Bản cũ của tài liệu này nói "chưa có rubric chính thức"; nay đã đối chiếu với ảnh
rubric thật.

**Cách đọc bảng.** Trạng thái dùng năm nhãn:

| Nhãn | Nghĩa là |
|---|---|
| **Đã có + test** | Có trong mã nguồn, có test tự động chứng minh |
| **Đã có** | Có trong mã nguồn, chưa có test riêng |
| **Đo được** | Có số liệu hoặc bằng chứng chạy được |
| **Một phần** | Làm được phần nào, thiếu gì đã ghi rõ |
| **Chưa làm** | Không có, và nói thẳng là không có |

Không tiêu chí nào ở đây được đánh dấu "Đã có + test" nếu không có tên test thật
trong `backend/tests/` hoặc `frontend/tests/`.

---

## Phần 1 — Bài kiểm tra thường xuyên 1 (thiết kế)

| # | Tiêu chí | Trạng thái | Bằng chứng |
|---|---|---|---|
| 1 | Phân tích tác nhân toàn quân lý: bối cảnh, người dùng, dữ liệu, quy trình, vấn đề cần giải quyết | Đã có | [REQUIREMENTS_AND_DESIGN.md](REQUIREMENTS_AND_DESIGN.md) mục 1 |
| 2 | Xác định đầy đủ yêu cầu chức năng, có đầu vào / xử lý / đầu ra | Đã có | Cùng tài liệu, mục 2 — bảng FR-1…FR-13 |
| 3 | Yêu cầu phi chức năng: bảo mật, hiệu năng, khả dụng, sao lưu, phân quyền, trải nghiệm | Đã có + test | Cùng tài liệu, mục 3 — mỗi dòng có test hoặc file cụ thể |
| 4 | Thiết kế actor và use case, có sơ đồ Use Case hoặc mô tả tương đương | Đã có | Cùng tài liệu, mục 4 — sơ đồ mermaid + đặc tả UC-04/07/08/12 |
| 5 | Thiết kế CSDL: ERD, bảng, khoá chính/ngoại, ràng buộc, giải thích quan hệ | Đã có | [ARCHITECTURE.md](ARCHITECTURE.md) mục 2 — ERD + bảng ràng buộc |
| 6 | Kiến trúc hệ thống: frontend, backend, database, AI service, luồng dữ liệu chính | Đã có | [ARCHITECTURE.md](ARCHITECTURE.md) mục 1 — sơ đồ 3 tầng |
| 7 | Xác định vị trí ứng dụng AI: chức năng nào, gắn với dữ liệu nào, câu hỏi thực tế nào | Đã có | [REQUIREMENTS_AND_DESIGN.md](REQUIREMENTS_AND_DESIGN.md) mục 5 — kèm ranh giới AI không làm gì |
| 8 | Thiết kế prompt và luồng gọi AI: system prompt, user prompt mẫu, input/output format, ràng buộc, xử lý lỗi | Đã có | Cùng tài liệu, mục 6 — trích nguyên văn từ `prompts.json` |
| 9 | Minh chứng sử dụng AI trong phân tích và thiết kế: lưu prompt, phân tích AI, nhận xét cách sinh/chỉnh sửa kiến thức quản trị AI | Đã có | Cùng tài liệu, mục 7 — ba nguồn kiến thức và quy trình cập nhật đã làm |
| 10 | Tài liệu phân tích thiết kế rõ ràng, có cấu trúc, kèm kế hoạch giai đoạn tiếp theo | Đã có | Cùng tài liệu, mục 8 + [ROADMAP.md](ROADMAP.md) |

**Nhận xét phần 1:** đây là phần yếu nhất của hồ sơ trước đây — repo có kiến trúc và
ERD nhưng **không có** tài liệu phân tích yêu cầu, không có sơ đồ use case, không
có đặc tả prompt. Cả ba vừa được bổ sung trong `REQUIREMENTS_AND_DESIGN.md`.

---

## Phần 2 — Bài kiểm tra thường xuyên 2 (chất lượng sản phẩm)

| # | Tiêu chí | Trạng thái | Bằng chứng |
|---|---|---|---|
| 1 | Dự án rõ ràng frontend/backend/database/config/docs, framework & ngôn ngữ | Đã có | Cây thư mục ở [README.md](../README.md); React 18 + Vite, FastAPI, SQLAlchemy, Cloudflare Workers |
| 2 | Đăng nhập, phân quyền: user, roles, phân quyền theo vai trò | Đã có + test | 5 vai trò có `CheckConstraint`; `test_v3_security_and_state_machine.py`, `test_multi_tenant_hardening.py` |
| 3 | CRUD nghiệp vụ | Đã có + test | Chiến dịch, task, nội dung, metrics, brand kit, workspace; `test_offline_core_works_without_ai.py` |
| 4 | Tìm kiếm, lọc, sắp xếp, **phân trang** | **Một phần** | Tìm/lọc/sắp xếp có (`search`, `status`, `priority`, `assignee_id`, `order_by`). **Phân trang mới chỉ có ở `/notifications` và `/ai/logs`**; `/campaigns`, `/contents`, `/tasks` trả toàn bộ danh sách |
| 5 | Báo cáo và dashboard phục vụ nghiệp vụ | Đã có + test | Dashboard, Command Center, KPI, attribution; `test_offline_core_works_without_ai.py` |
| 6 | Giao diện rõ ràng, dễ sử dụng: đánh dấu, điều hướng, thông báo lỗi, phản hồi người dùng | Đã có | 7 màn hình trong thanh điều hướng (Bảng điều khiển, Quản lý chiến dịch, Tác vụ của tôi, Xưởng sáng tạo AI, Hàng đợi phê duyệt, Lịch xuất bản, Cài đặt & Brand Kit) cộng trang đăng nhập/đăng ký; `ToastProvider` báo lỗi; focus trap cho modal; kiểm thử WCAG trong CI (Gate 4) |
| 7 | Kiểm tra CSDL: lưu, đọc, cập nhật, xoá; độ liên mẫu dữ liệu | Đã có + test | 19 bảng; `test_database_safety.py` |
| 8 | Xử lý core bản: kiểm tra input, kiểm tra logic, phân quyền, không để ứng dụng crash | Đã có + test | Validate bằng Pydantic; try/except ở tầng AI; `test_adversarial_v3.py`, `test_ai_failure_does_not_leak_any_content_shape` |
| 9 | Minh chứng sử dụng AI: prompt, phân tích AI, phần việc được hỗ trợ và cách tra chứng minh | Đã có + test | `prompts.json` (4 tác vụ × 3 phiên bản), `ai_logs`, `test_prompt_variant_harness.py`, [PROMPT_VARIANT_COMPARISON.md](PROMPT_VARIANT_COMPARISON.md) |
| 10 | Quản lý mã nguồn & tài liệu chạy thử: README, hướng dẫn cài/chạy, `.env.example`, commit rõ ràng | Đã có | README có 3 cách chạy, `.env.example` đầy đủ, commit theo nhóm tính năng |

---

## Phần 3 — Bài kiểm tra thường xuyên 3 (chất lượng AI)

| # | Tiêu chí | Trạng thái | Bằng chứng |
|---|---|---|---|
| 1 | Tích hợp AI cho **nhiều** chức năng | Đã có + test | 4 nhóm: ý tưởng, bản nháp, đa kênh, tóm tắt; xem [REQUIREMENTS_AND_DESIGN.md](REQUIREMENTS_AND_DESIGN.md) mục 5 |
| 2 | Kết nối **đa dạng**: OpenAI / Gemini / Claude / HuggingFace / Ollama | Đã có + test | Registry tại `providers.py` hỗ trợ đủ 5 loại (thêm OpenRouter, OpenCode); `test_ai_provider_expansion.py` — test mock, không gọi mạng |
| 3 | Thiết kế prompt tách khỏi code | Đã có + test | `backend/prompts/prompts.json` + `prompt_engine.py`; đổi prompt không sửa Python |
| 4 | Tối ưu prompt có **thử nghiệm**, so sánh ít nhất 3 phiên bản | Đã có + đo được | `scripts/compare_prompt_variants.py`; v1 0% schema hợp lệ → v2 75% → v3 100%; `test_prompt_variant_harness.py` (12 test) |
| 5 | Dữ liệu hỗ trợ AI từ CSDL / file / báo cáo, có kiểm soát truy cấp | Đã có + test | AI đọc chiến dịch, sản phẩm, kênh, brand kit, metrics; ghi `source_ids_json` vào `ai_logs`; truy cập qua `check_campaign_access_for_ai` |
| 6 | Hiển thị kết quả AI rõ ràng, dễ đánh giá, có cảnh báo khi cần | Đã có + test | Bảng cảnh báo hổ phách khi fallback, `is_fallback`, `model_provider`, `warnings` từ model; `test_fallback_templates_are_never_labelled_as_ai_output` |
| 7 | Xử lý tình huống: timeout, rate limit, response rỗng/sai định dạng, quá thời gian, đủ liệu quá đài | Đã có + test | `AI_TIMEOUT_SECONDS`, retry có backoff, `RATE_LIMIT`/`TIMEOUT`/`SCHEMA_ERROR` trong `ai_logs`; phản hồi lỗi không chứa trường nội dung |
| 8 | Kiểm thử chức năng quan trọng và chức năng AI: test case, manual test, script test | Đã có + đo được | 1371 test backend; Playwright; script so sánh prompt chạy trong CI |
| 9 | Review code và cải thiện chất lượng AI | Đã có | Sửa `compliance_score` mặc định 100 → đo thật; thêm adapter Anthropic thật; sửa rò khoá trong log |
| 10 | Trải nghiệm người dùng AI: linh hoạt, dễ hiểu, không gây nhầm lẫn | Đã có | Nhãn dự phòng rõ ràng; chạy được hoàn toàn không có AI; nhưng xem giới hạn ở [AI_ETHICS_AND_HUMAN_OVERSIGHT.md](AI_ETHICS_AND_HUMAN_OVERSIGHT.md) mục 8 |

---

## Phần 4 — Thiết kế học phần

| # | Tiêu chí | Trạng thái | Bằng chứng |
|---|---|---|---|
| 1 | Hoàn thiện chức năng hệ thống: chức năng quản lý và chức năng AI hoạt động đầy đủ | Đã có + test | FR-1…FR-13; `test_offline_core_works_without_ai.py` chứng minh mọi luồng cốt lõi chạy được không cần AI |
| 2 | Kiến trúc rõ ràng, mô tả người dùng, code rõ, module hóa, dễ bảo trì | Đã có | Tầng `api / services / models / schemas`; [ARCHITECTURE.md](ARCHITECTURE.md) mục 1 |
| 3 | Chất lượng CSDL hợp lý: kiểm soát dữ liệu, đúng nhất quán, ràng buộc, đúng mẫu và khả năng sao lưu/khôi phục | Đã có + test | 19 bảng, FK + `CheckConstraint` + index; `test_database_safety.py`. **Sao lưu:** dữ liệu ở Postgres bên ngoài Render; quy trình backup/restore **chưa diễn tập** |
| 4 | Chất lượng giao diện và trải nghiệm: rõ, nhất quán, responsive | Đã có + test | Tailwind, component dùng chung; Playwright kiểm tra responsive; axe trong CI |
| 5 | Chất lượng chức năng AI: hữu ích, đúng ngôn ngữ, có kiểm soát sai lệch, giới hạn | Đã có, giới hạn đã ghi | Prompt v3 100% đúng đặc tả; **chưa có** kiểm thử công khai về thiên lệch; chưa đo chất lượng văn phong bằng mô hình thật |
| 6 | Bảo mật, quyền riêng tư và dữ liệu: khoá, phân quyền, không lộ API key | Đã có + test | Fernet, che khoá, lọc log, RBAC + ranh giới workspace; `test_crypto_vault.py`, `test_wave5_credential_sanitization.py` |
| 7 | Hiệu năng: đáp ứng dữ liệu demo, cơ chế chống lỗi, có giao diện lỗi | Đã có, chưa đo tải | Validate + fallback + thông báo lỗi rõ. **Chưa có** kết quả kiểm thử tải đồng thời; xem ROADMAP |
| 8 | Triển khai và đóng gói: hướng dẫn triển khai, cấu hình môi trường, dữ liệu mẫu, khuyến nghị Docker | Đã có | `render.yaml`, `cloudflare/wrangler.jsonc`, `docker-compose.yml`, `backend/Dockerfile`, `seed_data.py` |
| 9 | Báo cáo mô tả phân tích, thiết kế, triển khai, kiểm thử, chức năng AI và AI trong SDLC | Đã có | Tài liệu này + 5 tài liệu trong `docs/` + V8/V9 giữ làm hồ sơ lịch sử |
| 10 | Thuyết trình và demo: demo mạch lạc, trình bày rõ chức năng quản lý, chức năng AI, minh chứng AI và trả lời câu hỏi | Chuẩn bị | Kịch bản demo: mở app → tạo chiến dịch → soạn nội dung **tay** → soạn nội dung **bằng AI** → thấy cảnh báo → gửi duyệt → duyệt → lên lịch → xem dashboard. Nhấn mạnh lần bật/tắt AI cho cùng một kịch bản |

---

## Các phát hiện đáng chú ý khi đối chiếu

### 1. Tiêu chí bị bỏ sót nhiều nhất là "phân trang"

Rubric yêu cầu rõ "tìm kiếm, lọc, sắp xếp, phân trang" (Bài 2 mục 4). Hệ thống có
tìm/lọc/sắp xếp nhưng **thiếu phân trang** ở ba danh sách chính. Đây là thiếu sót
thật, đã ghi vào ROADMAP, không nên giấu.

### 2. Test cũ từng mâu thuẫn rubric

Có test cũ khẳng định các provider Claude/OpenAI/Llama bị "cấm". Rubric yêu cầu đúng
ngược lại. Test đã được sửa theo rubric — và đó là minh chứng cho tiêu chí 3.9
(review code: đôi khi test sai, không phải code sai).

### 3. Điểm tuân thủ 100/100 từng là bằng chứng giả

`compliance_score` mặc định là 100 mà không ai gán. Đây là trường hợp AI **không**
liên quan, nhưng vẫn là dữ liệu bịa — đã sửa thành kết quả quét thật hoặc `None`.

### 4. Ba tài liệu cũ mô tả kiến trúc đã bị bỏ

Kiến trúc "FastAPI trong Cloudflare Containers + Durable Object + snapshot SQLite lên
R2" không còn tồn tại (tài khoản không có Workers Paid plan). Đã sửa ở
[ARCHITECTURE.md](ARCHITECTURE.md), [ROADMAP.md](ROADMAP.md),
[cloudflare/README.md](../cloudflare/README.md) và [README.md](../README.md).

### 5. Ba mốc đo được để trình bày

| Số liệu | Giá trị | Nguồn |
|---|---|---|
| Schema hợp lệ của prompt | v1 0% → v2 75% → v3 100% | `scripts/prompt_variant_results.json` |
| Test backend | 1371 pass | `pytest` trên `main` |
| Chi phí prompt khi tăng chất lượng | ×7,6 (249 → 1900 ký tự) | [PROMPT_VARIANT_COMPARISON.md](PROMPT_VARIANT_COMPARISON.md) |

---

## Những gì không nên nói khi bảo vệ

| Đừng nói | Nói thay |
|---|---|
| "Hệ thống AI không bao giờ tạo nội dung sai" | "Có validate schema và bộ quét từ khoá; con người duyệt trước khi xuất bản" |
| "Tuân thủ GDPR" | "Khoá được mã hoá và che; chưa có audit bên thứ ba" |
| "Đã tối ưu prompt tốt nhất" | "Đo được v3 đáp ứng 100% đặc tả trên bộ case cố định; chưa đo chất lượng văn phong" |
| "Đã đăng bài lên Facebook/TikTok" | "`PUBLISHED` là trạng thái nội bộ; chưa có connector gửi thật" |
| "Chạy trên Cloudflare" | "Frontend static trên Cloudflare Worker, backend FastAPI trên Render" |
| "Có phân trang đầy đủ" | "Tìm/lọc/sắp xếp có; phân trang mới ở notifications và log AI" |
