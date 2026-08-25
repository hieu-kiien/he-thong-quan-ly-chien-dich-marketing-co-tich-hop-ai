# Quy ước dự án AIA331-80300-MARKETING-AI

## Phạm vi canonical

Nguồn chính của repo là đề tài **Hệ thống quản lý chiến dịch marketing có tích
hợp AI** trong học phần **Ứng dụng trí tuệ nhân tạo - AIA331**, mã **80300**.
Không được dùng nội dung quản lý bán hàng làm yêu cầu của dự án này. Các thư mục
và tài liệu bán hàng tồn tại từ phiên bản trước chỉ có trạng thái `LEGACY`.

## Thứ tự ưu tiên nguồn

Chỉ hai ảnh nguồn là `P0 / CRITICAL`; cấp phân chia đầy đủ nằm trong
`docs/10-priority-policy.md`.

1. `source-materials/BÀI KIỂM TRA.png` — nguồn P0 / CRITICAL về 10 tiêu chí
   đánh giá và nội dung phải hoàn thành.
2. `source-materials/DỰ ÁN.png` — nguồn P0 / CRITICAL về tên đề tài, học phần,
   mã số và yêu cầu nghiệp vụ.
3. `project.md`, `informember.md` và `docs/09-assessment-checklist.md` — bản
   chép/biên tập có truy vết từ hai ảnh nguồn.
4. Mã nguồn `marketing_management/` và test tương ứng.
5. Tài liệu trong `docs/`, prompt và báo cáo sinh từ các nguồn trên.
6. Tài liệu học tập/tham khảo bên ngoài — chỉ dùng `REFERENCE`.

Nếu có xung đột, ưu tiên đề bài ảnh và ghi rõ trong `docs/06-open-questions.md`;
không tự hợp nhất hai đề tài.

## Trạng thái tài liệu

Mỗi tài liệu phải ghi một trong các trạng thái: `CANONICAL`,
`IMPLEMENTED_BASELINE`, `DERIVED`, `PROPOSED`, `OPEN`, `TEMPLATE`,
`REFERENCE` hoặc `LEGACY`. Yêu cầu chưa có code/test không được mô tả là đã
triển khai.

## Quy tắc truy hồi cho AI

- Dùng ID ổn định: `FR-*`, `NFR-*`, `AI-*`, `DB-*`, `ARCH-*`, `FLOW-*`, `EV-*`.
- Khi trả lời, nêu kết luận → trạng thái → file nguồn → điểm chưa xác minh.
- Ưu tiên `docs/README.md`, sau đó `docs/00-project-context.md`.
- Dùng liên kết tương đối trong Markdown; không ghi đường dẫn máy cá nhân.
- Loại `.venv/`, `.env`, database local, cache, vector store và `.gitnexus/` khỏi
  hồ sơ nộp.
- Với câu hỏi về yêu cầu/tài liệu, chạy `python tools/rag_index.py build` rồi
  `search`; với câu hỏi về symbol/luồng code mới dùng GitNexus. Manifest RAG là
  `docs/rag-corpus.json`, database `.rag/` chỉ là artifact local.
- `.gitnexusignore` là ranh giới code graph; không mở rộng GitNexus vào thư mục
  legacy chỉ để làm tăng số file được index.

## Quy tắc mã nguồn

- Baseline chạy trong `marketing_management/`, dùng Django + SQLite cho demo.
- AI nằm sau adapter, prompt có version; kết quả AI luôn là bản nháp và phải
  qua human approval.
- Không commit API key, mật khẩu hoặc dữ liệu cá nhân thật.
- Sau khi sửa logic, chạy `manage.py check` và test liên quan.
- Trước commit, chạy GitNexus `detect_changes()` nếu môi trường có CLI/MCP;
  nếu không có, ghi rõ kiểm tra tĩnh thay thế.

## Legacy

Các đường dẫn `Code QLBH/`, `sales_management/`, các báo cáo bán hàng cũ và
`QLBH demo/` là artifact lịch sử của một đề tài khác. Không tham chiếu chúng để
chứng minh yêu cầu marketing. Không xóa dữ liệu lịch sử nếu chưa có yêu cầu
riêng; chỉ đánh dấu và loại khỏi manifest canonical.

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **he-thong-quan-ly-chien-dich-marketing-co-tich-hop-ai** (697 symbols, 979 relationships, 42 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

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
