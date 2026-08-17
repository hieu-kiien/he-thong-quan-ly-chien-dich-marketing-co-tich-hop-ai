---
document_id: BAI03-DOC-04
document_type: ai-specification
project_id: BAI03-SALES-AI
status: PROPOSED
authority: safety-and-integration-design
implementation_status: NOT_IMPLEMENTED
last_reviewed: 2026-08-17
---

# Đặc tả chức năng AI có kiểm soát

Ba chức năng dưới đây là phạm vi yêu cầu. Tại thời điểm rà soát, chưa thấy
provider/client/endpoint AI chạy trong các nhánh Django; tài liệu này là thiết
kế đề xuất để triển khai và kiểm thử, không phải bằng chứng hiện trạng.

## 1. Nguyên tắc chung

1. Server lọc quyền, dữ liệu và PII trước khi gọi model.
2. Quy tắc nghiệp vụ và số liệu do code/database quyết định; AI chỉ giải thích,
   gợi ý hoặc chuyển câu hỏi thành intent đọc dữ liệu.
3. AI không được ghi database, thay đổi tồn, đặt hàng, phê duyệt hoàn tiền hoặc
   thay thế quyết định của người dùng (`BR-007`, `BR-008`).
4. Mọi response phải qua schema validation, giới hạn độ dài và kiểm tra đối
   chiếu với dữ liệu đầu vào.
5. Có timeout, retry hữu hạn, fallback và trạng thái `HUMAN_REVIEW`; không để
   lỗi provider làm hỏng luồng bán hàng chính.
6. Không gửi số điện thoại đầy đủ, dữ liệu thanh toán, mật khẩu, API key hoặc
   PII không cần thiết (`BR-006`, `NFR-025`).

## 2. AI-001 — Tư vấn sản phẩm

| Thuộc tính | Đặc tả |
|---|---|
| Actor | `Staff` hoặc người dùng được cấp quyền |
| Input | Nhu cầu tự nhiên, ngân sách, loại sản phẩm, tiêu chí tùy chọn |
| Context | Danh sách sản phẩm đã lọc; tối thiểu `id`, tên, nhóm, giá, tồn, thuộc tính mô tả |
| Tiền xử lý bắt buộc | Server lọc `stock_qty > 0`, trạng thái đang bán, giá hợp lệ; không để LLM quyết định điều kiện này |
| Output | Tối đa 3 sản phẩm, lý do ngắn, cảnh báo thiếu dữ liệu và mã nguồn sản phẩm |
| Fallback | Trả danh sách lọc theo rule nếu AI timeout/sai schema |
| Bằng chứng | Danh sách ID/giá/tồn dùng để đối chiếu |

Schema output tối thiểu:

```json
{
  "recommendations": [
    {
      "product_id": "string",
      "reason": "string",
      "matched_constraints": ["string"]
    }
  ],
  "missing_information": ["string"],
  "disclaimer": "Kết quả tham khảo dựa trên dữ liệu hiện có."
}
```

Không được trả về SKU/giá/tồn không xuất hiện trong context. `product_id` phải
được server kiểm tra lại trước khi hiển thị.

## 3. AI-002 — Nhận xét doanh thu

| Thuộc tính | Đặc tả |
|---|---|
| Actor | `Owner`/người dùng được cấp quyền báo cáo |
| Input | Khoảng thời gian, bộ lọc, các số liệu deterministic |
| Context | Doanh thu, số hóa đơn, top sản phẩm, tồn thấp, dữ liệu so sánh nếu có |
| Output | 3–5 nhận xét, nguyên nhân được gắn với số liệu, khuyến nghị nhập hàng |
| Ràng buộc | Không tự sửa số; nêu rõ thiếu dữ liệu; khuyến nghị chỉ để tham khảo |
| Fallback | Hiển thị báo cáo số liệu không có AI |
| Human review | Người dùng quyết định nhập hàng hoặc hành động kinh doanh |

Đầu vào nên là object có số liệu và metadata, không phải toàn bộ bảng khách
hàng. Cần hiển thị khoảng thời gian, thời điểm tạo, query/filter và các metric
nguồn cạnh phần nhận xét AI.

## 4. AI-003 — Hỏi đáp dữ liệu bán hàng

| Thuộc tính | Đặc tả |
|---|---|
| Actor | `Owner` hoặc vai trò được cấp quyền |
| Input | Câu hỏi tiếng Việt tự nhiên |
| Bước 1 | Phân loại intent vào allowlist: doanh thu, hóa đơn, top sản phẩm, tồn thấp, so sánh kỳ |
| Bước 2 | Server tạo query/selector có cấu trúc và kiểm tra quyền |
| Bước 3 | Lấy dữ liệu read-only; chỉ gửi aggregate tối thiểu cho model |
| Output | Câu trả lời, kỳ dữ liệu, nguồn metric, nếu không đủ dữ liệu thì nói rõ |
| Không cho phép | SQL tùy ý có quyền ghi, truy vấn bảng ngoài allowlist, xem PII trái quyền |
| Fallback | Hiển thị bộ lọc hoặc báo cáo tương ứng để người dùng tra cứu thủ công |

Tài liệu BA có nhắc tới `Text-to-SQL`; đây là hướng đề xuất cần đánh giá, không
được triển khai raw SQL trực tiếp từ output LLM. Phương án an toàn hơn là
intent-to-structured-query hoặc query builder chỉ đọc.

## 5. Prompt contract

Mỗi use case nên có version và ba phần:

```text
system_prompt: vai trò, phạm vi, quy tắc không bịa, schema output, không ghi DB
developer_context: dữ liệu đã lọc, kỳ báo cáo, quyền và mã nguồn tham chiếu
user_prompt: yêu cầu đã chuẩn hóa, không cho phép ghi đè system rules
```

Prompt phải giữ trong module/config riêng, có test injection và không ghép chuỗi
raw từ người dùng vào câu lệnh SQL hoặc lời nhắc hệ thống.

## 6. Xử lý lỗi và log

| Trường hợp | Hành vi |
|---|---|
| Provider timeout | Dừng theo timeout, log `ERROR` hoặc `FALLBACK`, hiển thị kết quả rule |
| Rate limit | Retry có backoff hữu hạn; không retry vô hạn |
| Response rỗng/sai JSON | Validate thất bại → fallback/human review |
| Dữ liệu quá dài | Summarize/aggregate ở server hoặc từ chối rõ ràng |
| Prompt injection | Giữ system policy, từ chối yêu cầu ngoài phạm vi, log sự kiện an toàn |
| Không đủ quyền | Từ chối trước khi tạo context |
| Dữ liệu thiếu | Trả lời “không đủ dữ liệu”, không suy đoán |

`AIEventLog` ở `sales_management/apps/accounts/models.py` có các trạng thái
`success`, `fallback`, `error`, `human_review`. Khi triển khai, log phải tránh
prompt/response chứa PII; lưu hash, summary hoặc metadata đã redact khi cần.

## 7. Đánh giá tối thiểu

| Nhóm đánh giá | Chỉ số/điều kiện | Mức mục tiêu từ yêu cầu |
|---|---|---|
| Grounding | Không có sản phẩm ngoài context; giá/tồn khớp DB | 100% test không hallucination |
| Availability | Gợi ý không hết hàng | 100% test rule |
| Usefulness | Gợi ý phù hợp nhu cầu do người đánh giá chấm | Mục tiêu BA: ≥70%, cần định nghĩa tập test |
| Latency | Thời gian end-to-end | Mục tiêu 15s; timeout 30s |
| Privacy | Không có PII không cần thiết trong payload/log | 0 trường hợp vi phạm |
| Safety | Không ghi DB hoặc tự đặt hàng | 0 thao tác ngoài quyền |
| Robustness | Timeout, rate limit, input dài, injection, schema sai | Có test cho từng nhánh |

Các mức phần trăm/thời gian là acceptance target, chưa phải số đo đã đạt.
