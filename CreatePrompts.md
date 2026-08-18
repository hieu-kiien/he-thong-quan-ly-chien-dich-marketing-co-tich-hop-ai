---
document_id: AIA331-PROMPT-GUIDE
project_id: AIA331-80300-MARKETING-AI
status: CANONICAL_DERIVED
---

# Hướng dẫn tạo prompt cho dự án Marketing AI

Mọi prompt canonical đặt trong `prompts/marketing/` và phải bám `project.md`.
Prompt cần có mục tiêu, context, input, task, constraints, output schema, phiên
bản và cách kiểm chứng. Không dùng đường dẫn máy cá nhân hoặc secret.

## Chuỗi prompt khuyến nghị

```text
phân tích yêu cầu -> thiết kế actor/ERD -> sinh CRUD -> thiết kế AI contract
-> sinh test -> review output -> viết tài liệu/báo cáo
```

## Quy tắc prompt AI nghiệp vụ

- Định danh bằng `AI-*` và version `vN`.
- System prompt nói rõ AI chỉ tạo bản nháp, không bịa claim và không tự đăng.
- User prompt truyền campaign brief, objective, audience, product, channel, tone.
- Output phải có schema; nếu thiếu dữ liệu phải trả về warning.
- Ghi lại prompt, phản hồi, người kiểm tra và kết quả; redaction thông tin nhạy cảm.

## Các kỹ thuật nên thể hiện

Zero-shot cho phân tích; few-shot cho format nội dung; self-consistency cho lựa
chọn ERD/prompt; RAG cho hỏi đáp tài liệu; test/refinement cho đánh giá caption
và báo cáo. Không coi câu trả lời AI là bằng chứng nếu chưa đối chiếu nguồn.
