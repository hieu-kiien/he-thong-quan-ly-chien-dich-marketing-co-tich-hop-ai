"""Fake AI Runner HTTP server phục vụ chạy QA và Playwright E2E tests (CONTRACT §7, §11).

Chạy trên cổng 8100:
    python backend/tests/qa_fake_runner.py --port 8100
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
import uuid
from collections.abc import AsyncIterator
from typing import Any

import httpx
import uvicorn
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import StreamingResponse

try:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    HAS_MCP_CLIENT = True
except ImportError:
    HAS_MCP_CLIENT = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("qa_fake_runner")

app = FastAPI(title="QA Fake AI Runner")

aborted_run_ids: set[str] = set()


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "ok": True,
        "opencode_version": "1.19.0",
        "model": "fake-qa-runner",
        "queue_length": 0,
        "active": 0,
        "last_error": None,
    }


@app.post("/abort")
async def abort(payload: dict[str, Any]) -> dict[str, bool]:
    run_id = payload.get("run_id")
    if run_id:
        aborted_run_ids.add(str(run_id))
        logger.info("Aborted run_id: %s", run_id)
    return {"ok": True}


async def _execute_mcp_tools(mcp_url: str, run_token: str, campaign_id: int) -> None:
    """Gọi backend MCP endpoint bằng MCP client hoặc fallback httpx."""
    called_successfully = False

    # 1. Thử dùng official MCP python client nếu có
    if HAS_MCP_CLIENT:
        try:
            logger.info("Connecting to MCP via streamablehttp_client: %s", mcp_url)
            async with (
                streamablehttp_client(
                    mcp_url,
                    headers={"Authorization": f"Bearer {run_token}"},
                    timeout=10,
                ) as (read, write, _),
                ClientSession(read, write) as session,
            ):
                await session.initialize()
                # Gọi get_stats
                try:
                    await session.call_tool("get_stats", arguments={"campaign_id": campaign_id})
                except Exception as e:  # noqa: BLE001
                    logger.warning("MCP call get_stats error: %s", e)

                # Gọi propose_content_drafts
                await session.call_tool(
                    "propose_content_drafts",
                    arguments={
                        "items": [
                            {
                                "campaign_id": campaign_id,
                                "channel_code": "FACEBOOK",
                                "content_type": "SOCIAL_POST",
                                "title": "Bản nháp bài viết Facebook từ Trợ lý AI",
                                "body": "Thưởng thức hương vị cà phê Robusta nguyên bản từ vùng cao nguyên Đắk Lắk. Giảm 20% cho đơn hàng đầu tiên trong tuần lễ ra mắt!",
                                "cta": "Đặt ngay hôm nay",
                                "status": "PENDING_REVIEW",
                            }
                        ]
                    },
                )
                called_successfully = True
                logger.info("MCP client tools executed successfully")
        except Exception as exc:  # noqa: BLE001
            logger.warning("mcp.client failed, falling back to httpx: %s", exc)

    # 2. Fallback httpx JSON-RPC nếu MCP client chưa thành công
    if not called_successfully:
        headers = {
            "Accept": "application/json, text/event-stream",
            "Authorization": f"Bearer {run_token}",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            # get_stats
            try:
                await client.post(
                    mcp_url,
                    headers=headers,
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "tools/call",
                        "params": {"name": "get_stats", "arguments": {"campaign_id": campaign_id}},
                    },
                )
            except Exception as e:  # noqa: BLE001
                logger.warning("httpx get_stats error: %s", e)

            # propose_content_drafts
            try:
                await client.post(
                    mcp_url,
                    headers=headers,
                    json={
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/call",
                        "params": {
                            "name": "propose_content_drafts",
                            "arguments": {
                                "items": [
                                    {
                                        "campaign_id": campaign_id,
                                        "channel_code": "FACEBOOK",
                                        "content_type": "SOCIAL_POST",
                                        "title": "Bản nháp bài viết Facebook từ Trợ lý AI",
                                        "body": "Thưởng thức hương vị cà phê Robusta nguyên bản từ vùng cao nguyên Đắk Lắk. Giảm 20% cho đơn hàng đầu tiên trong tuần lễ ra mắt!",
                                        "cta": "Đặt ngay hôm nay",
                                        "status": "PENDING_REVIEW",
                                    }
                                ]
                            },
                        },
                    },
                )
                logger.info("httpx fallback tools executed successfully")
            except Exception as e:  # noqa: BLE001
                logger.error("httpx fallback propose_content_drafts failed: %s", e)


@app.post("/run")
async def run(
    request: Request,
    x_runner_token: str | None = Header(None, alias="X-Runner-Token"),
) -> StreamingResponse:
    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON body") from exc

    prompt: str = body.get("prompt", "")
    session_id: str | None = body.get("session_id")
    env = body.get("env") or {}
    run_token: str = env.get("MF_RUN_TOKEN", "")

    run_id = request.headers.get("X-Run-Id") or str(uuid.uuid4())

    async def event_generator() -> AsyncIterator[str]:
        # 1. run event
        yield json.dumps({"type": "run", "run_id": run_id}) + "\n"
        await asyncio.sleep(0.05)

        # 2. queued event
        yield json.dumps({"type": "queued", "position": 0}) + "\n"
        await asyncio.sleep(0.05)

        # 3. session event
        sid = session_id or f"qa-session-{uuid.uuid4().hex[:8]}"
        yield json.dumps({"type": "session", "id": sid}) + "\n"
        await asyncio.sleep(0.05)

        # Scenario: AI_RATE_LIMITED simulation
        if "[RATE_LIMIT]" in prompt or "rate limit" in prompt.lower() or "ai_rate_limited" in prompt.lower():
            logger.info("Emitting simulated AI_RATE_LIMITED error")
            yield json.dumps({
                "type": "error",
                "code": "AI_RATE_LIMITED",
                "message": "Đã chạm giới hạn sử dụng mô hình AI miễn phí. Vui lòng thử lại sau ít phút.",
            }) + "\n"
            return

        # Scenario: Slow turn for testing STOP
        if "[SLOW]" in prompt or "[STOP]" in prompt:
            logger.info("Entering slow mode for stop testing...")
            yield json.dumps({"type": "text", "text": "Đang phân tích yêu cầu phức tạp..."}) + "\n"
            for _ in range(60):
                if run_id in aborted_run_ids:
                    logger.info("Turn %s was aborted by user", run_id)
                    return
                await asyncio.sleep(0.2)
            yield json.dumps({"type": "text", "text": " Hoàn tất xử lý sau thời gian chờ."}) + "\n"
            yield json.dumps({"type": "done", "model": "fake-qa-runner", "latency_ms": 12000}) + "\n"
            return

        # Standard AI flow: execute MCP tools if run_token is present
        if run_token:
            # Parse campaign_id from prompt if present
            camp_id = 1
            match = re.search(r"#(\d+)", prompt)
            if match:
                camp_id = int(match.group(1))

            mcp_url = "http://127.0.0.1:8000/mcp/"
            await _execute_mcp_tools(mcp_url, run_token, camp_id)

        # Text stream output
        text_content = (
            "Dựa trên số liệu hiệu quả và phân tích mục tiêu chiến dịch, "
            "tôi đã chuẩn bị đề xuất bản nháp nội dung cho kênh Facebook. "
            "Bạn có thể xem thẻ đề xuất ở bảng bên phải, chỉnh sửa câu chữ hoặc "
            "lời kêu gọi hành động (CTA) và bấm **Xác nhận** để chuyển sang bước phê duyệt."
        )
        yield json.dumps({"type": "text", "text": text_content}) + "\n"
        await asyncio.sleep(0.05)

        # Done event
        yield json.dumps({"type": "done", "model": "fake-qa-runner", "latency_ms": 350}) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8100)
    args = parser.parse_args()
    uvicorn.run(app, host="127.0.0.1", port=args.port)
