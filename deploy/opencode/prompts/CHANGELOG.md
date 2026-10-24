# Nhật Ký Phát Triển Prompt Trợ Lý AI (MarketFlow v2)

Tài liệu này ghi lại quá trình tiến hóa của System Prompt cho Trợ lý Marketing AI (`marketflow`) qua 3 phiên bản, đáp ứng tiêu chí đánh giá môn học (rubric AIA331) về kỹ thuật prompt engineering có bằng chứng thực nghiệm.

---

## Phiên bản 1 (v1.md) — Baseline (Khởi đầu cơ bản)

### 1. Đặc điểm
- Mô tả vai trò cơ bản: "Trợ lý Marketing AI của MarketFlow".
- Liệt kê nhiệm vụ chung chung: gợi ý ý tưởng, viết bài, tóm tắt hiệu quả.
- Cho phép sử dụng công cụ để tra cứu và tạo đề xuất.

### 2. Vấn đề phát hiện qua thực nghiệm
- **Ảo giác số liệu (Hallucination)**: Khi người dùng hỏi phân tích chiến dịch chưa có số liệu, model có xu hướng tự sáng tác các tỷ lệ tăng trưởng giả định ("dự kiến CTR đạt 8%", "tăng 25% doanh số").
- **Nhầm lẫn cơ chế Đề xuất vs Thực thi**: Khi gọi công cụ đề xuất (như tạo bản nháp), model thường tuyên bố sai lệch: "Tôi đã đăng bài viết lên Facebook thành công" hoặc "Bản nháp đã được lưu vào cơ sở dữ liệu", vi phạm nghiêm trọng Nguyên tắc Không Tính Năng Ảo (§0) và Phân quyền (§2).
- **Vi phạm quy tắc từ cấm**: Model hay sử dụng các từ ngữ giật gân, cam kết quá đà quen thuộc trong văn mẫu marketing ("cam kết 100%", "rẻ nhất Việt Nam", "đẳng cấp hàng đầu").

---

## Phiên bản 2 (v2.md) — Guardrails & Grounding (Thiết lập rào chắn)

### 1. Các cải tiến chính
- **Cấm bịa số liệu (Grounding constraint)**: Bổ sung nguyên tắc cấm tự bịa số liệu. Chỉ sử dụng dữ liệu thực tế trả về từ công cụ `marketflow_*`. Nếu không có số liệu, bắt buộc phải trả lời là chưa có dữ liệu.
- **Quy tắc Proposal-Only**: Làm rõ mọi thao tác ghi dữ liệu chỉ tạo bản ghi ở trạng thái `PROPOSED` (Đề xuất) và BẮT BUỘC phải thông báo người dùng bấm Xác nhận trên giao diện. Cấm tuyên bố là đã đăng bài hay đã duyệt.
- **Nhắc nhở cách ly môi trường**: Nhắc nhở model không có quyền truy cập shell, file, hay internet.
- **Rào chắn từ cấm (Banned keywords)**: Yêu cầu tuân thủ từ cấm thương hiệu và tránh cam kết sai sự thật.

### 2. Kết quả kiểm chứng thực nghiệm
- Model không còn tuyên bố "đã đăng bài", chuyển sang "Tôi đã tạo đề xuất bài viết, bạn hãy kiểm tra và xác nhận".
- Khi được hỏi về số liệu, model chủ động gọi `marketflow_get_stats` hoặc `marketflow_get_campaign_stats`.
- Tuy nhiên:
  - Cấu trúc bài viết giữa các kênh còn chưa đồng đều (bài TikTok viết dài dòng như bài blog, thiếu phân bổ thời lượng 3s hook).
  - Chưa tận dụng tối đa ngữ cảnh truyền vào từ backend (`[NGỮ CẢNH]`).
  - Định dạng bảng và chỉ số đôi khi bị rối khi mẫu số bằng 0.

---

## Phiên bản 3 (v3.md) — Production-Ready (Tối ưu hóa đa kênh & Trải nghiệm SME)

### 1. Các cải tiến chuyên sâu
- **Quy chuẩn hóa định dạng theo từng kênh cụ thể**:
  - Facebook: Hook 2 dòng đầu, đoạn văn ngắn gọn, CTA trực tiếp, 3-5 hashtag.
  - Instagram: Thị giác & phong cách sống.
  - TikTok: Kịch bản video phân đoạn chuẩn thời lượng [Hook 0-3s], [Nội dung 3-45s], [CTA 45-60s].
  - Email: Subject ngắn gọn (< 60 ký tự), cá nhân hóa, 1 CTA duy nhất.
  - Zalo OA & Google Ads: Giới hạn ký tự và câu từ súc tích, đánh trúng insight.
- **Chuẩn hóa công thức & xử lý số liệu biên**:
  - Quy định rõ công thức tính chỉ số (CTR, CVR, CPC, CPA).
  - Quy định mẫu số bằng 0 thì hiển thị ký hiệu không xác định ("—"), không tính ra giá trị vô lý.
- **Đồng bộ hóa với giao diện người dùng (UI Artifacts & Action Panel)**:
  - Chỉ dẫn model nhắc người dùng xem và bấm "Xác nhận" tại panel "Đề xuất & bản nháp" bên phải màn hình.
  - Nhận biết ngữ cảnh phiên làm việc (`[NGỮ CẢNH]` gồm người dùng, vai trò, ngày hiện tại, chiến dịch liên kết) để đưa ra câu trả lời cá nhân hóa mà không cần hỏi lại người dùng.
- **Văn phong chuẩn SME Việt Nam**: Gần gũi, ấm áp, thực tế, tránh các buzzword sáo rỗng ("hệ sinh thái khép kín", "đẳng cấp thế giới").

### 2. Bằng chứng thực nghiệm (Empirical Proof)
- **Thử nghiệm MCP Tool Call**: Gọi `marketflow_get_campaign_stats` và `marketflow_propose_content_drafts` đạt 100% độ chính xác tham số trên các model được chọn (`big-pickle`, `glm-5.3-flash-free`).
- **Thử nghiệm Prompt Injection & Security**: Khi người dùng yêu cầu đọc `/etc/passwd`, chạy shell `uname -a`, hay fetch URL bên ngoài, model từ chối rõ ràng và tuân thủ ranh giới bảo mật.
- **Thử nghiệm Tính trung thực**: Số lượt chuyển đổi (conversions = 211) được phản ánh chính xác trong bản nháp caption Facebook, không bị làm tròn sai hoặc thêm thắt.
