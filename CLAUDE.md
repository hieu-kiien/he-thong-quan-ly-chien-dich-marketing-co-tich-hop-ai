# AIA331-80300-MARKETING-AI — hướng dẫn AI trong repo

- Đề tài canonical: **Hệ thống quản lý chiến dịch marketing có tích hợp AI**.
- Đọc `AGENTS.md`, `project.md`, `docs/README.md` trước khi sửa.
- Baseline code: `marketing_management/`; legacy sales không được dùng làm
  yêu cầu hoặc bằng chứng marketing.
- Chỉ hai ảnh trong `source-materials/` là `P0 / CRITICAL`; xem
  `docs/10-priority-policy.md` để biết các mức P1/P2/P3.
- Khi sửa logic, chạy test; khi tuyên bố hoàn thành phải có bằng chứng lệnh chạy.
- AI output phải qua kiểm tra và human approval; không commit secret.
- Tra cứu tài liệu bằng `python tools/rag_index.py search ...`; GitNexus chỉ dùng
  cho code graph. Xem `docs/11-rag-implementation.md` và không commit `.rag/`.

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **he-thong-quan-ly-chien-dich-marketing-co-tich-hop-ai** (314 symbols, 447 relationships, 18 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

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
| `gitnexus://repo/he-thong-quan-ly-chien-dich-marketing-co-tich-hop-ai/context` | Codebase overview, check index freshness |
| `gitnexus://repo/he-thong-quan-ly-chien-dich-marketing-co-tich-hop-ai/clusters` | All functional areas |
| `gitnexus://repo/he-thong-quan-ly-chien-dich-marketing-co-tich-hop-ai/processes` | All execution flows |
| `gitnexus://repo/he-thong-quan-ly-chien-dich-marketing-co-tich-hop-ai/process/{name}` | Step-by-step execution trace |

<!-- gitnexus:end -->
