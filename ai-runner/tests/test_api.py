"""API integration tests for MarketFlow ai-runner FastAPI endpoints."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from app.config import Settings

from app.main import app, runner

FAKE_BIN = str(Path(__file__).parent / "fake_opencode.py")


@pytest.fixture(autouse=True)
def setup_test_runner(monkeypatch):
    test_settings = Settings(
        runner_token="test_secret_token",
        opencode_bin=FAKE_BIN,
        timeout_s=5.0,
        concurrency=1,
        kill_grace_s=0.2,
    )
    runner.s = test_settings
    runner.opencode_version = "opencode 1.19.0"
    runner.last_error = None
    runner.runs.clear()


@pytest.mark.asyncio
async def test_health_endpoint():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["opencode_version"] == "opencode 1.19.0"
        assert data["queue_length"] == 0


@pytest.mark.asyncio
async def test_run_auth_unauthorized():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/run", json={"prompt": "test"})
        assert resp.status_code == 401
        assert resp.json()["detail"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_run_validation_empty_prompt():
    headers = {"X-Runner-Token": "test_secret_token"}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/run", json={"prompt": "   "}, headers=headers)
        assert resp.status_code == 422
        assert resp.json()["detail"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_run_streaming_success():
    headers = {"X-Runner-Token": "test_secret_token", "X-Run-Id": "run_stream_test_1"}
    body = {
        "prompt": "Gợi ý bài viết",
        "env": {"MF_RUN_TOKEN": "valid_mock_jwt"},
    }
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/run", json=body, headers=headers)
        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("application/x-ndjson")
        assert resp.headers.get("x-run-id") == "run_stream_test_1"

        lines = [line.strip() for line in resp.text.splitlines() if line.strip()]
        events = [json.loads(line) for line in lines]

        types = [e["type"] for e in events]
        assert types[0] == "run"
        assert "text" in types
        assert "done" in types


@pytest.mark.asyncio
async def test_run_conflict_duplicate_id():
    runner.new_handle("duplicate_id")
    headers = {"X-Runner-Token": "test_secret_token"}
    body = {"prompt": "Xin chào", "run_id": "duplicate_id"}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/run", json=body, headers=headers)
        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "RUN_ID_EXISTS"


@pytest.mark.asyncio
async def test_abort_endpoint():
    headers = {"X-Runner-Token": "test_secret_token"}
    handle = runner.new_handle("run_to_abort")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/abort", json={"run_id": "run_to_abort"}, headers=headers)
        assert resp.status_code == 200
        assert resp.json() == {"ok": True, "run_id": "run_to_abort"}
        assert handle.aborted is True
