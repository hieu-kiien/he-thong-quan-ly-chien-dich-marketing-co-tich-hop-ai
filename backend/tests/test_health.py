"""Test /health endpoint (CONTRACT §4)."""

from __future__ import annotations

import httpx
from fastapi.testclient import TestClient

from app.core.config import settings


def test_health_check_healthy(client: TestClient):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["db"] == "ok"
    assert data["ai_runner"] == "unknown"  # AI_RUNNER_URL not set
    assert data["status"] == "ok"


def test_health_check_with_runner(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "AI_RUNNER_URL", "http://127.0.0.1:8100")
    monkeypatch.setattr(settings, "AI_RUNNER_TOKEN", "test-token")

    async def mock_get(self, url, headers=None):
        class MockResp:
            status_code = 200
        return MockResp()

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["db"] == "ok"
    assert data["ai_runner"] == "ok"
    assert data["status"] == "ok"


def test_health_check_runner_degraded(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "AI_RUNNER_URL", "http://127.0.0.1:8100")

    async def mock_get(self, url, headers=None):
        raise httpx.ConnectError("Connection refused")

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["db"] == "ok"
    assert data["ai_runner"] == "error"
    assert data["status"] == "degraded"
