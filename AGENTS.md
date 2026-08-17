# Quy ước dự án quản lý bán hàng

## Phạm vi

Thư mục này là nguồn làm việc chính cho dự án `BAI03-SALES-AI`, một hệ thống
quản lý bán hàng bằng Django có định hướng tích hợp AI. Không trộn nội dung của
dự án `BAOHANHAI` ở file `KT1_PHAN_TICH_THIET_KE.md` vào dự án này.

## Thứ tự ưu tiên nguồn

1. `project.md` và `informember.md`: yêu cầu gốc và thông tin nhóm.
2. Mã nguồn đã kiểm tra trong `Code QLBH/` và `sales_management/`.
3. Tài liệu phân tích/kiến trúc được suy ra từ hai nguồn trên.
4. DOCX đã sinh, prompt, template và tài liệu tham khảo.

Tài liệu phải ghi rõ trạng thái `CANONICAL`, `IMPLEMENTED`, `DERIVED`,
`PROPOSED`, `TEMPLATE`, `REFERENCE`, `LEGACY` hoặc `OPEN`. Không được trình
bày một yêu cầu như thể đã được triển khai nếu chưa có mã nguồn và kiểm thử
tương ứng.

## Quy tắc đọc và cập nhật

- Khi bắt đầu tra cứu, đọc `docs/README.md`, sau đó `docs/00-project-context.md`.
- Dùng các ID ổn định như `FR-001`, `NFR-001`, `AI-001` và `BR-001` khi liên kết
  yêu cầu, thiết kế, mã nguồn và kiểm thử.
- Dùng liên kết tương đối trong Markdown; không dùng đường dẫn ổ đĩa cá nhân
  hoặc đường dẫn phụ thuộc máy người viết trong tài liệu mới.
- Loại khỏi chỉ mục các thư mục sinh ra như `.venv/`, `venv/`, `__pycache__/`,
  file cơ sở dữ liệu local, cache và file chứa bí mật.
- Không đưa API key, mật khẩu hoặc nội dung `.env` vào tài liệu. Chỉ tham chiếu
  `.env.example`.

## Hai nhánh mã nguồn cần phân biệt

- `Code QLBH/`: skeleton kiến trúc modular; nhiều model, view, URL và test còn
  là khung trống.
- `sales_management/`: nhánh hiện thực một phần; model nghiệp vụ và CRUD
  danh mục có nội dung, nhưng phần lớn URL/view/test và toàn bộ tích hợp AI
  chưa hoàn chỉnh.

`QLBH demo/` ở cấp `Codes/` là bản demo cũ, chỉ dùng làm tài liệu lịch sử và
không phải nguồn triển khai chuẩn.

## Kiểm chứng trước khi bàn giao

Khi thay đổi mã nguồn hoặc tuyên bố tính năng đã hoàn thành, kiểm tra tối thiểu
`python manage.py check`, test liên quan và đối chiếu với ma trận trong
`docs/02-architecture-and-code-status.md`. Nếu môi trường chưa cài dependency,
ghi rõ đó là kiểm tra tĩnh, không gọi là test đã đạt.

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **he-thong-quan-ly-ban-hang-co-tich-hop-ai** (1261 symbols, 1419 relationships, 11 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> Index stale? Run `node .gitnexus/run.cjs analyze` from the project root — it auto-selects an available runner. No `.gitnexus/run.cjs` yet? `npx gitnexus analyze` (npm 11 crash → `npm i -g gitnexus`; #1939).

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows. For regression review, compare against the default branch: `detect_changes({scope: "compare", base_ref: "main"})`.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `rename` which understands the call graph.
- NEVER commit changes without running `detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/he-thong-quan-ly-ban-hang-co-tich-hop-ai/context` | Codebase overview, check index freshness |
| `gitnexus://repo/he-thong-quan-ly-ban-hang-co-tich-hop-ai/clusters` | All functional areas |
| `gitnexus://repo/he-thong-quan-ly-ban-hang-co-tich-hop-ai/processes` | All execution flows |
| `gitnexus://repo/he-thong-quan-ly-ban-hang-co-tich-hop-ai/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
