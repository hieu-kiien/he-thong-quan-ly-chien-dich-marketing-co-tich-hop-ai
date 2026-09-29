# Tài liệu AIA331 — Nhóm 25

Đây là bản LaTeX V8 của tài liệu phân tích và thiết kế cho đề tài **Hệ thống quản lý chiến dịch marketing có tích hợp trí tuệ nhân tạo**.

## Trạng thái

Bản này là hồ sơ phân tích–thiết kế trước khi nhóm bắt đầu lập trình. Những chỗ cần mã nguồn, dữ liệu chạy thật, kết quả kiểm thử hoặc phép đo đều được ghi là việc cần thực hiện; không có số liệu runtime được tạo giả.

## Biên dịch

Mở terminal tại thư mục này. Để không trộn file trung gian vào thư mục báo cáo, biên dịch vào một thư mục tạm bên ngoài:

```powershell
$aiaBuild = Join-Path $env:TEMP 'aia331-build'
New-Item -ItemType Directory -Force $aiaBuild | Out-Null
xelatex -interaction=nonstopmode -halt-on-error -output-directory $aiaBuild -jobname report_final main.tex
xelatex -interaction=nonstopmode -halt-on-error -output-directory $aiaBuild -jobname report_final main.tex
```

XeLaTeX được dùng để giữ tiếng Việt và phông chữ trong PDF ổn định. Các hình kỹ thuật nằm trong `figures/` dưới dạng TikZ nên có thể sửa trực tiếp; thiết kế schema nằm ở `design/schema.sql`.

## Cấu trúc chính

- `main.tex`, `ictu_v8_style.sty`: điểm vào và quy cách trình bày.
- `chapters/`: các chương, tài liệu tham khảo và phụ lục.
- `figures/`: sơ đồ bối cảnh, kiến trúc, ERD, trạng thái, sequence, AI và wireframe.
- `research_pack/`: nguồn, traceability, related work, kế hoạch đánh giá và tái lập.
- `design/schema.sql`: DDL thiết kế để dùng khi bắt đầu triển khai.
- `Bao_Cao_AIA331_80300_ICTU_V8.pdf`: PDF nộp chính thức đã biên dịch và kiểm tra trực quan.

## Khi nhóm bắt đầu code

Sau mỗi phần triển khai, cần cập nhật lại trạng thái trong báo cáo và `research_pack/`: thay phần “dự kiến/chưa có bằng chứng” bằng mã nguồn, test log, dữ liệu và kết quả đo thực tế tương ứng.
