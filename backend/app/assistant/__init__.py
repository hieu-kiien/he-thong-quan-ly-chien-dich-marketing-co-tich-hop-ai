"""Trợ lý AI runtime & MCP server (CONTRACT §5, §6, §11, §12)."""

from __future__ import annotations

from app.assistant.mcp_server import mcp_server
from app.assistant.router import router

__all__ = ["mcp_server", "router"]
