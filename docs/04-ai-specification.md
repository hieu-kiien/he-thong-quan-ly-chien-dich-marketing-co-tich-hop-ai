---
document_id: AIA331-DOC-04
document_type: ai-specification
project_id: AIA331-80300-MARKETING-AI
priority: P1
priority_level: HIGH
status: DERIVED
last_reviewed: 2026-08-18
---

# Đặc tả AI

## 1. AI contract

| Field | Quy ước |
|---|---|
| Prompt ID | `AI-CAM-001` |
| Version | `AI-CAM-001-v1` |
| Input | campaign brief, objective, audience, product, channel, tone |
| Output | `provider`, `prompt_version`, `ideas[]`, `needs_human_approval`, `warning` |
| Fallback | deterministic offline ideas; không gọi mạng khi không có key/config |
| Human gate | `Content` phải `APPROVED` mới được `PUBLISHED` |

## 2. System prompt

```text
Bạn là trợ lý marketing. Tạo nội dung nháp để con người duyệt. Chỉ sử dụng
thông tin được cung cấp; không bịa cam kết, số liệu hoặc chứng nhận. Nếu thiếu
dữ liệu, nói rõ. Trả về ý tưởng có hook, draft và CTA. Không tự đăng nội dung.
```

## 3. User prompt template

```text
Chiến dịch: {{campaign_brief}}
Kênh: {{channel_name}}
Giọng văn: {{tone}}
Hãy đề xuất 5 ý tưởng nội dung phù hợp kênh; mỗi ý tưởng có hook, draft và CTA.
```

## 4. Safety checklist

- Không đưa secret/PII không cần thiết vào prompt.
- Chỉ dùng metric mà user có quyền xem.
- Hiển thị warning “bản nháp” và nguồn/provider/version.
- Không coi câu chữ AI là sự thật marketing đã được xác minh.
- Có fallback khi timeout, thiếu key hoặc output sai schema.
- Lưu minh chứng prompt và phản hồi đã redaction; không lưu API key.

## 5. RAG boundary

RAG tài liệu có thể giúp AI tra cứu yêu cầu, prompt và code; RAG không được tự
thay thế truy vấn metric nghiệp vụ. Khi cần báo cáo hiệu quả, backend phải lấy
metric từ CSDL và kiểm tra quyền trước, rồi mới đưa context tối thiểu cho AI.
