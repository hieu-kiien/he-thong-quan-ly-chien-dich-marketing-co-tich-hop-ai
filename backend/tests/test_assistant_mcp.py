"""Kiểm thử MCP Server & Run-token Authentication (CONTRACT §5, §11)."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy.orm import Session

from app.assistant.bus import event_bus
from app.assistant.mcp_server import run_mcp_session_manager
from app.core.database import get_db
from app.core.security import create_access_token, encode_token
from app.core.timeutil import now_utc
from app.main import app
from app.models import AiMessage, AiThread, Campaign, User
from app.models.enums import AiMessageRole, AiMessageStatus


@pytest.fixture(autouse=True)
def override_db_for_mcp(db: Session):
    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def mcp_setup(
    db: Session,
    marketer1_user: User,
    sample_campaign: Campaign,
) -> tuple[AiThread, AiMessage, str]:
    thread = AiThread(
        user_id=marketer1_user.id,
        campaign_id=sample_campaign.id,
        title="Phiên kiểm thử MCP",
        last_message_at=now_utc(),
    )
    db.add(thread)
    db.flush()

    message = AiMessage(
        thread_id=thread.id,
        role=AiMessageRole.ASSISTANT,
        content="",
        parts_json=[],
        status=AiMessageStatus.STREAMING,
    )
    db.add(message)
    db.commit()
    db.refresh(thread)
    db.refresh(message)

    # Valid run-token (10 minutes)
    now = datetime.now(UTC)
    payload = {
        "typ": "assistant_run",
        "uid": marketer1_user.id,
        "thread_id": thread.id,
        "message_id": message.id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=10)).timestamp()),
    }
    run_token = encode_token(payload)
    return thread, message, run_token


@pytest.mark.anyio
async def test_mcp_tools_list():
    """Kiểm tra MCP tools/list trả về 14 công cụ không có tiền tố."""
    headers = {"Accept": "application/json, text/event-stream"}
    async with (
        run_mcp_session_manager(),
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client,
    ):
        resp = await client.post(
            "/mcp/",
            headers=headers,
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
        )
        assert resp.status_code == 200
        # Parse SSE stream
        text = resp.text
        assert "event: message" in text
        data_line = next(line for line in text.splitlines() if line.startswith("data: "))
        data = json.loads(data_line[6:])
        tools = data["result"]["tools"]
        assert len(tools) == 14
        tool_names = [t["name"] for t in tools]
        assert "list_campaigns" in tool_names
        assert "get_campaign" in tool_names
        assert "propose_content_drafts" in tool_names
        assert "propose_campaign" in tool_names
        assert "check_banned_keywords" in tool_names


@pytest.mark.anyio
async def test_mcp_call_tool_read_success(
    mcp_setup: tuple[AiThread, AiMessage, str],
    sample_campaign: Campaign,
    db: Session,
):
    _, message, run_token = mcp_setup

    bus_queue = await event_bus.register(message.id)
    headers = {
        "Accept": "application/json, text/event-stream",
        "Authorization": f"Bearer {run_token}",
    }

    async with (
        run_mcp_session_manager(),
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client,
    ):
        # Call list_campaigns tool
        resp = await client.post(
            "/mcp/",
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "list_campaigns", "arguments": {"limit": 5}},
            },
        )
        assert resp.status_code == 200
        data_line = next(line for line in resp.text.splitlines() if line.startswith("data: "))
        data = json.loads(data_line[6:])
        assert data["result"]["isError"] is False
        content_text = data["result"]["content"][0]["text"]
        assert "campaigns" in content_text

        # Verify event bus received tool_call events: running then done
        running_ev = await bus_queue.get()
        assert running_ev["event"] == "tool_call"
        assert running_ev["data"]["status"] == "running"
        assert running_ev["data"]["name"] == "list_campaigns"

        done_ev = await bus_queue.get()
        assert done_ev["event"] == "tool_call"
        assert done_ev["data"]["status"] == "done"
        assert "summary" in done_ev["data"]

        # Verify message parts_json updated in DB
        db.refresh(message)
        assert len(message.parts_json) >= 1
        assert message.parts_json[0]["name"] == "list_campaigns"
        assert message.parts_json[0]["status"] == "done"

    await event_bus.unregister(message.id, bus_queue)


@pytest.mark.anyio
async def test_mcp_call_tool_write_propose(
    mcp_setup: tuple[AiThread, AiMessage, str],
    sample_campaign: Campaign,
    db: Session,
):
    """Kiểm tra gọi write tool qua MCP phát sinh sự kiện action."""
    _, message, run_token = mcp_setup

    bus_queue = await event_bus.register(message.id)
    headers = {
        "Accept": "application/json, text/event-stream",
        "Authorization": f"Bearer {run_token}",
    }

    async with (
        run_mcp_session_manager(),
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client,
    ):
        resp = await client.post(
            "/mcp/",
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "propose_content_drafts",
                    "arguments": {
                        "items": [
                            {
                                "campaign_id": sample_campaign.id,
                                "channel_code": "FACEBOOK",
                                "content_type": "SOCIAL_POST",
                                "title": "Bản nháp qua MCP",
                                "body": "Nội dung bài viết được sinh ra bởi OpenCode",
                                "cta": "Xem ngay",
                                "status": "PENDING_REVIEW",
                            }
                        ]
                    },
                },
            },
        )
        assert resp.status_code == 200

        # Bus should receive: tool_call(running) -> action -> tool_call(done)
        ev1 = await bus_queue.get()
        assert ev1["event"] == "tool_call"
        assert ev1["data"]["status"] == "running"

        ev2 = await bus_queue.get()
        assert ev2["event"] == "action"
        assert ev2["data"]["tool"] == "propose_content_drafts"

        ev3 = await bus_queue.get()
        assert ev3["event"] == "tool_call"
        assert ev3["data"]["status"] == "done"

    await event_bus.unregister(message.id, bus_queue)


@pytest.mark.anyio
async def test_run_token_validation_failures(
    mcp_setup: tuple[AiThread, AiMessage, str],
    marketer1_user: User,
    db: Session,
):
    thread, message, _ = mcp_setup
    base_headers = {"Accept": "application/json, text/event-stream"}

    async with (
        run_mcp_session_manager(),
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client,
    ):
        # 1. Missing Authorization header
        resp = await client.post(
            "/mcp/",
            headers=base_headers,
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "list_channels", "arguments": {}}},
        )
        data_line = next(line for line in resp.text.splitlines() if line.startswith("data: "))
        data = json.loads(data_line[6:])
        assert data["result"]["isError"] is True
        assert "Thiếu Bearer run-token" in data["result"]["content"][0]["text"]

        # 2. Normal user access token (typ=access instead of assistant_run)
        user_jwt = create_access_token(marketer1_user)
        resp = await client.post(
            "/mcp/",
            headers={**base_headers, "Authorization": f"Bearer {user_jwt}"},
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "list_channels", "arguments": {}}},
        )
        data_line = next(line for line in resp.text.splitlines() if line.startswith("data: "))
        data = json.loads(data_line[6:])
        assert data["result"]["isError"] is True
        assert "assistant_run" in data["result"]["content"][0]["text"]

        # 3. Expired run-token
        past = datetime.now(UTC) - timedelta(minutes=1)
        expired_token = encode_token({
            "typ": "assistant_run",
            "uid": marketer1_user.id,
            "thread_id": thread.id,
            "message_id": message.id,
            "iat": int(past.timestamp()),
            "exp": int(past.timestamp()),
        })
        resp = await client.post(
            "/mcp/",
            headers={**base_headers, "Authorization": f"Bearer {expired_token}"},
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "list_channels", "arguments": {}}},
        )
        data_line = next(line for line in resp.text.splitlines() if line.startswith("data: "))
        data = json.loads(data_line[6:])
        assert data["result"]["isError"] is True
        assert "hết hạn" in data["result"]["content"][0]["text"]


@pytest.mark.anyio
async def test_mcp_mount_paths(mcp_setup: tuple[AiThread, AiMessage, str]):
    """Đảm bảo cả /mcp và /mcp/ đều hoạt động bình thường."""
    _, _, run_token = mcp_setup
    headers = {
        "Accept": "application/json, text/event-stream",
        "Authorization": f"Bearer {run_token}",
    }

    async with (
        run_mcp_session_manager(),
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client,
    ):
        # /mcp/ with trailing slash
        r1 = await client.post(
            "/mcp/",
            headers=headers,
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "list_channels", "arguments": {}}},
        )
        assert r1.status_code == 200

        # /mcp without trailing slash
        r2 = await client.post(
            "/mcp",
            headers=headers,
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "list_channels", "arguments": {}}},
        )
        assert r2.status_code == 200


@pytest.mark.anyio
async def test_mcp_run_token_rejected_after_turn_finished_or_revoked(
    mcp_setup: tuple[AiThread, AiMessage, str],
    marketer1_user: User,
    db: Session,
):
    """Run-token chỉ dùng được khi lượt đang chạy, và mất hiệu lực khi người dùng đăng xuất/đổi mật khẩu."""
    thread, message, _ = mcp_setup
    now = datetime.now(UTC)

    def mint(**extra) -> str:
        return encode_token({
            "typ": "assistant_run",
            "uid": marketer1_user.id,
            "thread_id": thread.id,
            "message_id": message.id,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=10)).timestamp()),
            **extra,
        })

    async def call(client: httpx.AsyncClient, token: str) -> dict:
        resp = await client.post(
            "/mcp/",
            headers={"Accept": "application/json, text/event-stream", "Authorization": f"Bearer {token}"},
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "list_channels", "arguments": {}}},
        )
        line = next(line for line in resp.text.splitlines() if line.startswith("data: "))
        return json.loads(line[6:])["result"]

    async with (
        run_mcp_session_manager(),
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client,
    ):
        # Token hợp lệ khi lượt đang STREAMING
        assert (await call(client, mint(tv=marketer1_user.token_version or 0)))["isError"] is False

        # token_version đã đổi (đăng xuất / đổi mật khẩu) → bị từ chối
        revoked = await call(client, mint(tv=(marketer1_user.token_version or 0) + 1))
        assert revoked["isError"] is True and "thu hồi" in revoked["content"][0]["text"]

        # Lượt đã kết thúc → run-token không còn hiệu lực
        message.status = AiMessageStatus.COMPLETE
        db.commit()
        finished = await call(client, mint(tv=marketer1_user.token_version or 0))
        assert finished["isError"] is True and "kết thúc" in finished["content"][0]["text"]
