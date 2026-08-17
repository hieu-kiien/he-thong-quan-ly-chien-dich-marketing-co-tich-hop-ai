---
document_id: BAI03-DOC-01
document_type: requirements-summary
project_id: BAI03-SALES-AI
status: DERIVED
authority: normalized-requirements
sources:
  - ../project.md
  - ../../../Bai 02/CacGiaiDoanThucHien/02_GenAI_SoftwareDevelopment_requirements-qa.docx
last_reviewed: 2026-08-17
---

# Ma trận yêu cầu chuẩn hóa

Các ID dưới đây được chuẩn hóa theo tài liệu BA đã sinh và đối chiếu lại với
`project.md`. `CANONICAL` nghĩa là phạm vi được yêu cầu; không có nghĩa là mã
nguồn đã triển khai.

## 1. Functional Requirements

| ID | Tên | Mô tả ngắn | Ưu tiên | Trạng thái code |
|---|---|---|---|---|
| FR-001 | Đăng nhập hệ thống | Xác thực username/password và mở phiên làm việc | Must | Chưa chứng minh đầy đủ |
| FR-002 | Phân quyền người dùng | Giới hạn chức năng theo vai trò | Must | Có model/khung quyền ở một nhánh; route bảo vệ chưa đủ |
| FR-003 | Quản lý sản phẩm | CRUD mã, tên, giá, tồn, trạng thái | Must | Model có ở `sales_management`; CRUD chưa đầy đủ |
| FR-004 | Quản lý nhóm hàng | CRUD nhóm/danh mục sản phẩm | Must | CRUD `categories` đã có ở `sales_management` |
| FR-005 | Quản lý khách hàng | CRUD, tìm kiếm và lịch sử mua | Must | Model có; URL/view chưa đầy đủ |
| FR-006 | Lập hóa đơn bán hàng | Chọn dòng hàng, số lượng, giảm giá, thanh toán, tổng tiền | Must | Model có; luồng UI/API chưa đủ |
| FR-007 | Xem/tìm kiếm hóa đơn | Tra cứu theo mã, khách hàng, thời gian và xem chi tiết | Must | Chưa có route hoàn chỉnh |
| FR-008 | Quản lý nhập hàng | Tạo phiếu nhập và cập nhật hàng vào kho | Must | Model/service một phần ở `sales_management` |
| FR-009 | Quản lý tồn kho | Xem tồn, cảnh báo, không cho bán âm kho | Must | Có logic `StockMovement`; cần kiểm thử/route |
| FR-010 | Tìm kiếm và lọc dữ liệu | Tìm sản phẩm, khách hàng, hóa đơn theo tiêu chí | Must | Chưa chứng minh đầy đủ |
| FR-011 | Thống kê doanh thu | Dashboard, doanh thu theo kỳ/nhóm, top sản phẩm | Must | Có model snapshot; chưa có báo cáo chạy qua route |
| FR-012 | Xuất báo cáo | Xuất doanh thu/hóa đơn ra PDF, Excel hoặc CSV | Should | Chưa thấy hiện thực |
| FR-013 | Chatbot tư vấn sản phẩm | Gợi ý tối đa 3 sản phẩm còn hàng theo nhu cầu | Must | Chưa có provider/client/endpoint |
| FR-014 | AI sinh báo cáo doanh thu | Sinh nhận xét và khuyến nghị từ số liệu hệ thống | Must | Chưa có luồng AI chạy |
| FR-015 | Hỏi đáp dữ liệu bán hàng | Trả lời câu hỏi tự nhiên dựa trên dữ liệu có quyền truy cập | Should | Chưa có luồng AI chạy |

## 2. Non-Functional Requirements

Các con số trong bảng là mục tiêu từ tài liệu BA, cần đo bằng kiểm thử trước khi
được gọi là kết quả.

| ID | Nhóm | Yêu cầu | Ưu tiên |
|---|---|---|---|
| NFR-001 | Performance | CRUD phản hồi trong 2 giây ở điều kiện bình thường | Must |
| NFR-002 | Performance | Tối thiểu 5 người dùng đồng thời cho demo | Must |
| NFR-003 | Security | Mật khẩu phải được hash trước khi lưu | Must |
| NFR-004 | Security | API key ở biến môi trường, không hardcode/commit | Must |
| NFR-005 | Security | Dùng ORM/parameterized query chống SQL injection | Must |
| NFR-006 | Security | Kiểm soát dữ liệu hiển thị để giảm XSS | Must |
| NFR-007 | Authentication | Session hoặc JWT | Must |
| NFR-008 | Authentication | Khóa tạm thời sau 5 lần sai liên tiếp | Must |
| NFR-009 | Authorization | Kiểm tra quyền ở mỗi request/API | Must |
| NFR-010 | Audit | Ghi log thao tác quan trọng | Must |
| NFR-011 | Logging | Tách error log và access log | Must |
| NFR-012 | Logging | Ghi nhận request AI, latency và trạng thái | Must |
| NFR-013 | Backup | Có sao lưu; demo có thể export thủ công | Should |
| NFR-014 | Recovery | Khôi phục từ bản sao lưu gần nhất trong 30 phút | Should |
| NFR-015 | Scalability | Có thể đổi SQLite sang MySQL/PostgreSQL bằng cấu hình | Should |
| NFR-016 | Maintainability | Tách module; prompt tách khỏi code | Must |
| NFR-017 | Availability | Mục tiêu uptime 95% trong giờ hoạt động | Should |
| NFR-018 | Reliability | Xử lý lỗi DB và timeout AI với thông báo thân thiện | Must |
| NFR-019 | Cost | Có thể dùng SQLite/Ollama để giảm chi phí | Should |
| NFR-020 | AI latency | AI mục tiêu 15 giây, timeout tối đa 30 giây | Must |
| NFR-021 | AI accuracy | Không gợi ý hết hàng; mục tiêu đúng tối thiểu 70% | Should |
| NFR-022 | Explainability | Nêu lý do ngắn cho từng gợi ý | Should |
| NFR-023 | Hallucination control | Chỉ dùng dữ liệu được cung cấp; thiếu thì nói rõ | Must |
| NFR-024 | Prompt security | Chống prompt injection và ghi đè system prompt | Must |
| NFR-025 | Privacy | Không gửi PII/thanh toán không cần thiết cho AI | Must |
| NFR-026 | Compliance | Dùng dữ liệu khách hàng đúng mục đích | Should |

## 3. Business Rules

| ID | Quy tắc |
|---|---|
| BR-001 | Mật khẩu tối thiểu 6 ký tự |
| BR-002 | Khóa tài khoản 15 phút sau 5 lần đăng nhập sai liên tiếp |
| BR-003 | Không tạo hóa đơn vượt tồn kho |
| BR-004 | Hóa đơn phải có ít nhất một dòng hàng |
| BR-005 | AI chỉ gợi ý sản phẩm có tồn kho lớn hơn 0 |
| BR-006 | Không gửi số điện thoại đầy đủ hoặc dữ liệu thanh toán cho AI nếu không cần |
| BR-007 | AI chỉ khuyến nghị; không tự đặt hàng |
| BR-008 | Báo cáo AI là tham khảo, không thay thế quyết định con người |
| BR-009 | SKU/mã sản phẩm duy nhất |
| BR-010 | Giá bán lớn hơn hoặc bằng giá nhập |
| BR-011 | Không xóa khách hàng đã có lịch sử; chuyển trạng thái |
| BR-012 | Không xóa sản phẩm đã có giao dịch; chuyển trạng thái |
| BR-013 | Hóa đơn đã lưu không sửa trực tiếp; xử lý bằng hủy và lập lại |
| BR-014 | Nhập tăng kho, bán giảm kho, hủy hoàn kho |
| BR-015 | Số điện thoại khách hàng duy nhất nếu có nhập |
| BR-016 | Chỉ Admin có quyền xóa dữ liệu |
| BR-017 | Giảm giá không vượt tổng tiền trước giảm |
| BR-018 | API key chỉ nằm trong biến môi trường |

## 4. User Stories và Use Cases

Tài liệu BA đã sinh có 14 user story (`US-001`–`US-014`) và 5 use case chính:

| Use Case | Nội dung | Liên quan |
|---|---|---|
| UC-001 | Đăng nhập hệ thống | FR-001, BR-001–002 |
| UC-002 | Lập hóa đơn bán hàng | FR-006, BR-003–004, BR-013, BR-017 |
| UC-003 | Chatbot tư vấn sản phẩm | FR-013, BR-005–006 |
| UC-004 | AI sinh báo cáo doanh thu | FR-014, BR-006–008 |
| UC-005 | Nhập hàng và cập nhật tồn kho | FR-008–009, BR-014 |

User story và acceptance criteria chi tiết nằm trong
   [`Bai 02/CacGiaiDoanThucHien/02_GenAI_SoftwareDevelopment_requirements-qa.docx`](<../../../Bai 02/CacGiaiDoanThucHien/02_GenAI_SoftwareDevelopment_requirements-qa.docx>).

## 5. Traceability rút gọn

| FR | BR/US/UC | Module đích | Bằng chứng cần có |
|---|---|---|---|
| FR-001–002 | BR-001–002, US-001–002, UC-001 | accounts/auth | model, form/view, permission test |
| FR-003–004 | BR-009–010, US-003 | catalog/products/categories | model constraint, CRUD, test |
| FR-005 | BR-011/015, US-004 | customers | model, search, permission test |
| FR-006–007 | BR-003/004/013/017, US-005–006, UC-002 | sales/invoices | transaction, invoice test, route |
| FR-008–009 | BR-003/014, US-007–008, UC-005 | inventory/purchases | stock movement, invariant test |
| FR-010 | US-009 | search | filter tests và đo thời gian |
| FR-011–012 | US-010–011 | reports | query, dashboard/export test |
| FR-013 | BR-005/006, US-012, UC-003 | AI/product advice | server-side filter, prompt/eval/fallback |
| FR-014 | BR-006–008, US-013, UC-004 | AI/report | deterministic metrics + human review |
| FR-015 | BR-006, US-014 | AI/query | read-only allowlist + access control |

## 6. Tiêu chí chấp nhận tối thiểu

- Không bán âm kho và không làm sai tổng hóa đơn trong các tình huống bình
  thường, biên và lỗi.
- Quyền truy cập được kiểm tra trên server, không chỉ ẩn nút ở giao diện.
- AI không được tạo sản phẩm/giá/tồn kho ngoài dữ liệu đầu vào; lỗi/timeout phải
  có fallback rõ.
- Báo cáo hiển thị được kỳ dữ liệu và nguồn số liệu trước khi hiển thị nhận xét
  AI.
- Mọi tiêu chí hiệu năng, độ chính xác và uptime phải có phương pháp đo cùng
  kết quả, không dùng số mục tiêu làm bằng chứng.
