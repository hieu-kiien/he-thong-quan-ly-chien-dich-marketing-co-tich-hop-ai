---
document_id: AIA331-DOC-09
document_type: assessment-checklist
project_id: AIA331-80300-MARKETING-AI
priority: P1
priority_level: HIGH
status: CANONICAL_DERIVED
source: ../source-materials/BÀI KIỂM TRA.png
last_reviewed: 2026-08-25
---

# Checklist 10 tiêu chí bài kiểm tra

Đây là bản chép có cấu trúc từ ảnh `source-materials/BÀI KIỂM TRA.png`. Checklist
10 tiêu chí bài kiểm tra dùng để đánh giá dự án marketing theo đúng nguồn P0;
nó dùng để kiểm tra độ đầy đủ của hồ sơ, không phải điểm số và không được dùng
để tự khẳng định bài đã đạt nếu chưa có bằng chứng tương ứng.

| ID | Tiêu chí nguồn | Bằng chứng trong dự án |
|---|---|---|
| KT-01 | Phân tích đúng bài toán quản lý: bối cảnh, người dùng, dữ liệu, quy trình nghiệp vụ và vấn đề cần giải quyết | `project.md`, `docs/00-project-context.md`, báo cáo mục 2 |
| KT-02 | Xác định đầy đủ yêu cầu chức năng, có đầu vào, xử lý và đầu ra | `project.md`, `docs/01-requirements-summary.md`, báo cáo mục 3 |
| KT-03 | Xác định yêu cầu phi chức năng: bảo mật, hiệu năng, khả dụng, sao lưu, phân quyền và trải nghiệm | `docs/01-requirements-summary.md`, `docs/12-operations-and-backup.md`, báo cáo mục 4 |
| KT-04 | Thiết kế actor và use case, có sơ đồ hoặc mô tả tương đương | `docs/03-business-flows.md`, `docs/diagrams/usecase.png`, báo cáo mục 5 |
| KT-05 | Thiết kế cơ sở dữ liệu: ERD, bảng, khóa và ràng buộc | `docs/diagrams/erd.png`, `marketing_management/campaigns/models.py`, báo cáo mục 6 |
| KT-06 | Thiết kế kiến trúc frontend, backend, database, AI service và luồng dữ liệu | `docs/diagrams/architecture.png`, `docs/02-architecture-and-code-status.md`, báo cáo mục 7 |
| KT-07 | Xác định vị trí ứng dụng AI hợp lý, gắn với dữ liệu và nhu cầu thực tế | `docs/04-ai-specification.md`, báo cáo mục 8 |
| KT-08 | Thiết kế prompt và luồng gọi AI: system prompt, user prompt, input/output và giới hạn | `prompts/marketing/`, `docs/04-ai-specification.md`, báo cáo mục 9 |
| KT-09 | Có minh chứng sử dụng AI, phản hồi, nhận xét kiểm chứng và chỉnh sửa kết quả | `submission/Nhom25/Phu_luc_minh_chung_AI.md`, `evidence/ai/`, báo cáo mục 10 |
| KT-10 | Tài liệu phân tích thiết kế rõ ràng, có cấu trúc và kế hoạch triển khai tiếp theo | `submission/Nhom25/Bao_cao_du_an_marketing_ai.tex`, `.pdf`, `docs/diagrams/metric-chart.png`, báo cáo mục 12 |

## Quality gate bổ sung — in ấn

Không phải tiêu chí nguồn thứ 11, nhưng hồ sơ phải vượt kiểm tra print-safe:
PDF A4 đọc được ở grayscale, màu không phải tín hiệu duy nhất, biểu đồ có nhãn
và sơ đồ vẫn phân biệt được các quan hệ khi in đen trắng.

## Checklist Bài kiểm tra thường xuyên 2

Mười tiêu chí triển khai của Bài 2 được giữ thành ma trận riêng để không trộn
với 10 tiêu chí phân tích thiết kế của Bài 1: [`docs/13-bai-2-implementation.md`](13-bai-2-implementation.md).

## Quy tắc hoàn thành

- Mỗi tiêu chí phải trỏ tới ít nhất một file hoặc test có thật.
- Nội dung chưa có code/test phải giữ trạng thái `PROPOSED` hoặc `OPEN`.
- Hai ảnh nguồn P0 / CRITICAL vẫn là căn cứ cuối cùng nếu bản chép có sai khác.
