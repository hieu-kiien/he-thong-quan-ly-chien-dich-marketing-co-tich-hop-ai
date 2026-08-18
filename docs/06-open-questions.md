---
document_id: AIA331-DOC-06
document_type: open-questions
project_id: AIA331-80300-MARKETING-AI
priority: P2
priority_level: MEDIUM
status: OPEN
last_reviewed: 2026-08-18
---

# Điểm mở cần chốt

Các câu hỏi dưới đây không được AI tự trả lời như sự thật đã chốt.

| ID | Câu hỏi | Mặc định baseline | Người cần xác nhận |
|---|---|---|---|
| DEC-001 | Dùng Django hay FastAPI? | Django + SQLite | Nhóm/giảng viên |
| DEC-002 | Vai trò chính gọi là Manager/Staff hay tên khác? | Marketing Manager/Marketing Staff | Nhóm |
| DEC-003 | Có bắt buộc kết nối provider thật khi demo? | Fallback offline cho baseline | Giảng viên |
| DEC-004 | Schedule/Budget có cần tách bảng riêng? | Gộp vào Content/Campaign | Nhóm |
| DEC-005 | Metric cần thêm reach/impressions hay doanh thu? | views, clicks, conversions, cost | Nhóm |
| DEC-006 | Có cần RAG trả lời tài liệu trong sản phẩm? | RAG hỗ trợ tài liệu, không dùng thay metric | Nhóm |
| DEC-007 | Độ dài báo cáo và mẫu bìa chính thức? | 25–40 trang nội dung, bìa ICTU tối giản | Giảng viên |

## Quy tắc chốt

Khi có câu trả lời, ghi `decision`, `decided_by`, `decided_at`, `evidence`, sau
đó đồng bộ `project.md`, requirements, code và báo cáo. Không sửa yêu cầu gốc
chỉ để làm cho code hiện tại có vẻ đã đạt.
