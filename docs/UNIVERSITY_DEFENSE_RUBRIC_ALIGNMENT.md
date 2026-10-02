# Bản nháp đối chiếu đồ án và chuẩn bị bảo vệ

**Trạng thái:** tài liệu làm việc nội bộ; chưa có rubric chính thức của trường để đối chiếu. Không xem bảng dưới đây là xác nhận đạt chuẩn hoặc là nội dung đã được giảng viên duyệt.

**Baseline mã nguồn:** `main` tại `b99ac876a06993edfb5a88d866c22080434e7372` (2026-09-29). Bản PDF/LaTeX V8/V9 là snapshot đã lưu; xem [mục lục tài liệu](README.md) và README trong thư mục từng phiên bản.

## Cách dùng tài liệu này

Trước khi đưa một nhận định vào báo cáo hoặc bài bảo vệ:

1. Gắn nhãn nhận định là **đã hiện thực**, **đã kiểm thử**, **đã đo**, **đề xuất** hoặc **chưa xác nhận**.
2. Mở đúng mã nguồn, test, log CI hoặc dữ liệu pilot để xác minh. Tài liệu này không thay thế bằng chứng gốc.
3. Nêu phạm vi, commit, môi trường và mẫu số. Không ngoại suy benchmark nhỏ thành bảo đảm tổng quát.
4. Chỉ đối chiếu với rubric sau khi có bản chính thức; lưu tên tiêu chí và trang/mục tương ứng.

## Bản đồ nội dung và bằng chứng hiện có

| Chủ đề | Có thể trình bày trong phạm vi hiện tại | Bằng chứng chuẩn | Giới hạn cần nói rõ |
|---|---|---|---|
| Bài toán và phạm vi sản phẩm | Prototype điều phối campaign có task, ngân sách/KPI mục tiêu, nội dung và bước duyệt; hướng sản phẩm là workspace cho agency. | [README](../README.md), [roadmap](ROADMAP.md), mã nguồn và test tương ứng. | Chưa có bằng chứng pilot xác nhận mức tiết kiệm thời gian, mức độ phù hợp thị trường hoặc tăng hiệu quả marketing. |
| Kiến trúc | Mô tả các thành phần đúng như baseline đang triển khai. | [Architecture](ARCHITECTURE.md), config và source hiện hành. | Không dùng sơ đồ/tuyên bố trong báo cáo cũ nếu chưa đối chiếu lại với code. Không gọi cấu hình demo là production-ready. |
| Lên lịch/phát hành | Scheduler cập nhật trạng thái nội bộ; `PUBLISHED` hiện không chứng minh nội dung đã được gửi tới nhà cung cấp bên ngoài. | [Roadmap](ROADMAP.md), backend scheduler/publish flow. | Chưa có đường gửi email/provider được xác nhận trong baseline này. |
| AI | Có benchmark tự động cho schema, grounding, failover và đường chẩn đoán xác định theo phạm vi ghi trong báo cáo. | [AI evaluation report](AI_EVALUATION_REPORT.md) và generator. | 0/40 vi phạm chỉ áp dụng cho 40 case đã chạy; latency SQLite không phải latency LLM qua mạng. Không tuyên bố “zero hallucination”. |
| Kiểm thử và CI | Có thể báo cáo kết quả của đúng run/commit được ghi trong [Testing](TESTING.md). | CI workflow, run URL, artifact và TESTING.md. | CI xanh không đồng nghĩa đạt rubric, bảo mật toàn diện, UX tốt hay sẵn sàng vận hành production. Advisory dependency phải được nêu. |
| Bảo vệ dữ liệu và vận hành | Trình bày cấu hình/deployment cùng các giới hạn đã biết. | [Cloudflare deployment](../cloudflare/README.md), config và workflow. | Snapshot toàn file SQLite lên R2 sau mỗi write là rủi ro cần giải quyết trước khi dùng dữ liệu khách hàng thật. |

## Câu hỏi nên chuẩn bị cho phần bảo vệ

Các mục sau là câu hỏi gợi ý, không phải câu trả lời đã được kiểm chứng:

1. **Vấn đề người dùng:** agency hiện giải quyết workflow này ra sao? Cần phỏng vấn/quan sát người dùng và nêu đặc điểm mẫu trước khi kết luận về nhu cầu.
2. **Thiết kế hệ thống:** vì sao chọn các thành phần hiện tại, ranh giới module nằm ở đâu, và trade-off nào được chấp nhận? Dùng sơ đồ kiến trúc đã đối chiếu với code.
3. **AI và độ tin cậy:** AI nhận dữ liệu gì, con người duyệt gì, fallback xử lý ra sao? Chỉ nêu hành vi có thể chỉ ra trong source/test; tách dữ liệu đo lường khỏi nội dung do model sinh.
4. **Phân quyền và ranh giới workspace:** kiểm tra ma trận vai trò và truy cập theo bản ghi bằng test hiện tại; không khẳng định bảo mật tuyệt đối từ một nhóm test.
5. **Đo lường chất lượng:** giải thích cách chọn case, mẫu số, môi trường và giới hạn của test/benchmark; tách kết quả kỹ thuật với kết quả người dùng.
6. **Sẵn sàng triển khai:** nêu chính xác chức năng nào đi qua dịch vụ bên ngoài, cách backup/restore, giám sát và rollback. Phân biệt staging/demo với production.

## Việc cần bổ sung trước khi biến thành tài liệu nộp

- Nhận rubric chính thức và ánh xạ từng tiêu chí tới chương, hình, source, test hoặc kết quả đo.
- Đối chiếu lại từng sơ đồ, tên công nghệ, vai trò và con số trong báo cáo với commit dùng để nộp.
- Lưu run CI cụ thể và artifact; ghi rõ mục nào không tái lập được.
- Bổ sung evidence người dùng/pilot nếu báo cáo đưa ra kết luận về tính hữu ích hoặc hiệu quả.
- Tạo bản revision mới cho LaTeX/PDF nếu cần; giữ nguyên bản V8/V9 đã nộp.
