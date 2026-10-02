# Trung tâm tài liệu MarketFlow AI

Tài liệu này là mục lục cho **tài liệu sống của dự án**. Các tài liệu PDF/LaTeX V8/V9 là hồ sơ phiên bản học thuật; ghi chú trong `.agents/` là lịch sử làm việc nội bộ. Chúng không thay thế tài liệu hiện hành bên dưới.

## Bắt đầu theo nhu cầu

| Tôi muốn… | Đọc |
|---|---|
| Hiểu sản phẩm, trạng thái hiện tại và khởi chạy local | [README gốc](../README.md) |
| Biết hướng sản phẩm/kỹ thuật và thứ tự công việc dài hạn | [Lộ trình](ROADMAP.md) |
| Hiểu cấu trúc kỹ thuật đang có | [Kiến trúc](ARCHITECTURE.md) |
| Chạy hoặc đọc kết quả kiểm thử | [Testing và CI](TESTING.md) |
| Hiểu phạm vi benchmark AI, kết quả và giới hạn | [AI evaluation report](AI_EVALUATION_REPORT.md) |
| Xem bối cảnh release V9.5 | [Release notes lịch sử](RELEASE_NOTES_V9.5_OPERATIONS.md) |
| Chuẩn bị nội dung đối chiếu đồ án | [Rubric alignment draft](UNIVERSITY_DEFENSE_RUBRIC_ALIGNMENT.md) |
| Hiểu cách deploy Cloudflare và giới hạn lưu trữ | [Cloudflare README](../cloudflare/README.md) |

## Nguồn sự thật theo chủ đề

| Chủ đề | Nguồn chuẩn |
|---|---|
| API | Router/backend và OpenAPI tại `/docs` khi chạy local. |
| Schema và quyền | ORM/model, database setup/migrations và authorization trong backend. |
| Cấu hình | Config code, `.env.example` nếu có, `docker-compose.yml` và cấu hình deploy tương ứng. Không đưa secret vào tài liệu. |
| Hành vi hiện tại | Mã nguồn và test; tài liệu kiến trúc tóm tắt, không thay thế chúng. |
| Kết quả CI | GitHub Actions theo commit; ghi link run và commit khi trích số liệu. |
| Benchmark AI | `scripts/evaluate_ai_grounding.py` là generator; báo cáo được sinh lại trong Gate 5. Kết quả chỉ đúng với bộ case/môi trường ghi trong báo cáo. |
| Roadmap | [ROADMAP.md](ROADMAP.md), trạng thái đề xuất cho đến khi có quyết định/evidence mới. |
| Hồ sơ nộp V8/V9 | PDF và source trong `Bao_Cao_AIA331_80300_ICTU_V8/` và `Bao_Cao_AIA331_80300_ICTU_V9/`; xem README từng thư mục. Giữ nguyên như snapshot lịch sử. |

## Quy tắc duy trì

- Ghi rõ trạng thái: đã hiện thực, đã kiểm thử, đã đo, đề xuất hoặc chưa xác nhận.
- Không chép số liệu dễ đổi sang nhiều tài liệu; trỏ tới run CI hoặc báo cáo sinh tự động.
- Khi thay đổi mã, cập nhật tài liệu kiến trúc/kiểm thử liên quan trong cùng thay đổi.
- Tài liệu được sinh tự động cần sửa generator, rồi cập nhật artifact cùng nguồn sinh.
- Giữ biên bản, yêu cầu ban đầu, PDF nộp và nhật ký `.agents/` làm hồ sơ; không dùng chúng làm hướng dẫn hiện hành.
- Không công bố mật khẩu mẫu, secret, thông tin người dùng hoặc dữ liệu khách hàng trong tài liệu.

## Tài liệu lịch sử và hồ sơ học thuật

- [Release notes V9.5](RELEASE_NOTES_V9.5_OPERATIONS.md): snapshot lịch sử, không phải trạng thái phát hành hiện tại.
- [TEST_READY.md](../TEST_READY.md) và [TEST_INFRA.md](../TEST_INFRA.md): báo cáo test cũ; hướng dẫn hiện hành ở [TESTING.md](TESTING.md).
- [Biên bản nghiệm thu](../BIEN_BAN_NGHIEM_THU.md): hồ sơ lịch sử.
- [Yêu cầu ban đầu](../ORIGINAL_REQUEST.md): lưu nguyên văn làm nguồn bối cảnh.
- V8/V9: xem README trong từng thư mục để biết snapshot, nguồn LaTeX và PDF tương ứng.
