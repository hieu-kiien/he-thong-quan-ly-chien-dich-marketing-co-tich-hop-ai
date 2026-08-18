---
document_id: AIA331-DOC-02
document_type: architecture-and-code-status
project_id: AIA331-80300-MARKETING-AI
status: DERIVED
sources: [../marketing_management/README.md, ../marketing_management/campaigns, 01-requirements-summary.md]
last_reviewed: 2026-08-18
---

# Kiến trúc và trạng thái code

## 1. Kiến trúc baseline

```text
Browser
  -> Django URL/View + authentication/RBAC
  -> Forms/Services
  -> Django ORM / SQLite
  -> Campaign, Channel, Content, Metric
  -> AI adapter (prompt version + provider/fallback)
```

## 2. Ma trận code

| Thành phần | Đường dẫn | Trạng thái | Bằng chứng |
|---|---|---|---|
| Project config | `marketing_management/config/` | IMPLEMENTED_BASELINE | settings, urls, ASGI/WSGI |
| Campaign model | `campaigns/models.py` | IMPLEMENTED_BASELINE | validation, performance_summary |
| Channel model | `campaigns/models.py` | IMPLEMENTED_BASELINE | choices, active flag |
| Content approval | `campaigns/models.py` | IMPLEMENTED_BASELINE | `approve()`/`publish()` + test |
| Metric validation | `campaigns/models.py` | IMPLEMENTED_BASELINE | clean + unique constraint + test |
| CRUD campaign | `campaigns/views.py`, `forms.py` | IMPLEMENTED_BASELINE | list/create/update/detail + test |
| Search/filter | `campaigns/views.py` | IMPLEMENTED_BASELINE | query `q`/`status` |
| AI prompt/adapter | `campaigns/ai_service.py` | IMPLEMENTED_BASELINE | `AI-CAM-001-v1`, fallback |
| Provider integration | `ai_service.py` | PROPOSED/OPTIONAL | OpenAI-compatible branch requires config/integration test |
| AI report UI | — | PROPOSED | chưa có endpoint/màn hình |

## 3. Không được nhầm trạng thái

Baseline hiện chứng minh model, workflow duyệt, metric aggregation và fallback
AI. Chưa được tuyên bố đã có dashboard phân tích nâng cao, kết nối provider thật,
RAG nghiệp vụ hoặc triển khai production.
