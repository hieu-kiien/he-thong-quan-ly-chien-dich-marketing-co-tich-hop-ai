# Mục Lục Tài Liệu Kỹ Thuật — MarketFlow v2

> Dự án môn học: Ứng dụng trí tuệ nhân tạo (AIA331)  
> Đề tài: Hệ thống quản lý chiến dịch marketing có tích hợp AI (Mã số: 80300)  
> Phiên bản hệ thống: MarketFlow v2 (Clean Rebuild)  

---

## 1. Danh Mục Tài Liệu Chính

| Tài liệu | Giai đoạn đánh giá | Nội dung trọng tâm |
|---|---|---|
| [**REQUIREMENTS_AND_DESIGN.md**](REQUIREMENTS_AND_DESIGN.md) | **Bài kiểm tra thường xuyên 1 (KT1)** | Phân tích bài toán quản lý tiếp thị SME Việt Nam; xác định 2 vai trò người dùng (`MANAGER`, `MARKETER`); bảng yêu cầu chức năng (Input/Process/Output); yêu cầu phi chức năng; sơ đồ Use Case; thiết kế CSDL (ERD 14 bảng, ràng buộc toàn vẹn); sơ đồ kiến trúc phân tầng; luồng dữ liệu Trợ lý AI (Sequence Diagram) và cấu trúc Prompt ban đầu. |
| [**AI_ASSISTANT.md**](AI_ASSISTANT.md) | **Bài kiểm tra thường xuyên 3 (KT3)** | Kiến trúc dịch vụ `ai-runner` nội bộ; tích hợp OpenCode Zen qua OpenCode CLI; danh mục công cụ MCP (Read tools vs Propose tools); cơ chế xác thực Run-Token JWT; luồng sự kiện SSE; tiến hóa prompt qua 3 phiên bản (v1 → v2 → v3) có đo lường thực nghiệm; cơ chế xử lý lỗi (Timeout, Rate Limit, Empty); kiểm soát quyền truy cập dữ liệu và quy trình con người duyệt đề xuất (Human-in-the-Loop). |
| [**AI_ETHICS_AND_PRIVACY.md**](AI_ETHICS_AND_PRIVACY.md) | **Đạo đức & Quyền riêng tư AI (Rubric Chung)** | Bảo vệ khóa API và bí mật hệ thống; phạm vi dữ liệu gửi tới LLM (chỉ dữ liệu kinh doanh công khai theo quyền, cấm gửi PII); công bố minh bạch điều khoản huấn luyện của mô hình miễn phí; các biện pháp kiểm soát và chống ảo giác số liệu (Grounding); bằng chứng thực nghiệm phòng thủ các kịch bản tấn công Prompt Injection trên máy chủ VPS. |
| [**TESTING.md**](TESTING.md) | **Kiểm thử Hệ thống (Rubric KT2 & KT3)** | Hướng dẫn thực thi từng bộ kiểm thử (Backend Pytest, AI Runner Pytest, Frontend TypeScript strict typecheck, ESLint, Vite Production Build, và kịch bản đánh giá Prompt định lượng); số liệu đo lường thực tế; danh mục chi tiết các ca kiểm thử theo từng module nghiệp vụ bao gồm trường hợp bình thường (Normal), lỗi (Error) và biên (Boundary). |
| [**AI_IN_SDLC.md**](AI_IN_SDLC.md) | **Minh chứng Ứng dụng AI trong SDLC** | Minh chứng ứng dụng AI xuyên suốt vòng đời phát triển: rà soát hiện trạng v1 bằng AI phát hiện 22 tính năng ảo và lỗ hổng bảo mật (KT1); lập trình đa tác nhân bám sát Design Contract (KT2); đo đạc bộ nhớ RSS và benchmark 8 mô hình miễn phí trên VPS thực tế (KT3); các điểm con người và Orchestrator đã can thiệp, kiểm chứng và hiệu chỉnh chất lượng mã nguồn. |
| [**DEPLOYMENT-VPS.md**](DEPLOYMENT-VPS.md) | **Triển khai & Vận hành Production** | Hướng dẫn triển khai thực tế trên máy chủ VPS Ubuntu 24.04 LTS qua Cloudflare Tunnel; cấu hình các dịch vụ hệ thống systemd (`marketflow-api`, `marketflow-ai-runner`, `nginx`, `postgresql`, `cloudflared`); phân quyền thư mục và giới hạn bộ nhớ an toàn. |

---

## 2. Tài Liệu Thiết Kế Nền Tảng (Read-Only Specs)

Các tài liệu nghiên cứu và hợp đồng kỹ thuật được thiết lập trước khi lập trình:
- [**docs/rebuild/CONTRACT.md**](rebuild/CONTRACT.md): Nguồn chân lý chung cho toàn bộ dự án — Rule 0 chống tính năng ảo, danh mục bảng CSDL, quy ước API RESTful, hình dạng response chuẩn (Phụ lục A), kết quả spike thực nghiệm (Phụ lục B) và chi tiết các đề xuất AI (Phụ lục C).
- [**docs/rebuild/P0_SPIKE_REPORT.md**](rebuild/P0_SPIKE_REPORT.md): Báo cáo thực nghiệm P0 trên máy chủ VPS — đo đạc mức tiêu thụ RAM RSS (~490MB), khảo sát 8 mô hình miễn phí của OpenCode Zen, mẫu khóa phân quyền agent và kiểm thử tấn công Injection.
- [**docs/rebuild/BACKEND_NOTES.md**](rebuild/BACKEND_NOTES.md): Ghi chú triển khai Backend — cấu trúc các tầng kiến trúc, hướng dẫn chạy migration Alembic và nạp dữ liệu mẫu.

---

## 3. Mã Nguồn Cũ & Nhật Ký Lịch Sử (Archive)

Mã nguồn phiên bản v1 cùng các báo cáo thử nghiệm cũ được lưu trữ an toàn trong lịch sử Git thông qua tag:
```bash
git show legacy-v1:<đường_dẫn_tệp>
```
Toàn bộ mã nguồn trên nhánh `rebuild/v2` là mã nguồn được xây dựng lại sạch sẽ, trung thực và tuân thủ các yêu cầu kỹ thuật của đề tài.
