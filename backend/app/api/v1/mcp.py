"""
API Endpoints cho Model Context Protocol (MCP) Server & Agentic AI Copilot.

Hỗ trợ đồng thời:
1. Chuẩn giao thức JSON-RPC 2.0 (`POST /api/v1/mcp/rpc`) cho các MCP Clients bên ngoài.
2. Các REST Endpoints trực quan (`/manifest`, `/tools/call`, `/resources/read`, `/agent/run`,
   `/compliance/auto-fix`) phục vụ giao diện MCP & Agentic Copilot Studio trên Frontend.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.entities import User
from app.services.mcp.mcp_server import mcp_server

router = APIRouter(prefix="/mcp", tags=["Model Context Protocol (MCP) & Agentic AI"])


class MCPToolCallRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Tên MCP Tool cần gọi")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Tham số đầu vào của Tool")


class MCPAgentRunRequest(BaseModel):
    goal: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="Mục tiêu tự nhiên giao cho Agentic AI điều phối qua MCP Tools",
    )
    campaign_id: Optional[int] = Field(default=None, description="ID chiến dịch trọng tâm")
    workspace_id: Optional[int] = Field(default=None, description="ID Workspace hiện hành")
    channel: str = Field(default="facebook", max_length=50, description="Kênh tiếp thị mục tiêu")
    draft_input: Optional[Dict[str, str]] = Field(
        default=None,
        description="Nội dung nháp tùy chọn {title, body, cta} để Agent quét và tự động sửa lỗi tuân thủ",
    )


class MCPComplianceAutoFixRequest(BaseModel):
    workspace_id: Optional[int] = None
    channel: str = Field(default="facebook", max_length=50)
    title: str = Field(default="", max_length=500)
    body: str = Field(default="", max_length=10000)
    cta: str = Field(default="", max_length=500)


@router.get("/manifest")
def get_mcp_manifest(
    current_user: User = Depends(get_current_user),
):
    """Trả về toàn bộ thông tin cấu hình MCP Server, danh sách Tools, Resources và Prompts."""
    return {
        "server": mcp_server.get_server_info(),
        "tools": mcp_server.list_tools(),
        "resources": mcp_server.list_resources(),
        "prompts": mcp_server.list_prompts(),
    }


@router.post("/rpc")
def handle_mcp_jsonrpc(
    payload: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Điểm cuối JSON-RPC 2.0 chuẩn Model Context Protocol (initialize, tools/list, tools/call, resources/read...)."""
    return mcp_server.handle_jsonrpc(db=db, user=current_user, payload=payload)


@router.post("/tools/call")
def call_mcp_tool(
    req: MCPToolCallRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Thực thi trực tiếp một MCP Tool với kiểm soát cách ly đa người thuê (Multi-tenant Isolation)."""
    try:
        return mcp_server.call_tool(db=db, user=current_user, name=req.name, arguments=req.arguments)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/resources/read")
def read_mcp_resource(
    uri: str = Query(..., description="URI của MCP Resource (VD: marketflow://workspace/brand-kit)"),
    workspace_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Đọc nội dung ngữ cảnh từ một MCP Resource."""
    try:
        return mcp_server.read_resource(db=db, user=current_user, uri=uri, workspace_id=workspace_id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/agent/run")
def run_mcp_agent(
    req: MCPAgentRunRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Kích hoạt Agentic AI Copilot tự động đọc MCP Resources và gọi chuỗi MCP Tools để giải quyết mục tiêu."""
    try:
        return mcp_server.run_agent_workflow(
            db=db,
            user=current_user,
            goal=req.goal,
            campaign_id=req.campaign_id,
            workspace_id=req.workspace_id,
            channel=req.channel,
            draft_input=req.draft_input,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/compliance/auto-fix")
def auto_fix_compliance_endpoint(
    req: MCPComplianceAutoFixRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """1-Click AI Semantic Compliance Auto-Fix: Tự động viết lại toàn bộ vi phạm chính sách để đạt 100/100 PASSED."""
    try:
        res = mcp_server.call_tool(
            db=db,
            user=current_user,
            name="auto_fix_compliance_violations",
            arguments=req.model_dump(),
        )
        return res["structuredContent"]
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


class MCPWebhookTestRequest(BaseModel):
    connector_type: str = Field(
        default="n8n_zapier",
        max_length=50,
        description="Loại kết nối: n8n_zapier, telegram_bot, slack_discord, facebook_graph, tiktok_business, wordpress_cms",
    )
    event_type: str = Field(
        default="content.published",
        max_length=100,
        description="Sự kiện: content.published, content.in_review, campaign.budget_rebalanced, compliance.auto_fixed",
    )
    campaign_id: Optional[int] = Field(default=None)
    workspace_id: Optional[int] = Field(default=None)
    target_url: Optional[str] = Field(default=None, max_length=500)


@router.get("/integrations/blueprint")
def get_external_integrations_blueprint(
    workspace_id: int = Query(1, description="ID Workspace"),
    current_user: User = Depends(get_current_user),
):
    """Trả về cấu hình kết nối cho Claude Desktop, Cursor IDE, cURL JSON-RPC và danh mục Outbound Webhooks."""
    return mcp_server.get_external_integrations_blueprint(workspace_id=workspace_id)


@router.post("/integrations/webhook-test")
def test_external_webhook_dispatch(
    req: MCPWebhookTestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Kiểm thử bắn Outbound Webhook ký số HMAC-SHA256 (X-MarketFlow-Signature) tới các nền tảng bên ngoài."""
    try:
        res = mcp_server.call_tool(
            db=db,
            user=current_user,
            name="dispatch_external_webhook",
            arguments=req.model_dump(),
        )
        return res["structuredContent"]
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

