<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **he-thong-quan-ly-chien-dich-marketing-co-tich-hop-ai** (1596 symbols, 2889 relationships, 105 execution flows).

> Index stale? Run `node .gitnexus/run.cjs analyze --index-only` from the project root — it auto-selects an available runner. No `.gitnexus/run.cjs` yet? Bootstrap with `npx`, `bunx`, or `pnpm dlx` — e.g. `bunx gitnexus@latest analyze` (npm 11 npx crash; #1939).

## Always Do

- **MUST run impact before editing.** Use `impact({target: "symbolName", direction: "upstream"})` or `node .gitnexus/run.cjs impact "symbolName" --direction upstream --repo .`; report callers, processes, and risk. Never substitute grep for graph analysis.
- **MUST analyze graph changes before committing.** Use `detect_changes({scope: "all"})` (MCP) or `node .gitnexus/run.cjs detect-changes --scope all --repo .` (CLI fallback). `partial: true` or `truncated: true` is not a clean check — a zero means unseen, not unaffected; re-run it. For regression review: `detect_changes({scope: "compare", base_ref: "main"})` or `node .gitnexus/run.cjs detect-changes --scope compare --base-ref "main" --repo .`.
- MUST warn on HIGH/CRITICAL `risk` pre-edit; never use `riskSharedAxes` to waive a HIGH/CRITICAL `risk` warning. Compare File/symbol: MCP File omits axes; Graph-RAG expands File.
- **MUST treat `risk: UNKNOWN` as unresolved, not as low.** An empty caller set is not evidence the symbol is unused — it can also mean the callers are not resolvable by the index (plain-object property access, dynamic dispatch, cross-language calls). `impact` pairs `UNKNOWN` with a `riskNote` saying so. Confirm with a text search before treating the symbol as safe to change or delete; do not proceed on the strength of a zero.
- **MUST use `query({search_query: "concept"})` for concepts/flows, `context({name: "symbolName"})` for a named symbol, or `impact` for blast radius, on read-only callers, dependencies, imports, or execution flow.** Graph first; text search only for empty/`UNKNOWN`/literals.
- For security review, `explain({target: "fileOrSymbol"})` lists taint findings (source→sink flows; needs `analyze --pdg`).

## Never Do

- NEVER edit a function, class, or method before MCP/CLI impact analysis.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis, and never read `UNKNOWN` as an all-clear — it means the walk could not answer, which is the one verdict that requires confirming by other means.
- NEVER rename symbols with find-and-replace — use `rename` which understands the call graph.
- NEVER commit before MCP/CLI graph change analysis.

## Resources

| Resource | Use for |
| --- | --- |
| `gitnexus://repo/he-thong-quan-ly-chien-dich-marketing-co-tich-hop-ai/context` | Codebase overview, check index freshness |
| `gitnexus://repo/he-thong-quan-ly-chien-dich-marketing-co-tich-hop-ai/clusters` | All functional areas |
| `gitnexus://repo/he-thong-quan-ly-chien-dich-marketing-co-tich-hop-ai/processes` | All execution flows |
| `gitnexus://repo/he-thong-quan-ly-chien-dich-marketing-co-tich-hop-ai/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
| --- | --- |
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->

# Hạ tầng VPS & Triển khai Production

- **Bảng điều khiển quản lý VPS (Start / Stop / Reboot / Console):** `https://vps.clooud.codes/servers/639a6009`
- **Tên miền Production (qua Cloudflare Tunnel):** `https://marketing.kienhieu.id.vn/`
- **Kết nối SSH:**
  - Host: `root@vn-hn.cloudcode.io.vn` (IP NAT: `27.76.200.123`)
  - Port: `30513`
  - SSH Private Key: `$HOME\.ssh\marketflow_vps_ed25519`
  - Lệnh kết nối: `ssh -i "$HOME\.ssh\marketflow_vps_ed25519" -p 30513 root@vn-hn.cloudcode.io.vn`
- **Đường dẫn & Dịch vụ trên VPS:**
  - Backend FastAPI: `/opt/marketflow/backend` (virtualenv tại `/opt/marketflow/.venv`, systemd service: `marketflow-api.service` chạy ở `127.0.0.1:8000`)
  - Frontend tĩnh (Nginx): `/var/www/marketflow` (Nginx lắng nghe ở `127.0.0.1:8080`, bắt buộc `chmod 755` cho thư mục và `chmod 644` cho file sau khi `scp`)
  - Dịch vụ hệ thống: `systemctl status nginx postgresql marketflow-api cloudflared`

