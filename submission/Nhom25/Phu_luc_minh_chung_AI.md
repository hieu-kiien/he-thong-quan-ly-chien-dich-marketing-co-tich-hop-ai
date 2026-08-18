---
document_id: AIA331-EVIDENCE-AI
project_id: AIA331-80300-MARKETING-AI
status: SUBMISSION_CANONICAL
last_reviewed: 2026-08-18
---

# Phụ lục minh chứng sử dụng AI

## 1. Prompt đã chuẩn hóa

- `prompts/marketing/AI-CAM-001-v1-content-ideas.md`: sinh ý tưởng nội dung.
- `prompts/marketing/AI-CAM-002-v1-performance-summary.md`: thiết kế summary.
- `prompts/marketing/AI-CAM-003-v1-rag-document-qa.md`: RAG hỏi đáp tài liệu.

Tất cả prompt đều yêu cầu output nháp, nêu thiếu dữ liệu và không tự đăng.

## 2. Code minh chứng

- `marketing_management/campaigns/ai_service.py`: adapter, prompt version,
  provider/fallback và warning.
- `marketing_management/campaigns/models.py`: `Content.approve()` và
  `Content.publish()` chặn đăng khi chưa duyệt.
- `marketing_management/campaigns/tests.py`: test metric, approval, fallback và
  quyền truy cập danh sách.

## 3. Kết quả kiểm thử

```text
Ran 4 tests ... OK
System check identified no issues (0 silenced).
```

Kết quả trên là baseline local; không phải kết quả đo provider production.

## 4. Giới hạn

- Chưa có bộ dữ liệu đánh giá định lượng độ đúng/sáng tạo của AI.
- Provider ngoài chỉ có adapter tùy chọn, chưa có integration test với API thật.
- RAG tài liệu mới là thiết kế/truy hồi hỗ trợ; không dùng vector store để tính
  metric nghiệp vụ.
- Không lưu API key hoặc dữ liệu cá nhân thật trong hồ sơ.
