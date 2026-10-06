# Đạo đức AI & Giám sát của con người (Tuần 3 mục 5–6; Thiết kế mục 5–6)

**Phạm vi.** Tài liệu này gom những cơ chế **đã có trong mã nguồn** thành một lập
luận có thể trình bày khi bảo vệ. Mỗi mục đều dẫn tới file và — nếu có — test
tương ứng.

> **Nguyên tắc trình bày.** Mục tiêu của tài liệu là cho biết **cơ chế nào tồn
> tại và được kiểm chứng tới đâu**, không phải để tuyên bố hệ thống "an toàn" hay
> "đạt đạo đức". Ở mục 8 liệt kê những gì **không** có cơ sở để khẳng định.
> Khi bảo vệ, phần thiếu phải nói trước phần có, không phải sau.

---

## 1. Con người duyệt là bắt buộc, không phải tuỳ chọn

Đây là cơ chế nền. Mọi nội dung — kể cả nội dung do AI sinh — đều phải đi qua
tài khoản có quyền trước khi tới được xuất bản.

| Điều kiện | Cơ chế | Mã nguồn | Test |
|---|---|---|---|
| Không tạo được bài ở trạng thái `APPROVED`/`PUBLISHED` | Chặn ở `POST /contents` | `app/api/v1/contents.py` | `test_adversarial_v3.py` (2 ca) |
| Không nâng cấp trạng thái trực tiếp qua `PUT /contents/{id}` | Chặn 400 | `app/api/v1/contents.py` | `test_adversarial_v3.py` (2 ca) |
| Sửa bài đã duyệt sẽ hạ về `AI_DRAFT` và phải duyệt lại | Anti-tampering | `app/api/v1/contents.py` | `test_adv_anti_tampering_approved_content_reverts_to_ai_draft` |
| Chỉ lên lịch được bài đã `APPROVED` | Điều kiện tiên quyết ở `POST /contents/{id}/schedule` | `app/api/v1/schedules.py` | `test_schedules_lifecycle.py` |
| AI không thể tự duyệt bài của chính nó | Không có đường code nào cho phép | Kiểm chứng: `ai_service` không import `contents.py` | `test_offline_core_works_without_ai.py::test_no_business_router_depends_on_the_ai_layer` |

**Cách trình bày khi bảo vệ.** Điểm mạnh không nằm ở việc "có hàng đợi duyệt" —
nhiều hệ thống có. Điểm mạnh nằm ở chỗ **đường duyệt là bắt buộc ở tầng API**,
nên không có cách nào lách qua từ giao diện. Test cuối cùng trong bảng là bằng
chứng cấu trúc cho điều đó: tầng AI không có đường tới tầng nghiệp vụ.

---

## 2. Hệ thống nói rõ khi nội dung KHÔNG do AI viết

Trước đây giao diện hiện thẳng "Gemini 2.5 Flash" và toast báo thành công bất kể
backend có gọi được nhà cung cấp hay không. Người dùng tưởng đang xem nội dung
do AI viết trong khi thực ra là khuôn mẫu dự phòng.

| Cơ chế | Chi tiết | Mã nguồn | Test |
|---|---|---|---|
| Mọi phản hồi AI mang cờ `is_fallback` | `False` = mô hình thật, `True` = template | `app/services/ai/ai_service.py` | `test_v3_security_and_state_machine.py` |
| `model_provider` nói đúng nguồn | ví dụ `ollama-system`, `anthropic-workspace` | `ai_service.py` | `test_ai_provider_expansion.py` |
| Bảng cảnh báo hổ phách trong AI Studio | Nhãn "Nội dung dự phòng (không phải do AI viết)" | `frontend/src/pages/AIStudio.tsx` | Playwright `works-without-ai.spec.ts` |
| Vị trí nhận biết khi fallback | `role="alert"` + `role="status"` tùy tình huống | `AIStudio.tsx` | Kiểm thử WCAG Gate 4 |

Mọi template dự phòng đều phải kèm `warnings` giải thích lý do, và nhãn nguồn
phải là `template-fallback-engine` chứ không phải tên model:

```python
assert out.get("is_fallback") is True
assert out.get("model_provider") == "template-fallback-engine"
assert out.get("warnings")
```

Nguồn: `test_offline_core_works_without_ai.py::test_fallback_templates_are_never_labelled_as_ai_output`

---

## 3. AI không được tự chấm điểm cho mình

Đây là cơ chế bị sửa trong đợt làm hiện tại, và là ví dụ rõ nhất về việc hệ thống
đã từng đưa ra một nhận định không có cơ sở.

**Trước.** `OmnichannelResponse.compliance_score` mặc định là `100`, và không mã
nào từng gán lại nó. Kết quả: **mọi** phản hồi — kể cả template dự phòng — đều báo
"100/100 đạt chuẩn", dù không có bộ quét nào chạy. Người dùng đọc điểm tuyệt đối
đó là bằng chứng nội dung đã được kiểm duyệt tự động, rồi dựa vào nó để quyết
định có duyệt bài hay không.

**Sau.** Điểm đến từ `_score_omnichannel_compliance()`, gọi `ComplianceScanner.scan`
— cùng bộ quét với `POST /contents/compliance-check`, đối chiếu từ khóa cấm của
Brand Kit. Quét cả ba kênh và lấy điểm thấp nhất: một email sạch không bù được
cho một bài Facebook vi phạm. Không có Brand Kit hoặc không có nội dung để quét
thì trả `None` để UI hiện "chưa chấm", thay vì bịa điểm.

| Điều | Trước | Sau | Mã nguồn | Test |
|---|---|---|---|---|
| `compliance_score` | `int = 100`, không ai gán | `Optional[int]`, đo thật | `app/schemas/schemas.py`, `app/api/v1/ai.py` | `test_offline_core_works_without_ai.py::test_fallback_omnichannel_does_not_claim_a_perfect_compliance_score` |

**Điểm bảo vệ được:** con số 100 vẫn có thể xuất hiện, nhưng giờ nó là **kết quả quét**
chứ không phải giá trị mặc định. Đó là khác biệt giữa "100/100" và "chưa chấm".

---

## 4. An toàn thương hiệu: kiểm tra trước khi gửi duyệt

| Cơ chế | Chi tiết | Mã nguồn | Test |
|---|---|---|---|
| Quét từ khóa cấm của Brand Kit | Từng workspace một blacklist | `app/services/compliance/compliance_service.py` | `test_brand_kit.py`, `test_compliance_guardrail.py` |
| Quét chính sách quảng cáo | ~38 quy tắc `AD_POLICY` (cam kết quá mức, chữ ký, từ ngữ y tế/tài chính…) | `compliance_service.py` | `test_compliance_guardrail.py` |
| Không dấu, không phân biệt hoa thường | So khớp cả chuỗi gốc lẫn chuỗi đã bỏ dấu | `strip_accents()` | `test_compliance_guardrail.py` |
| Chặn gửi duyệt khi vi phạm mức HIGH | `can_submit` | `app/api/v1/contents.py` | `test_strict_submit_gate_blocks_high_severity` |
| Nút gửi duyệt bị khoá trên UI | Cùng hàng rào | `AIDrawer.tsx`, `WorkflowCanvas.tsx` | Playwright |

**Điểm quan trọng:** bộ quét này là **quy tắc tất định**, không gọi mô hình. Nó
chạy được khi AI tắt hoàn toàn — đó là lý do trình bày "an toàn thương hiệu" không
phụ thuộc vào việc có AI hay không.

---

## 5. Số liệu thật, không phải số bịa

| Cơ chế | Chi tiết | Mã nguồn | Test |
|---|---|---|---|
| Gắn nguồn từng dòng metrics | `NULL` = dữ liệu thật, `'seed'` = dữ liệu mẫu | `app/models/entities.py` | `test_database_safety.py` |
| Báo cáo dòng không rõ nguồn, không đếm như thật | `has_unverified_data` tách riêng `source IS NULL` | `app/api/v1/metrics.py` | `test_wave5_credential_sanitization.py` |
| Cảnh báo dữ liệu mẫu trên dashboard | "Số liệu dưới đây chứa dữ liệu MẪU, không phải số đo thật" | `frontend/src/pages/Dashboard.tsx` | Playwright golden-journey |
| AI Doctor cảnh báo khi dữ liệu thưa | `is_sparse_data` → UI hiện chế độ demo | `ai_doctor.py`, `AIDoctorWidget.tsx` | `test_attribution_ai_doctor.py` |
| AI Doctor không suy luận nhân quả khi thiếu số liệu | Chỉ chấm điểm theo ngưỡng trên metrics đã lưu | `app/services/ai/ai_doctor.py` | `test_attribution_ai_doctor.py` |

**Cách trình bày khi bảo vệ.** Điểm mạnh là hệ thống **phân biệt được dữ liệu thật
và dữ liệu mẫu**, và nói cho người dùng biết đang nhìn cái nào. Đây là điều ít
hệ thống bài tập làm được: hầu hết hoặc đổ tất cả là số thật, hoặc vứt bỏ số mẫu
khỏi giao diện.

---

## 6. Khi AI hỏng, hệ thống báo lỗi chứ không bịa nội dung

Ba nhánh lỗi được phân biệt rõ, mỗi nhánh có một nhãn khác nhau:

| Tình huống | Hành vi | Mã nguồn |
|---|---|---|
| Không có khoá, fallback **tắt** | `HTTP 502` — báo lỗi, không trả nội dung | `app/api/v1/ai.py` |
| Không có khoá, fallback **bật** | Trả template kèm `is_fallback=true` | `ai_service.py` |
| Provider lỗi/timeout/schema sai | `ai_logs` ghi `TIMEOUT` / `PROVIDER_ERROR` / `SCHEMA_ERROR` | `ai_service.py` |

Phản hồi lỗi không được chứa bất kỳ trường nội dung nào:

```python
for leaked_field in ('"facebook"', '"tiktok"', '"email"', '"hook_3s"', '"ideas"', '"title"'):
    assert leaked_field not in text
```

Nguồn: `test_offline_core_works_without_ai.py::test_ai_failure_does_not_leak_any_content_shape`

---

## 7. Riêng tư dữ liệu: khoá AI được mã hoá, không rò ra log

| Cơ chế | Chi tiết | Mã nguồn | Test |
|---|---|---|---|
| Mã hoá khoá BYOK | Fernet, lưu trong CSDL dạng mã hoá | `app/core/crypto.py` | `test_crypto_vault.py` |
| Chỉ trả về khoá đã che | `masked_key`, không bao giờ trả bản rõ | `app/api/v1/settings.py` | `test_settings_byok.py` |
| Chặn ciphertext không chuẩn trước khi giải mã | Chống tấn công chuỗi đệm | `app/core/crypto.py` | `test_p0_security_regressions.py` |
| Lọc API key khỏi log và message lỗi | `_sanitize_ai_error()` — xoá `?key=`, `AIza…`, `Bearer …` | `ai_service.py`, `settings.py` | `test_wave5_credential_sanitization.py` |
| Khoá chỉ cho Manager/Agency Manager/Admin đặt | Marketer nhận 403 | `app/api/v1/settings.py` | `test_settings_byok.py` |
| Ranh giới workspace + bản ghi | `check_campaign_access` cho Content/Metrics/AI | `app/api/v1/*.py` | `test_adversarial_v3.py`, `test_multi_tenant_hardening.py` |
| Tài khoản bị vô hiệu hoá mất token ngay | `RoleChecker` đọc trạng thái trong CSDL, không chỉ dựa vào JWT | `app/core/security.py` | `test_v3_security_and_state_machine.py` |

Về quyền riêng tư, nói thẳng trong phần giới hạn: hệ thống **không** có cơ chế
ẩn danh, không đo lường hành vi người dùng, không tuân thủ GDPR một cách đầy
đủ. Nó chỉ giữ dữ liệu trong một hệ thống mà người vận hành kiểm soát. Không nói
thêm.

---

## 8. Những gì KHÔNG có cơ sở để khẳng định

Phần này tồn tại để tránh bị hỏi về những thứ chưa kiểm chứng được.

| Không thể khẳng định | Vì sao |
|---|---|
| "AI không bao giờ tạo nội dung sai" | Schema hợp lệ ≠ nội dung đúng. Benchmark chỉ chạy trên tập case cố định. |
| "Điểm tuân thủ chính xác 100%" | Điểm đo bằng bộ quy tắc từ khoá. Nó bỏ sót vi phạm mà bộ quy tắc chưa mô hình hoá. |
| "Tuân thủ GDPR / chuẩn đạo đức AI" | Không có audit bên thứ ba, không DPA, không đăng ký. |
| "Không thiên lệch" | Không có kiểm thử công khai về thiên lệch đầu ra. |
| "Người dùng tin tưởng đầu ra AI" | Chưa có nghiên cứu người dùng nào trong phạm vi này. |
| "So sánh chất lượng prompt v1/v2/v3 với mô hình thật" | Harness dùng stub tất định. Xem [PROMPT_VARIANT_COMPARISON.md](PROMPT_VARIANT_COMPARISON.md) mục 1. |

---

## 9. Trung thực về giới hạn AI

Ngoài các bảng trên, hai giới hạn đã được ghi trong mã nguồn:

1. **`PUBLISHED` không có nghĩa đã đăng thật.** Scheduler và endpoint publish chỉ
   cập nhật trạng thái nội bộ. Chưa có connector gửi tới Facebook/TikTok/email.
2. **Benchmark không đại diện production.** Số liệu trong
   [AI_EVALUATION_REPORT.md](AI_EVALUATION_REPORT.md) đo trên SQLite cô lập và tập
   case cố định, không phải latency LLM qua mạng.

---

## 10. Bảng tra cứu nhanh khi bảo vệ

| Câu hỏi giảng viên có thể hỏi | Trả lời bằng | File |
|---|---|---|
| "AI có tự duyệt bài được không?" | Không có đường code từ tầng AI sang tầng nghiệp vụ | `test_offline_core_works_without_ai.py` |
| "Người dùng có biết nội dung do AI viết không?" | `is_fallback` + bảng cảnh báo | `AIStudio.tsx` |
| "Số liệu trên dashboard có thật không?" | Có trường `source` và cảnh báo dữ liệu mẫu | `metrics.py`, `Dashboard.tsx` |
| "Nếu AI hỏng thì sao?" | 502 khi tắt fallback; template có nhãn khi bật | `test_offline_core_works_without_ai.py` |
| "Khoá API của tôi có an toàn không?" | Fernet + che khoá + lọc log | `crypto.py`, `test_crypto_vault.py` |
| "Người không dùng AI có làm được việc không?" | Có — có bộ soạn thảo thủ công, test chứng minh | `ManualContentComposer.tsx`, `works-without-ai.spec.ts` |
| "Prompt nào tốt hơn?" | Có bảng đo, nhưng chỉ về đặc tả chứ không phải văn phong | `PROMPT_VARIANT_COMPARISON.md` |