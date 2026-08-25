---
document_id: AIA331-SKILL-INDEX
project_id: AIA331-80300-MARKETING-AI
status: CANONICAL_DERIVED
---

# Skill của dự án

Thư mục này là nơi lưu các hướng dẫn/skill phục vụ riêng cho repo. Mỗi skill
đặt trong một thư mục con có `README.md` hoặc `SKILL.md`, kèm nguồn, phiên bản,
phạm vi và lệnh kiểm chứng. Không đặt `.venv`, cache, API key hoặc dữ liệu thật
vào đây.

## Ưu tiên cho giai đoạn web tiếp theo

| Skill | Mục đích | Trạng thái |
|---|---|---|
| `webapp-testing` | Kiểm thử Django local bằng Playwright, DOM và screenshot | [anthropics/skills](https://www.skills.sh/anthropics/skills/webapp-testing) |
| `python-testing` | Chuẩn hóa test hành vi/contract cho Django và Python | [ahgraber/skills](https://www.skills.sh/ahgraber/skills/python-testing) |
| `frontend-ui-engineering` | Quy tắc UI hiện có trong môi trường Codex | Có sẵn ngoài repo |
| `browser-testing-with-devtools` | Kiểm tra runtime trình duyệt khi MCP được cấu hình | Có sẵn ngoài repo |

## Cách thêm skill

Không cài trực tiếp vào mã nguồn ứng dụng. Ghi nguồn và mục đích vào README của
skill trước, sau đó mới cài bằng lệnh được tài liệu hóa. Ví dụ:

```powershell
npx skills add https://github.com/anthropics/skills --skill webapp-testing
npx skills add https://github.com/ahgraber/skills --skill python-testing
```

Các skill bên ngoài chỉ là công cụ hỗ trợ; kết quả của chúng vẫn phải được
kiểm chứng bằng test, tài liệu canonical và nguồn P0 trong `source-materials/`.
