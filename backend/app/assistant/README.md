# MarketFlow v2 — Trợ lý AI & MCP Runtime

Thư mục này dành riêng cho AI Assistant Runtime Agent triển khai:
- MCP server streamable HTTP mount tại `/mcp` (`FastMCP(..., stateless_http=True)`).
- Endpoints `/api/v1/assistant/*` (threads, messages SSE stream, actions confirm/reject, status).
- Tích hợp với `ai-runner` (127.0.0.1:8100) qua NDJSON stream.

Toàn bộ nghiệp vụ đọc/ghi được gọi qua service layer (`app.services.*`).
