"""FastAPI entrypoint for MarketFlow ai-runner service.

Implements CONTRACT §7 & §11:
- GET  /health -> probe version and status without calling any models
- POST /run    -> stream opencode execution as NDJSON
- POST /abort  -> abort an active run by run_id
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from . import __version__
from .config import Settings
from .runner import Runner, RunRequestData

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("ai_runner.main")

settings = Settings.from_env()
runner = Runner(settings)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("MarketFlow AI Runner v%s starting on %s:%d", __version__, settings.host, settings.port)
    log.info("Agent: %s, Sandbox: %s, Concurrency: %d", settings.agent, settings.sandbox_dir, settings.concurrency)
    # Background version probe
    asyncio.create_task(runner.probe_version())
    yield
    log.info("MarketFlow AI Runner shutting down")


app = FastAPI(
    title="MarketFlow AI Runner",
    version=__version__,
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)


def verify_runner_token(x_runner_token: str | None = Header(None, alias="X-Runner-Token")) -> None:
    expected = runner.s.runner_token
    if not expected:
        return
    if not x_runner_token or x_runner_token.strip() != expected.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "Mã xác thực X-Runner-Token không hợp lệ hoặc thiếu."},
        )


class RunRequestSchema(BaseModel):
    prompt: str = Field(..., description="User prompt or instructions for the turn")
    session_id: str | None = Field(None, description="OpenCode session ID for multi-turn conversation")
    run_token: str | None = Field(None, description="JWT run-token for backend MCP authentication")
    env: dict[str, str] | None = Field(None, description="Environment variables dict, e.g. {'MF_RUN_TOKEN': '...'}")
    timeout_s: float | None = Field(None, description="Per-run timeout override in seconds")
    model: str | None = Field(None, description="Model override, e.g. 'opencode/big-pickle'")
    run_id: str | None = Field(None, description="Client-specified unique run ID")


class AbortRequestSchema(BaseModel):
    run_id: str = Field(..., description="ID of the run to abort")


@app.get("/health")
async def health():
    """Cheap health check (does not call any LLM)."""
    return {
        "ok": runner.opencode_version is not None,
        "opencode_version": runner.opencode_version,
        "model": settings.model or "default",
        "queue_length": runner.queue_length,
        "active": runner.active,
        "last_error": runner.last_error,
        "rate_limited_for_s": runner.cooldown_remaining_s,
    }


@app.post("/run", dependencies=[Depends(verify_runner_token)])
async def run(
    body: RunRequestSchema,
    request: Request,
    x_run_id: str | None = Header(None, alias="X-Run-Id"),
):
    """Execute an assistant turn with OpenCode and stream NDJSON events."""
    raw_prompt = body.prompt
    if not raw_prompt or not raw_prompt.strip():
        raise HTTPException(
            status_code=422,
            detail={"code": "VALIDATION_ERROR", "message": "Nội dung prompt không được để trống."},
        )

    if len(raw_prompt) > settings.max_prompt_chars:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "VALIDATION_ERROR",
                "message": f"Prompt vượt quá độ dài tối đa cho phép ({settings.max_prompt_chars} ký tự).",
            },
        )

    # Resolve run_token from body.run_token or body.env["MF_RUN_TOKEN"]
    run_token = body.run_token
    if not run_token and body.env and "MF_RUN_TOKEN" in body.env:
        run_token = body.env["MF_RUN_TOKEN"]

    # Resolve run_id
    effective_run_id = body.run_id or x_run_id
    try:
        handle = runner.new_handle(effective_run_id)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "RUN_ID_EXISTS", "message": f"Run ID '{effective_run_id}' đang được xử lý."},
        )

    req_data = RunRequestData(
        prompt=raw_prompt,
        session_id=body.session_id,
        run_token=run_token,
        timeout_s=body.timeout_s,
        model=body.model,
        run_id=handle.run_id,
    )

    async def stream_generator():
        gen = runner.stream(req_data, handle)
        try:
            async for event in gen:
                line = json.dumps(event, ensure_ascii=False) + "\n"
                yield line.encode("utf-8")
        except asyncio.CancelledError:
            log.info("Client disconnected from run %s; aborting execution", handle.run_id)
            await runner.abort(handle.run_id)
            raise
        finally:
            with contextlib.suppress(Exception):
                await gen.aclose()

    return StreamingResponse(
        stream_generator(),
        media_type="application/x-ndjson",
        headers={"X-Run-Id": handle.run_id},
    )


@app.post("/abort", dependencies=[Depends(verify_runner_token)])
async def abort(body: AbortRequestSchema):
    """Abort an active or queued run."""
    ok = await runner.abort(body.run_id)
    return {"ok": ok, "run_id": body.run_id}
