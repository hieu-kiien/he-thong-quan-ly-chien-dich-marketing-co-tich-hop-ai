---
document_id: AIA331-DOC-02
document_type: architecture-and-code-status
project_id: AIA331-80300-MARKETING-AI
priority: P1
priority_level: HIGH
status: DERIVED
sources: [../marketing_management/README.md, ../marketing_management/campaigns, 01-requirements-summary.md]
last_reviewed: 2026-08-24
---

# Kiến trúc và trạng thái code

## 1. Kiến trúc baseline

```text
Browser
  -> Django URL/View + authentication/RBAC
  -> Forms/Services
  -> Django ORM / SQLite
  -> Campaign, Channel, Content, Metric
  -> AI adapter (prompt version + provider/fallback + schema validation)
  -> human approval gate
```

## 2. Ma trận code

| Thành phần | Đường dẫn | Trạng thái | Bằng chứng |
|---|---|---|---|
| Project config | `marketing_management/config/` | IMPLEMENTED_BASELINE | settings, urls, ASGI/WSGI |
| Campaign model | `campaigns/models.py` | IMPLEMENTED_BASELINE | validation, performance_summary |
| Channel model | `campaigns/models.py` | IMPLEMENTED_BASELINE | choices, active flag |
| Content approval | `campaigns/models.py`, `views.py` | IMPLEMENTED_BASELINE | `approve()`/`reject()`/`publish()` + manager-only routes + test |
| Metric validation | `campaigns/models.py` | IMPLEMENTED_BASELINE | clean + unique constraint + test |
| CRUD campaign | `campaigns/views.py`, `forms.py`, `urls.py` | IMPLEMENTED_BASELINE | list/create/detail/update + POST delete + test |
| CRUD channel | `campaigns/views.py`, `forms.py`, `urls.py` | IMPLEMENTED_BASELINE | list/create/update + manager-only delete + ProtectedError handling |
| CRUD content | `campaigns/views.py`, `forms.py`, `urls.py` | IMPLEMENTED_BASELINE | create/detail/update/delete; sửa nội dung buộc duyệt lại |
| CRUD metric | `campaigns/views.py`, `forms.py`, `urls.py` | IMPLEMENTED_BASELINE | create/detail/update/delete + full_clean + unique constraint |
| Search/filter/sort | `campaigns/views.py` | IMPLEMENTED_BASELINE | keyword/status/channel/date range/order + invalid filter message |
| Dashboard KPI | `campaigns/views.py`, `templates/campaigns/dashboard.html` | IMPLEMENTED_BASELINE | counts, pending review, clicks, cost từ aggregate `Metric` |
| AI prompt/adapter | `campaigns/ai_service.py` | IMPLEMENTED_BASELINE | `AI-CAM-001-v1`, fallback, output contract validation |
| Provider integration | `ai_service.py` | IMPLEMENTED_BASELINE (optional) | OpenAI-compatible branch, invalid output chuyển fallback; cần key để demo provider thật |
| AI performance report | — | PROPOSED | prompt và thiết kế có; UI summary đầy đủ là giai đoạn sau |

## 3. Không được nhầm trạng thái

Baseline hiện chứng minh model, CRUD bốn nhóm dữ liệu, tìm kiếm/lọc/sắp xếp,
dashboard KPI, workflow duyệt, metric aggregation, permission guard và fallback
AI. Provider thật vẫn cần API key và integration test riêng; AI performance
summary theo campaign và RAG nghiệp vụ vẫn là mở rộng, không được ghi thành tính
năng đã triển khai.
