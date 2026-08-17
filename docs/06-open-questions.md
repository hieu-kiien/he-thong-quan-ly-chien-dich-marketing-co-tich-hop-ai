---
document_id: BAI03-DOC-06
document_type: open-questions-and-decisions
project_id: BAI03-SALES-AI
status: OPEN
authority: decision-log
last_reviewed: 2026-08-17
---

# Điểm mở, xung đột và quyết định cần chốt

Các mục `OPEN` không được AI tự biến thành sự thật. Khi nhóm chốt, cập nhật
`status`, người quyết định, ngày và nguồn bằng chứng.

## 1. Quyết định kỹ thuật

| ID | Vấn đề | Hiện trạng | Đề xuất để nhóm xác nhận |
|---|---|---|---|
| DEC-001 | Chọn baseline code | Có `Code QLBH` là skeleton và `sales_management` là nhánh partial | Dùng `sales_management` làm base hiện thực; lấy blueprint/service boundary của `Code QLBH` để hợp nhất |
| DEC-002 | Framework | Yêu cầu cho phép FastAPI/Flask/Django; code đang là Django | Chốt Django cho bài nộp hiện tại |
| DEC-003 | Database | `Code QLBH` dùng SQLite; `sales_management` cấu hình PostgreSQL | Chốt SQLite cho demo reproducible hoặc PostgreSQL nếu có service/seed rõ |
| DEC-004 | AI provider | Chưa có client/provider trong code | Chọn một provider hoặc Ollama; tạo adapter thay vì gọi trực tiếp trong view |
| DEC-005 | Hỏi đáp dữ liệu | BA nhắc Text-to-SQL | Dùng intent + query allowlist read-only; chỉ cân nhắc Text-to-SQL có validator |
| DEC-006 | Export | Yêu cầu PDF/Excel/CSV nhưng chưa có implementation | Chốt ít nhất CSV/Excel cho MVP, PDF nếu còn thời gian |
| DEC-007 | Tồn kho khi bán/hủy | `Invoice.confirm()` hiện chưa tạo OUT movement | Bổ sung service transaction và test trước khi công bố FR-006/009 |

## 2. Xung đột nguồn

| ID | Xung đột | Nguồn A | Nguồn B | Cách xử lý hiện tại |
|---|---|---|---|---|
| CON-001 | Vai trò thành viên Mai | BAI02: chưa ghi vai trò | BAI03: Phó nhóm | Tạm dùng BAI03 trong phạm vi Bài 03; cần xác nhận chính thức |
| CON-002 | Tên vai trò nghiệp vụ | `Admin/Staff/Owner` trong project brief | `Manager/Store Manager` trong BA | Không tự gộp; chốt bảng quyền cuối |
| CON-003 | Định dạng timezone | Một số settings dùng `Asia/Bangkok`; nhánh partial dùng `Asia/Ho_Chi_Minh` | Hai cấu hình khác nhau | Chốt `Asia/Ho_Chi_Minh` nếu nhóm dùng múi giờ Việt Nam và cập nhật một nguồn |
| CON-004 | README Bài 03 | README cũ nói về số nguyên tố | Code và project nói về bán hàng | Đã tách nội dung legacy và thay README bằng chỉ mục dự án |
| CON-005 | Dự án KT1 | BaoHanhAI có actor/schema/AI riêng | BAI03 là bán hàng | Giữ `KT1_PHAN_TICH_THIET_KE.md` là project độc lập |

## 3. Câu hỏi nghiệp vụ cần trả lời

- Chủ cửa hàng có được tạo/sửa sản phẩm, nhập hàng và xem PII ở mức nào?
- Nhân viên có được xem giá nhập, báo cáo doanh thu và chức năng AI doanh thu
  hay chỉ AI tư vấn sản phẩm?
- Hóa đơn sau xác nhận có được hoàn/hủy một phần không? Cách hoàn kho là gì?
- Giảm giá là phần trăm, số tiền, theo dòng hay trên toàn hóa đơn?
- Số điện thoại khách hàng có bắt buộc và có được dùng làm định danh không?
- Ngưỡng “tồn thấp” do ai cấu hình và báo cáo theo thời điểm nào?
- PDF/Excel/CSV nào là bắt buộc cho MVP?
- Tập dữ liệu đánh giá AI, người chấm và định nghĩa “phù hợp” là gì?
- Lịch 9 tuần trong DOCX có phải lịch chính thức không?

## 4. Quy tắc cập nhật quyết định

Khi chốt một mục, thêm `decision`, `decided_by`, `decided_at`, `evidence` và
đồng bộ các file bị ảnh hưởng. Không sửa ngầm requirement gốc để làm cho code
hiện tại có vẻ đã đạt.
