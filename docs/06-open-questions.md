---
document_id: AIA331-DOC-06
document_type: open-questions
project_id: AIA331-80300-MARKETING-AI
priority: P2
priority_level: MEDIUM
status: OPEN
last_reviewed: 2026-08-24
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
| DEC-007 | Độ dài báo cáo và mẫu bìa chính thức? | Bản kiểm tra được cô đọng còn 13 trang A4; bìa dùng logo/bố cục ICTU công khai làm tham chiếu, vẫn chờ mẫu GV | Giảng viên |
| DEC-008 | Bài 2 có yêu cầu nộp commit hash hoặc demo trên trình duyệt cụ thể không? | README/lệnh chạy/test đã có; commit cuối và trình duyệt/thiết bị demo cần nhóm chốt | Giảng viên/nhóm |

## Quy tắc chốt

Khi có câu trả lời, ghi `decision`, `decided_by`, `decided_at`, `evidence`, sau
đó đồng bộ `project.md`, requirements, code và báo cáo. Không sửa yêu cầu gốc
chỉ để làm cho code hiện tại có vẻ đã đạt.
