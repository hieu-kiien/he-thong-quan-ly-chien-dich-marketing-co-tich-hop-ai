"""FastMCP streamable-HTTP server mount tại `/mcp` cho OpenCode gọi ngược (CONTRACT §5, §11)."""

import logging
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import jwt
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp.server import TransportSecuritySettings
from sqlalchemy.orm import Session

from app.assistant.bus import event_bus
from app.assistant.context import ToolContext, get_db_context
from app.assistant.tools import registry
from app.core.config import settings
from app.core.errors import PermissionDenied
from app.models.ai import AiAction, AiMessage, AiThread
from app.models.enums import AiMessageStatus
from app.models.user import User
from app.schemas.ai import AiActionOut

logger = logging.getLogger(__name__)

# Khởi tạo FastMCP với stateless_http=True và path="/" (để khi mount tại /mcp thì path nội bộ là /)
mcp_server = FastMCP(
    name="marketflow",
    instructions="Trợ lý Marketing AI MarketFlow MCP Server",
    stateless_http=True,
    streamable_http_path="/",
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)


@asynccontextmanager
async def run_mcp_session_manager() -> AsyncIterator[None]:
    """Quản lý vòng đời StreamableHTTPSessionManager, hỗ trợ restart an toàn trong test suite."""
    sm = mcp_server.session_manager
    if getattr(sm, "_has_started", False):
        sm._has_started = False
    async with sm.run():
        yield


def verify_run_token(ctx: Context, db: Session) -> tuple[User, AiThread, AiMessage]:
    """Xác thực run-token từ header Authorization: Bearer <run-token>."""
    headers = ctx.request_context.request.headers
    auth_header = ""
    for k, v in headers.items():
        if k.lower() == "authorization":
            auth_header = v
            break
    if not auth_header.startswith("Bearer "):
        raise PermissionDenied("Thiếu Bearer run-token")

    token = auth_header[7:].strip()
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise PermissionDenied("Run-token đã hết hạn") from exc
    except jwt.PyJWTError as exc:
        raise PermissionDenied("Run-token không hợp lệ") from exc

    if payload.get("typ") != "assistant_run":
        raise PermissionDenied("Loại token không hợp lệ (yêu cầu assistant_run)")

    uid = payload.get("uid")
    thread_id = payload.get("thread_id")
    message_id = payload.get("message_id")
    if uid is None or thread_id is None or message_id is None:
        raise PermissionDenied("Run-token thiếu các trường định danh")

    user = db.get(User, uid)
    if not user or not user.is_active:
        raise PermissionDenied("Tài khoản người dùng không tồn tại hoặc đã bị khoá")
    # Đăng xuất / đổi mật khẩu (tăng token_version) phải vô hiệu hoá luôn run-token đang chạy
    if "tv" in payload and int(payload["tv"]) != (user.token_version or 0):
        raise PermissionDenied("Phiên đăng nhập đã bị thu hồi")

    thread = db.get(AiThread, thread_id)
    if not thread or thread.user_id != user.id:
        raise PermissionDenied("Phiên hội thoại không tồn tại hoặc không thuộc về người dùng")

    message = db.get(AiMessage, message_id)
    if not message or message.thread_id != thread.id:
        raise PermissionDenied("Tin nhắn trợ lý không hợp lệ")
    # Run-token chỉ có hiệu lực khi lượt trả lời đang chạy (không dùng lại sau khi đã xong / bị dừng)
    if message.status != AiMessageStatus.STREAMING:
        raise PermissionDenied("Lượt trả lời đã kết thúc, run-token không còn hiệu lực")

    return user, thread, message


def _generate_summary(tool_name: str, args: dict[str, Any], result: dict[str, Any]) -> str:
    if "summary" in result:
        return str(result["summary"])
    if tool_name == "list_campaigns":
        return f"Đã tra cứu {len(result.get('campaigns', []))} chiến dịch"
    if tool_name == "get_campaign":
        return f"Đã xem chi tiết chiến dịch '{result.get('name', '')}'"
    if tool_name == "get_stats":
        return f"Đã tra cứu thống kê (nhóm: {result.get('group_by', 'tổng quan')})"
    if tool_name == "list_contents":
        return f"Đã tra cứu {len(result.get('contents', []))} nội dung"
    if tool_name == "get_content":
        return f"Đã xem nội dung '{result.get('title', '')}'"
    if tool_name == "list_schedules":
        return f"Đã tra cứu {len(result.get('schedules', []))} lịch đăng"
    if tool_name == "list_channels":
        return f"Đã tra cứu {len(result.get('channels', []))} kênh truyền thông"
    if tool_name == "get_brand_profile":
        return "Đã tra cứu hồ sơ thương hiệu"
    if tool_name == "check_banned_keywords":
        return f"Đã kiểm tra từ cấm ({len(result.get('matches', []))} từ phát hiện)"
    return f"Đã thực thi công cụ {tool_name}"


async def _execute_tool(ctx: Context, tool_name: str, raw_args: dict[str, Any]) -> dict[str, Any]:
    tool_def = registry.get(tool_name)
    if not tool_def:
        raise ValueError(f"Không tìm thấy công cụ '{tool_name}'")

    call_id = str(getattr(ctx, "request_id", None) or uuid.uuid4().hex[:8])

    with get_db_context() as db:
        user, thread, message = verify_run_token(ctx, db)
        tool_ctx = ToolContext(db=db, user=user, thread=thread, message=message)

        # 1. Phát sự kiện running trên event bus
        await event_bus.publish(
            message.id,
            "tool_call",
            {
                "id": call_id,
                "name": tool_name,
                "args": raw_args,
                "status": "running",
            },
        )

        try:
            # 2. Xác thực tham số và thực thi
            validated_args = tool_def.args_model.model_validate(raw_args)
            result = tool_def.handler(tool_ctx, validated_args)
            summary = _generate_summary(tool_name, raw_args, result)

            # 3. Nếu là write tool, phát sự kiện action
            if tool_def.is_write and "action_id" in result:
                action = db.get(AiAction, result["action_id"])
                if action:
                    action_data = AiActionOut.model_validate(action).model_dump(mode="json")
                    await event_bus.publish(message.id, "action", action_data)

            # 4. Phát sự kiện done trên event bus
            await event_bus.publish(
                message.id,
                "tool_call",
                {
                    "id": call_id,
                    "name": tool_name,
                    "args": raw_args,
                    "status": "done",
                    "summary": summary,
                },
            )

            # 5. Lưu lại part trong message.parts_json
            current_parts = list(message.parts_json or [])
            current_parts.append({
                "type": "tool_call",
                "id": call_id,
                "name": tool_name,
                "args": raw_args,
                "status": "done",
                "summary": summary,
            })
            if tool_def.is_write and "action_id" in result:
                current_parts.append({
                    "type": "action",
                    "action_id": result["action_id"],
                })
            message.parts_json = current_parts
            db.commit()

            return result

        except Exception as exc:
            err_msg = getattr(exc, "message", str(exc))
            await event_bus.publish(
                message.id,
                "tool_call",
                {
                    "id": call_id,
                    "name": tool_name,
                    "args": raw_args,
                    "status": "error",
                    "summary": err_msg,
                },
            )
            current_parts = list(message.parts_json or [])
            current_parts.append({
                "type": "tool_call",
                "id": call_id,
                "name": tool_name,
                "args": raw_args,
                "status": "error",
                "summary": err_msg,
            })
            message.parts_json = current_parts
            db.commit()
            raise


# --- Đăng ký 14 tools vào FastMCP server --------------------------------------

@mcp_server.tool(name="list_campaigns", description="Tra cứu danh sách chiến dịch tiếp thị")
async def list_campaigns(
    ctx: Context,
    q: str | None = None,
    status: str | None = None,
    channel_code: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    raw = {k: v for k, v in {"q": q, "status": status, "channel_code": channel_code, "date_from": date_from, "date_to": date_to, "limit": limit}.items() if v is not None}
    return await _execute_tool(ctx, "list_campaigns", raw)


@mcp_server.tool(name="get_campaign", description="Xem chi tiết chiến dịch gồm thông tin mục tiêu, ngân sách, kênh và stats")
async def get_campaign(ctx: Context, campaign_id: int) -> dict[str, Any]:
    return await _execute_tool(ctx, "get_campaign", {"campaign_id": campaign_id})


@mcp_server.tool(name="get_stats", description="Xem số liệu thống kê hiệu quả tiếp thị (tổng quan, kênh, chiến dịch hoặc thời gian)")
async def get_stats(
    ctx: Context,
    campaign_id: int | None = None,
    channel_code: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    group_by: str = "none",
) -> dict[str, Any]:
    raw = {"campaign_id": campaign_id, "channel_code": channel_code, "date_from": date_from, "date_to": date_to, "group_by": group_by}
    return await _execute_tool(ctx, "get_stats", {k: v for k, v in raw.items() if v is not None})


@mcp_server.tool(name="list_contents", description="Tra cứu danh sách bài viết/nội dung marketing")
async def list_contents(
    ctx: Context,
    campaign_id: int | None = None,
    channel_code: str | None = None,
    status: str | None = None,
    q: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    raw = {"campaign_id": campaign_id, "channel_code": channel_code, "status": status, "q": q, "limit": limit}
    return await _execute_tool(ctx, "list_contents", {k: v for k, v in raw.items() if v is not None})


@mcp_server.tool(name="get_content", description="Xem chi tiết một bài viết/nội dung marketing")
async def get_content(ctx: Context, content_id: int) -> dict[str, Any]:
    return await _execute_tool(ctx, "get_content", {"content_id": content_id})


@mcp_server.tool(name="list_schedules", description="Tra cứu lịch đăng nội dung theo thời gian hoặc chiến dịch")
async def list_schedules(
    ctx: Context,
    date_from: str | None = None,
    date_to: str | None = None,
    campaign_id: int | None = None,
) -> dict[str, Any]:
    raw = {"date_from": date_from, "date_to": date_to, "campaign_id": campaign_id}
    return await _execute_tool(ctx, "list_schedules", {k: v for k, v in raw.items() if v is not None})


@mcp_server.tool(name="list_channels", description="Lấy danh sách các kênh truyền thông kèm quy chuẩn định dạng (format_rules)")
async def list_channels(ctx: Context) -> dict[str, Any]:
    return await _execute_tool(ctx, "list_channels", {})


@mcp_server.tool(name="get_brand_profile", description="Xem hồ sơ thương hiệu và danh sách từ cấm")
async def get_brand_profile(ctx: Context) -> dict[str, Any]:
    return await _execute_tool(ctx, "get_brand_profile", {})


@mcp_server.tool(name="check_banned_keywords", description="Kiểm tra một đoạn văn bản xem có chứa từ cấm của thương hiệu không")
async def check_banned_keywords(ctx: Context, text: str) -> dict[str, Any]:
    return await _execute_tool(ctx, "check_banned_keywords", {"text": text})


@mcp_server.tool(name="propose_content_drafts", description="Tạo đề xuất soạn thảo nhiều bản nháp nội dung (bài đăng, email...). Chỉ tạo đề xuất chờ người dùng xác nhận.")
async def propose_content_drafts(ctx: Context, items: list[dict[str, Any]]) -> dict[str, Any]:
    return await _execute_tool(ctx, "propose_content_drafts", {"items": items})


@mcp_server.tool(name="propose_campaign", description="Tạo đề xuất một chiến dịch tiếp thị mới với mục tiêu, ngân sách và các kênh phân bổ. Chỉ tạo đề xuất chờ người dùng xác nhận.")
async def propose_campaign(
    ctx: Context,
    name: str,
    goal: str,
    objective: str,
    target_audience: str,
    product: str,
    start_date: str,
    end_date: str,
    budget: int,
    channels: list[dict[str, Any]],
    key_message: str | None = None,
) -> dict[str, Any]:
    raw = {
        "name": name,
        "goal": goal,
        "objective": objective,
        "target_audience": target_audience,
        "product": product,
        "start_date": start_date,
        "end_date": end_date,
        "budget": budget,
        "channels": channels,
        "key_message": key_message,
    }
    return await _execute_tool(ctx, "propose_campaign", {k: v for k, v in raw.items() if v is not None})


@mcp_server.tool(name="propose_campaign_update", description="Tạo đề xuất chỉnh sửa thông tin hoặc phân bổ kênh của chiến dịch hiện có. Chỉ tạo đề xuất chờ người dùng xác nhận.")
async def propose_campaign_update(
    ctx: Context,
    campaign_id: int,
    name: str | None = None,
    goal: str | None = None,
    objective: str | None = None,
    target_audience: str | None = None,
    product: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    budget: int | None = None,
    status: str | None = None,
    key_message: str | None = None,
    channels: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    raw = {
        "campaign_id": campaign_id,
        "name": name,
        "goal": goal,
        "objective": objective,
        "target_audience": target_audience,
        "product": product,
        "start_date": start_date,
        "end_date": end_date,
        "budget": budget,
        "status": status,
        "key_message": key_message,
        "channels": channels,
    }
    return await _execute_tool(ctx, "propose_campaign_update", {k: v for k, v in raw.items() if v is not None})


@mcp_server.tool(name="propose_schedule", description="Tạo đề xuất lên lịch đăng bài cho một nội dung marketing vào thời điểm cụ thể. Chỉ tạo đề xuất chờ người dùng xác nhận.")
async def propose_schedule(
    ctx: Context,
    content_id: int,
    scheduled_at: str,
    note: str | None = None,
) -> dict[str, Any]:
    raw = {"content_id": content_id, "scheduled_at": scheduled_at, "note": note}
    return await _execute_tool(ctx, "propose_schedule", {k: v for k, v in raw.items() if v is not None})


@mcp_server.tool(name="propose_metrics", description="Tạo đề xuất nhập hoặc cập nhật số liệu hiệu quả (views, clicks, conversions, cost) từ bảng dữ liệu người dùng cung cấp. Chỉ tạo đề xuất chờ người dùng xác nhận.")
async def propose_metrics(ctx: Context, rows: list[dict[str, Any]]) -> dict[str, Any]:
    return await _execute_tool(ctx, "propose_metrics", {"rows": rows})
