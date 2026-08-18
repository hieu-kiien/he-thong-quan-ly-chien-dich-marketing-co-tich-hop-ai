# CONTEXT CHUNG — AIA331 MARKETING AI

Đây là context dùng chung cho việc phân tích và xây dựng **Hệ thống quản lý
chiến dịch marketing có tích hợp AI** của học phần AIA331, mã 80300.

## 1. Bối cảnh

Doanh nghiệp cần quản lý chiến dịch, kênh truyền thông, nội dung, ngân sách,
lịch đăng và chỉ số hiệu quả trên một hệ thống. AI hỗ trợ tạo nội dung nháp,
tóm tắt kết quả và gợi ý cải thiện; người phụ trách vẫn kiểm tra và duyệt.

## 2. Actor

- Quản lý marketing: quản lý chiến dịch/ngân sách, duyệt nội dung, xem thống kê.
- Nhân viên marketing: nhập nội dung/lịch/chỉ số và yêu cầu AI hỗ trợ.
- AI service: nhận dữ liệu đã được cấp quyền, trả kết quả nháp có cảnh báo.

## 3. Dữ liệu lõi

`User`, `Role`, `Campaign`, `Channel`, `Content`, `Schedule`, `Budget`, `Metric`.
Baseline gộp `Schedule` vào `Content.scheduled_at` và `Budget` vào
`Campaign.budget` để giảm độ phức tạp cho bản demo.

## 4. Công nghệ baseline

- Python/Django, Django ORM, HTML/CSS.
- SQLite cho local demo; có thể đổi PostgreSQL khi triển khai.
- Provider adapter OpenAI-compatible và fallback offline.

## 5. Quy tắc bảo mật

Dùng authentication/authorization, CSRF, hash mật khẩu, kiểm tra quyền; API key
chỉ ở `.env`. Không gửi dữ liệu nhạy cảm cho AI nếu không cần.

## 6. Quy tắc AI

Prompt tách khỏi view, có version; output phải có schema/cảnh báo; nội dung AI
không được đăng nếu chưa có người duyệt. Nếu thiếu dữ liệu hoặc provider lỗi,
hệ thống phải nói rõ và dùng fallback an toàn.

## 7. Phân biệt đề tài

Các tài liệu nói về sản phẩm, hóa đơn, tồn kho, nhập hàng hoặc tư vấn bán hàng
là nội dung legacy của đề tài khác, không phải context của AIA331 marketing.
