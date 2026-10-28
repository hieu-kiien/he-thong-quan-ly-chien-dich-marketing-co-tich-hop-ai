# Kế hoạch nghiên cứu và thiết kế dự án

## 1. Nhận diện dự án

- Tên dự án: Hệ thống quản lý chiến dịch marketing có tích hợp AI
- Học phần: Ứng dụng trí tuệ nhân tạo - AIA331
- Mã dự án: 80300
- Đơn vị: Trường Đại học Công nghệ Thông tin và Truyền thông, Đại học Thái Nguyên
- Nhóm: 25; Vũ Hiếu Kiên DTC245200244; Nguyễn Hải Đăng DTC245120051
- Giảng viên: TS. Nguyễn Tuấn Anh
- Mốc tài liệu: baseline phân tích và thiết kế trước khi triển khai
- Ranh giới đóng góp: thiết kế nghiệp vụ, kiến trúc, dữ liệu, AI workflow, kiểm thử và kế hoạch đánh giá; chưa có mã nguồn ứng dụng

## 2. Bài toán

- Stakeholder chính: Manager marketing, Marketer, người duyệt nội dung và giảng viên/assessor.
- Nỗi đau hiện tại: thông tin campaign, kênh, nội dung, lịch đăng, ngân sách và metrics thường rời rạc; tạo nội dung và tổng hợp kết quả tốn thời gian.
- Ý nghĩa: cần một workflow nhất quán để quản lý campaign và dùng AI như trợ lý có giới hạn, có nguồn context và có người chịu trách nhiệm duyệt.
- Phạm vi: authentication/RBAC, campaign/product/channel/content/schedule/metrics, dashboard và ba tác vụ AI là idea, draft và summary.
- Loại trừ: tự publish ra nền tảng bên ngoài, tối ưu ngân sách tự động, dự đoán doanh thu, huấn luyện model riêng và kết luận hiệu quả marketing thật khi chưa có dữ liệu thật.

## 3. Câu hỏi kỹ thuật

1. Làm thế nào thiết kế một workflow quản lý marketing có thể theo dõi được dữ liệu, trạng thái, quyền và approval thay vì chỉ là CRUD rời rạc?
2. Làm thế nào giới hạn AI bằng context whitelist, output schema, warning và human review để đánh giá được usefulness mà không biến output ngôn ngữ thành sự thật không kiểm chứng?
3. Làm thế nào nối requirements, kiến trúc, schema, test, evaluation và evidence thành một chuỗi mà giảng viên có thể kiểm tra lại?

## 4. Mục tiêu và tiêu chí thành công

| Mục tiêu | Chỉ số/bằng chứng | Tiêu chí |
|---|---|---|
| Quản lý nghiệp vụ cốt lõi | use case, API, CRUD test | campaign, content, schedule, metrics có đường đi đầy đủ và quyền rõ |
| Bảo toàn dữ liệu | ERD, FK, CHECK, negative test | không tạo record mồ côi; state và KPI có rule xác định |
| Dùng AI có kiểm soát | prompt contract, parser, failure matrix | output sai/timeout/thiếu context không trở thành nội dung hợp lệ |
| Human-in-the-loop | state machine, review log, demo | AI chỉ tạo draft; người có quyền mới approve/schedule |
| Chất lượng sản phẩm | test matrix, usability checklist, performance protocol | có cả test dương, test âm và kế hoạch đo, không chỉ screenshot |
| Tái lập | README, seed, manifest, commit | một người khác có thể dựng lại hoặc thấy rõ blocker |

## 5. Kế hoạch nghiên cứu

- Nguồn miền và học thuật: marketing analytics, AI trong marketing, human-AI interaction.
- Hệ thống tham chiếu: tài liệu analytics/campaign của các nền tảng marketing phổ biến; chỉ dùng để học workflow và giới hạn, không sao chép nhận diện thương hiệu hay tuyên bố benchmark.
- Chuẩn và hướng dẫn: ISO/IEC/IEEE 29148 cho requirements, ISO/IEC/IEEE 42010 cho architecture description, ISO/IEC 25010 cho quality, C4 cho architecture views, NIST AI RMF/GenAI Profile cho risk và governance.
- Chuẩn báo cáo: hướng dẫn dissertation/capstone của Cambridge và CMU được dùng để phân biệt implementation với evaluation, nêu mục tiêu, thiết kế, bằng chứng và giới hạn.
- Bằng chứng dự án: hai ảnh đề tài/yêu cầu do người dùng cung cấp, source LaTeX V8, DDL thiết kế, figures vector và ledger.

## 6. Kế hoạch thiết kế và đánh giá

- Thiết kế: context/use case, requirements, C4 container, logical/physical ERD, state machine, sequence AI approval, wireframe, deployment target.
- Kiểm thử: unit/domain/API/UI/integration, negative permission, data integrity, parser contract và fault injection.
- Đánh giá AI: bộ case cố định, ít nhất ba vòng so sánh prompt/model khi implementation cho phép; schema validity, grounding, usefulness, warnings, edit rate, latency.
- Tái lập: khóa input, seed, prompt version, provider/model/date, lệnh chạy và output gốc.

## 7. Rủi ro và unknown

| Item | Risk/unknown | Verification action | Status |
|---|---|---|---|
| Runtime | chưa có code nên chưa biết lỗi tích hợp | triển khai theo S0--S6, test mỗi lát | UNKNOWN |
| Provider | API/model, quota và chi phí chưa chọn | adapter, mock, log provider/model, so sánh có kiểm soát | UNKNOWN |
| Data | chưa có dữ liệu marketing thật | dùng seed rõ nguồn; không suy ra hiệu quả thật | UNKNOWN |
| Scale | SQLite chỉ là lựa chọn prototype | ADR và load test; giữ repository boundary | PROPOSED |
| UX | wireframe chưa phải usability evidence | task-based test và ghi nhận lỗi thao tác | PLANNED |

## 8. Quy tắc bằng chứng

Mọi câu trong báo cáo phải được phân loại bằng một trong các trạng thái: EXISTING, DESIGNED, PROPOSED, PLANNED, TESTED, MEASURED, VALIDATED hoặc UNKNOWN. Không dùng từ đã triển khai/đã đạt/đã chứng minh nếu chưa có artifact runtime tương ứng.
