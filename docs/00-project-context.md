---
document_id: BAI03-DOC-00
document_type: project-context
project_id: BAI03-SALES-AI
project_title: Hệ thống quản lý bán hàng có tích hợp AI
priority: P1
status: DERIVED
authority: curated-context
sources:
  - ../project.md
  - ../informember.md
  - ../ContextProject.md
  - 99-source-register.md
last_reviewed: 2026-08-17
---

# Bối cảnh dự án — BAI03-SALES-AI

## 1. Định danh

| Thuộc tính | Giá trị | Trạng thái |
|---|---|---|
| `project_id` | `BAI03-SALES-AI` | `CANONICAL` trong lớp tài liệu này |
| Tên | Hệ thống quản lý bán hàng có tích hợp AI | `CANONICAL` |
| Cấp ưu tiên | `P1` / `HIGH` | Ưu tiên cao nhất trong phạm vi hồ sơ Bài 03 và truy hồi AI |
| Miền nghiệp vụ | Bán lẻ: sản phẩm, khách hàng, hóa đơn, nhập hàng, tồn kho, báo cáo | `CANONICAL` |
| Mục tiêu AI | Tư vấn sản phẩm, nhận xét doanh thu, hỏi đáp dữ liệu bán hàng | `CANONICAL` về phạm vi; chưa phải hiện thực |
| Framework hiện đang có trong code | Django | `IMPLEMENTED`/quan sát được; yêu cầu gốc vẫn cho phép framework khác |
| Mốc kế hoạch | 27/07/2026–27/09/2026 trong DOCX kế hoạch | `DERIVED`, cần xác nhận là lịch chính thức |

## 2. Vấn đề và mục tiêu

Cửa hàng bán lẻ cần giảm việc nhập liệu rời rạc và tổng hợp thủ công. Hệ thống
phải hỗ trợ nhân viên thao tác bán hàng, chủ cửa hàng theo dõi doanh thu/tồn
kho, quản lý dữ liệu tập trung và dùng AI như một lớp hỗ trợ có kiểm soát.

Mục tiêu yêu cầu gốc:

- quản lý người dùng/vai trò, sản phẩm, nhóm hàng, khách hàng, hóa đơn, nhập
  hàng, tồn kho và báo cáo;
- tích hợp ba chức năng AI gắn với dữ liệu hệ thống;
- dùng AI trong các giai đoạn SDLC, nhưng phải lưu minh chứng và kiểm chứng kết
  quả do AI sinh ra;
- có dữ liệu mẫu, phân quyền, hướng dẫn chạy và kịch bản demo.

## 3. Actor và quyền ở mức yêu cầu

| Actor | Trách nhiệm dự kiến | Độ chắc chắn |
|---|---|---|
| `Admin` / Quản trị viên | Tài khoản, vai trò, cấu hình và thao tác quản trị được cấp quyền | `CANONICAL` |
| `Staff` / Nhân viên bán hàng | Tra cứu sản phẩm/khách hàng, lập hóa đơn, hỗ trợ tư vấn | `CANONICAL` |
| `Owner` / Chủ cửa hàng | Theo dõi dashboard, báo cáo, hỏi đáp dữ liệu, quyết định nhập hàng | `CANONICAL` |
| `Manager` / Quản lý | Tên vai trò xuất hiện trong tài liệu BA; có thể là alias của `Owner` | `OPEN` |
| `AI provider` | Dịch vụ ngoài hoặc mô hình local được gọi qua adapter | `PROPOSED`, chưa có trong code |

Không tự gộp `Manager`, `Store Manager`, `Owner` thành ba vai trò mới. Cần một
quyết định quyền cuối cùng trước khi hoàn thiện RBAC.

## 4. Phạm vi chức năng

| Nhóm | Nội dung |
|---|---|
| Nhận diện | Đăng nhập, đăng xuất, tạo/quản lý tài khoản, phân quyền |
| Catalog | Nhóm hàng, sản phẩm, mã/SKU, giá nhập, giá bán, tồn kho, trạng thái |
| Khách hàng | Thông tin liên hệ, nhóm khách hàng, lịch sử mua hàng |
| Bán hàng | Hóa đơn, chi tiết hóa đơn, giảm giá, phương thức thanh toán, tổng tiền |
| Nhập và tồn | Phiếu nhập, dòng nhập, tăng/giảm tồn, cảnh báo tồn thấp |
| Tra cứu | Tìm kiếm/lọc sản phẩm, khách hàng, hóa đơn theo tiêu chí phù hợp |
| Báo cáo | Doanh thu ngày/tháng/nhóm hàng, sản phẩm bán chạy, xuất PDF/Excel/CSV |
| AI | Tư vấn sản phẩm, nhận xét doanh thu, hỏi đáp dữ liệu bán hàng |

## 5. Dữ liệu lõi dự kiến

`User/Role`, `Category`, `Product`, `Customer`, `Supplier`, `Invoice`,
`InvoiceItem`, `GoodsReceipt`, `GoodsReceiptLine`, `StockMovement` và các bản
ghi báo cáo là các thực thể được yêu cầu hoặc xuất hiện trong code. Tên model
không hoàn toàn giống nhau giữa hai nhánh Django; xem
[`02-architecture-and-code-status.md`](02-architecture-and-code-status.md)
trước khi tạo migration hoặc API mới.

## 6. Ranh giới giữa yêu cầu và hiện thực

| Nội dung | Yêu cầu gốc | Hiện trạng đã quan sát |
|---|---|---|
| Backend | FastAPI/Flask/Django đều được chấp nhận | Hai nhánh code đều là Django |
| Database demo | SQLite | `Code QLBH` dùng SQLite; `sales_management` cấu hình PostgreSQL |
| AI provider | OpenAI/Gemini/Claude/Hugging Face/Ollama | Chưa thấy dependency/client/endpoint gọi provider |
| Prompt runtime | Tách trong `prompts/` | Có prompt tài liệu/thử nghiệm, chưa thấy luồng gọi AI trong app |
| Test | Hóa đơn, tồn kho, báo cáo, AI | Có test CRUD danh mục; nhiều test còn rỗng hoặc chưa đủ phạm vi |
| Deploy | Local hoặc cloud, có `.env.example` | Có README và `.env.example` ở các nhánh; chưa chứng minh deploy |

## 7. Không thuộc phạm vi

- [`KT1_PHAN_TICH_THIET_KE.md`](<../../../KT1_PHAN_TICH_THIET_KE.md>) là dự án
  `BAOHANHAI`, không phải một phiên bản khác của dự án bán hàng.
- [`QLBH demo/`](<../../QLBH demo/>) là bản demo cũ dùng để tham khảo lịch sử,
  không phải baseline triển khai.
- Các PDF/PNG bài giảng và `Bài giảng DJANGO.docx` chỉ giải thích kiến thức,
  không phải yêu cầu hoặc bằng chứng hệ thống đã chạy.

## 8. Quy tắc suy luận cho AI

Khi được hỏi về dự án, AI nên trả lời theo mẫu: `kết luận` → `trạng thái`
(`CANONICAL`/`IMPLEMENTED`/`OPEN`) → `nguồn` → `điểm chưa xác minh`. Với một
chức năng chưa có route, view/service hoặc test tương ứng, phải nói là “chưa
được chứng minh triển khai”, không nói “đã hoàn thành” chỉ vì chức năng xuất
hiện trong `project.md` hoặc DOCX.
