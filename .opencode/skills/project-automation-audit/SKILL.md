---
name: project-automation-audit
description: Rà soát cấu hình tự động hóa của dự án (MCP, skills, subagents, hooks, lệnh tắt) và đề xuất thứ đáng thêm. Use when the user asks "cấu hình opencode/agent cho dự án này thế nào", "nên thêm automation gì", "cải thiện workflow", "set up agent", or asks what tooling would help this repo. Không dùng khi chỉ cần chạy test hay deploy.
---

# Rà soát automation của dự án

Đọc cấu hình sẵn có trước khi đề xuất thêm. Đừng đề xuất thứ đã có.

## 1. Chụp lại hiện trạng

```bash
# opencode: config + agent + command + skill
cat opencode.json 2>/dev/null || cat opencode.jsonc 2>/dev/null
ls -R .opencode 2>/dev/null
# Skill nạp tự động từ .claude/skills và .agents/skills
ls .claude/skills/*/SKILL.md .agents/skills/*/SKILL.md 2>/dev/null
# Quy tắc cho agent
head -60 AGENTS.md 2>/dev/null

# Hạ tầng dự án
cat package.json 2>/dev/null | head -40
grep -E '"(react|vue|next|express|fastapi|django|prisma|supabase)"' package.json 2>/dev/null
cat backend/requirements.txt 2>/dev/null | head -30
ls .github/workflows/ 2>/dev/null
```

## 2. Chấm điểm theo tín hiệu trong repo

| Tín hiệu trong repo | Nên có |
|---|---|
| `pytest` + `ruff`/`eslint` cấu hình | Hook tự lint/format sau khi sửa file |
| File `.env*`, `render.yaml`, khóa bí mật | Chặn sửa file nhạy cảm, quét secret khi commit |
| Thư mục `tests/` lớn | Subagent review chuyên biệt |
| SQL thô, `create_all()`, chưa có migration | Skill tạo migration có kiểm chứng |
| Frontend React + Playwright | MCP Playwright để kiểm tra giao diện thật |
| Tài liệu khối lớn cập nhật thủ công | MCP context7 để tra tài liệu thư viện còn sống |
| Nhiều người dùng chung repo | `.mcp.json` commit vào repo để đồng bộ |

## 3. Giới hạn đề xuất

**Tối đa 1–2 đề xuất cho mỗi loại.** Liệt kê mười thứ không giúp ai quyết định;
hai thứ cụ thể thì có.

Với mỗi đề xuất, nêu bằng chứng cụ thể từ repo — không nói chung chung kiểu
"project này nên có MCP".

## 4. Với dự án này

Đã có sẵn, **không** đề xuất thêm:

- 6 skill GitNexus trong `.claude/skills/` (opencode tự nạp): đã tránh được việc
  sửa mù, phân tích blast radius trước khi đổi symbol.
- CI 8 gate trong `.github/workflows/`: lint, typecheck, test, gitleaks, build.
- Skill `verify-before-claiming`: chống báo cáo sai.
- BrowserSkill (toàn cục): điều khiển trình duyệt thật.

Còn thiếu và đáng làm, theo thứ tự:

1. **Hook chặn sửa file nhạy cảm.** Repo có `.env.example` và cấu hình hạ tầng. Nên
   chặn `.env` thật trước khi commit.
2. **Skill tạo migration.** Ứng dụng dùng `create_all()` nên thêm cột ở production
   phải `ALTER TABLE` thủ công — đây là nơi dễ sai âm thầm.
3. **Subagent review bảo mật.** Đã có `explain()` của GitNexus cho taint analysis;
   subagent chuyên biệt sẽ chạy nó có hệ thống hơn.
4. **MCP Playwright.** Cần kiểm tra giao diện thật sau khi sửa frontend.

## 5. Về nguồn bên ngoài

Khi lấy cấu hình từ kho bên ngoài (plugin Anthropic, Claude Code, skill cộng đồng):

- Kiểm tra đường dẫn có khớp hệ thống đang chạy không. opencode dùng
  `.opencode/` và `~/.config/opencode/`; `.claude/` chỉ được nạp cho **skill**, không
  phải agent/hook/command.
- Skill read-only mà tự nhận "cài đặt được" thì đừng báo như đã cài.
- Đọc phần thực thi, không chỉ phần mô tả. README nói "cài gì" còn code mới là bằng
  chứng.
- Viết lại phần lấy được cho đúng hệ thống và bám bối cảnh dự án, thay vì chép
  nguyên si — bản gốc giả định stack khác.