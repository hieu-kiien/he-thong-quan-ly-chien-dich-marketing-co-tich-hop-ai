---
document_id: BAI03-SUBMISSION-APP-A
document_type: evidence-appendix
project_id: BAI03-SALES-AI
project_title: Hệ thống quản lý bán hàng có tích hợp AI
priority: P1
status: DERIVED
last_reviewed: 2026-08-18
source_of_truth: false
---

# Phụ lục A — Minh chứng sử dụng AI và kiểm chứng

Phụ lục này phân biệt bằng chứng nguồn, artifact cục bộ, template prompt và phản hồi provider. Nhóm không chèn câu trả lời LLM giả lập vào bài. Các JSON/Markdown trong mục 8 của báo cáo là hợp đồng thiết kế minh họa, không phải API response đã thu được.

## A.1. Nhật ký kiểm tra có thể tái lập

| EV | Lệnh/nguồn | Kết quả quan sát | Mức kết luận |
|---|---|---|---|
| `EV-CHK-001` | Thư mục làm việc `sales_management`; lệnh ` .\.venv-rag\Scripts\python.exe manage.py check` | `System check identified no issues (0 silenced).` | `PASS` cho system check tại thời điểm kiểm tra. |
| `EV-CHK-002` | Lệnh ` .\.venv-rag\Scripts\python.exe manage.py test apps.knowledge --verbosity 1` | Stdout ghi `Ran 7 tests in 0.020s` và `OK`; test runner không trả prompt ổn định trong thời gian quan sát do môi trường cleanup, nên tiến trình được dừng sau khi đã thu stdout. | `PARTIAL`: kết quả test hiển thị OK, nhưng không gọi là bằng chứng end-to-end hoặc exit code sạch. |
| `EV-CHK-003` | `node .gitnexus/run.cjs analyze` và `status` tại commit `46cb278` | Analyzer ghi `1,261 nodes | 1,419 edges | 13 clusters | 11 flows`; status ghi current/indexed commit trùng nhau và `up-to-date`. | `PASS` cho trạng thái index; không suy ra nghiệp vụ đã chạy. |

**Raw stdout rút gọn của system check/test:**

```text
System check identified no issues (0 silenced).
.......
----------------------------------------------------------------------
Ran 7 tests in 0.020s

OK
Found 7 test(s).
System check identified no issues (0 silenced).
```

**Ghi chú trung thực:** hiện trường kiểm tra cho thấy 7 test knowledge in ra `OK`, nhưng tiến trình Django không kết thúc sạch trong cửa sổ quan sát. Vì vậy nhóm dùng kết quả này để chứng minh lớp helper/endpoint retrieval đã có kiểm tra, không dùng nó để tuyên bố toàn hệ thống hoặc AI provider đã đạt.

## A.2. Bảng evidence theo nguồn

| EV | Bằng chứng | Trạng thái | Kết luận được phép |
|---|---|---|---|
| `EV-001` | `sales_management/apps/knowledge/services.py` và `management/commands/index_knowledge.py` | `IMPLEMENTED — retrieval/context` | Có chunk, metadata, embedding, tìm kiếm và citation; chưa có LLM answer. |
| `EV-002` | `sales_management/apps/knowledge/tests.py` và raw stdout ở A.1 | `PARTIAL/PASS có điều kiện` | 7 test helper/endpoint in `OK`; chưa là kiểm thử nghiệp vụ end-to-end. |
| `EV-003` | Chroma collection `bai03_knowledge`, artifact local được tạo từ corpus | `LOCAL ARTIFACT` | Có thể dùng làm context; không đưa `knowledge_store/` vào ZIP và không coi là DB giao dịch. |
| `EV-004` | `prompts/07-RAG/01-RAG-Chatbot-tu-van-san-pham.md`, `02-RAG-Hoi-dap-tai-lieu-du-an.md` | `REFERENCE/TEMPLATE` | Có prompt grounding/citation; không có response provider kèm theo. |
| `EV-005` | Prompt test/security tại `prompts/10-*`, `prompts/14-*`, `prompts/15-*` | `REFERENCE/TEMPLATE` | Có ý tưởng test injection, hết hàng, PII, fallback; chưa có runtime log. |
| `EV-006` | `embeding.ipynb` với embedding minh họa | `IMPLEMENTED — experiment` | Chứng minh thí nghiệm vector; không chứng minh đã trả lời câu hỏi bán hàng. |
| `EV-007` | `sales_management/apps/accounts/models.py` — `AIEventLog` | `IMPLEMENTED — schema` | Có nơi lưu metadata/summarized event; chưa có provider/call site/log thật. |
| `EV-008` | GitNexus re-analyze/status tại commit `46cb278` | `PASS — index current` | Hỗ trợ tra cứu code; không thay thế test transaction/RBAC/AI. |
| `EV-009` | Các model Product/Invoice/Inventory/Report | `IMPLEMENTED — model evidence` | Xác nhận field/guard dùng cho thiết kế; không suy ra route/view/report đầy đủ. |

## A.3. AI đề xuất gì và sinh viên kiểm chứng/chỉnh sửa gì

| Chủ đề | Đề xuất từ prompt/tài liệu | Kiểm chứng/chỉnh sửa của nhóm |
|---|---|---|
| Tư vấn sản phẩm | RAG chỉ dùng context có citation, tối đa 3 gợi ý, nêu khi thiếu dữ liệu. | Lọc `Product.status` và `stock_qty` ở server; output không được tạo ID ngoài context; `AI-001` giữ `PROPOSED`. |
| Hỏi đáp tài liệu | Trả lời kèm citation và thừa nhận không đủ thông tin. | `KnowledgeService.format_context()` có format citation; nhóm công bố `AI-004` là retrieval/context, không gọi là chatbot. |
| Bán hàng–tồn | AI có thể nhận xét/khuyến nghị. | Nhóm giữ database/ledger là nguồn sự thật; `Invoice.confirm()` hiện chưa tạo `StockMovement.OUT`, nên không công bố flow bán–tồn đã hoàn thiện. |
| Prompt injection/privacy | Không tiết lộ system prompt, không chạy SQL/tool, không gửi PII thừa. | Đưa thành guardrail/acceptance gate; chưa có provider runtime để ghi `PASS`. |
| GitNexus/RAG | Dùng graph và embedding để tra cứu context. | Cập nhật index GitNexus; tách Chroma khỏi ERD giao dịch; không trộn model notebook với provider RAG runtime. |

## A.4. Kết luận mục 9

Bằng chứng hiện có đủ để chứng minh nhóm đã dùng AI-oriented prompts, document retrieval, embedding experiment và công cụ code intelligence trong quá trình phân tích/thiết kế. Chưa có phản hồi LLM/provider end-to-end được lưu trong repo; do đó báo cáo không bịa response, accuracy, latency hay uptime. Các mục `AI-001`–`AI-003` tiếp tục là `PROPOSED/OPEN`.

# Phụ lục B — Ma trận truy xuất và cổng bàn giao

| Mục đề | Nội dung chính | Mã/nguồn truy xuất | Cổng kiểm tra |
|---|---|---|---|
| 1 | Bối cảnh, actor, dữ liệu, quy trình, vấn đề | `BR-*`, `SRC-001/002`, `docs/03` | Bảng vấn đề–dữ liệu–kết quả và flow bán hàng. |
| 2 | Yêu cầu chức năng | `FR-001..015`, `BR-*` | Mỗi FR có input–processing–output–acceptance. |
| 3 | Yêu cầu phi chức năng | `NFR-*` | Target phải gắn nhãn đề xuất nếu chưa có benchmark; kiểm tra bảo mật/RBAC/backup/UX. |
| 4 | Actor/use case | `ACT-*`, `UC-001..013` | Input/output/tiền-hậu điều kiện; quyền `Owner` chưa chốt phải đánh dấu `OPEN`. |
| 5 | CSDL/ERD | `DB-*`, `DB-C*` | Đối chiếu field `line_amount`, FK, status, cardinality và invariant confirm. |
| 6 | Kiến trúc | `ARCH-*`, `FLOW-ARCH-*` | Tách current/target; Chroma không phải DB giao dịch. |
| 7 | Vị trí AI | `AI-001..004` | Gắn đúng actor, dữ liệu, giá trị và trạng thái `PROPOSED`/retrieval `IMPLEMENTED`. |
| 8 | Prompt/luồng AI | prompt contract, JSON schema, guardrail | Mẫu prompt/JSON chỉ là thiết kế minh họa, có fallback/privacy/timeout. |
| 9 | Minh chứng AI | `EV-001..009`, `EV-CHK-*` | Prompt → nguồn/log → kiểm chứng → chỉnh sửa; không bịa provider response. |
| 10 | Báo cáo/kế hoạch | `PLAN-*`, `PLAN-AC-*`, `PLAN-R-*` | Có giai đoạn, tiêu chí pass/fail, rủi ro và điều kiện nâng status. |

## B.1. Cổng triển khai bắt buộc trước khi công bố sản phẩm hoàn chỉnh

1. Chốt ma trận quyền `Admin/Staff/Owner` và môi trường demo/database/provider.
2. Hoàn thiện transaction bán–tồn: `StockMovement.OUT`, rollback khi vượt kho, idempotency, hủy/hoàn và test `FLOW-T01`–`FLOW-T06`.
3. Hoàn thiện selector báo cáo deterministic; chỉ đọc invoice `CONFIRMED`; hiển thị metric nguồn trước nhận xét AI.
4. Tách provider adapter; validate schema; timeout/retry hữu hạn; fallback; redact PII; ghi `AIEventLog`; có evaluation set.
5. Bảo vệ endpoint knowledge theo user/role, secret scan, backup/restore và demo tái lập.

## B.2. Checklist file nộp

- Không có `.env`, API key, mật khẩu, database local, cache, `.gitnexus/` hoặc `knowledge_store/`.
- Link trong tài liệu là đường dẫn tương đối trong repo; không dùng đường dẫn ổ đĩa cá nhân.
- Các phần chưa có code/test/provider được ghi `PROPOSED` hoặc `OPEN`.
