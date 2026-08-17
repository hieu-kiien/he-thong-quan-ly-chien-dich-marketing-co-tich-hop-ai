# Quy ước dự án quản lý bán hàng

## Phạm vi

Thư mục này là nguồn làm việc chính cho dự án `BAI03-SALES-AI`, một hệ thống
quản lý bán hàng bằng Django có định hướng tích hợp AI. Không trộn nội dung của
dự án `BAOHANHAI` ở file `KT1_PHAN_TICH_THIET_KE.md` vào dự án này.

## Thứ tự ưu tiên nguồn

1. `project.md` và `informember.md`: yêu cầu gốc và thông tin nhóm.
2. Mã nguồn đã kiểm tra trong `Code QLBH/` và `sales_management/`.
3. Tài liệu phân tích/kiến trúc được suy ra từ hai nguồn trên.
4. DOCX đã sinh, prompt, template và tài liệu tham khảo.

Tài liệu phải ghi rõ trạng thái `CANONICAL`, `IMPLEMENTED`, `DERIVED`,
`PROPOSED`, `TEMPLATE`, `REFERENCE`, `LEGACY` hoặc `OPEN`. Không được trình
bày một yêu cầu như thể đã được triển khai nếu chưa có mã nguồn và kiểm thử
tương ứng.

## Quy tắc đọc và cập nhật

- Khi bắt đầu tra cứu, đọc `docs/README.md`, sau đó `docs/00-project-context.md`.
- Dùng các ID ổn định như `FR-001`, `NFR-001`, `AI-001` và `BR-001` khi liên kết
  yêu cầu, thiết kế, mã nguồn và kiểm thử.
- Dùng liên kết tương đối trong Markdown; không dùng đường dẫn ổ đĩa cá nhân
  hoặc đường dẫn phụ thuộc máy người viết trong tài liệu mới.
- Loại khỏi chỉ mục các thư mục sinh ra như `.venv/`, `venv/`, `__pycache__/`,
  file cơ sở dữ liệu local, cache và file chứa bí mật.
- Không đưa API key, mật khẩu hoặc nội dung `.env` vào tài liệu. Chỉ tham chiếu
  `.env.example`.

## Hai nhánh mã nguồn cần phân biệt

- `Code QLBH/`: skeleton kiến trúc modular; nhiều model, view, URL và test còn
  là khung trống.
- `sales_management/`: nhánh hiện thực một phần; model nghiệp vụ và CRUD
  danh mục có nội dung, nhưng phần lớn URL/view/test và toàn bộ tích hợp AI
  chưa hoàn chỉnh.

`QLBH demo/` ở cấp `Codes/` là bản demo cũ, chỉ dùng làm tài liệu lịch sử và
không phải nguồn triển khai chuẩn.

## Kiểm chứng trước khi bàn giao

Khi thay đổi mã nguồn hoặc tuyên bố tính năng đã hoàn thành, kiểm tra tối thiểu
`python manage.py check`, test liên quan và đối chiếu với ma trận trong
`docs/02-architecture-and-code-status.md`. Nếu môi trường chưa cài dependency,
ghi rõ đó là kiểm tra tĩnh, không gọi là test đã đạt.
