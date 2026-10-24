"""Client kết nối tới dịch vụ nội bộ ai-runner (CONTRACT §7) và FakeRunner cho testing."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class RunnerClient:
    """Client giao tiếp với ai-runner nội bộ qua giao thức HTTP / NDJSON stream."""

    def __init__(self, base_url: str | None = None, token: str | None = None) -> None:
        self.base_url = (base_url or settings.AI_RUNNER_URL or "").rstrip("/")
        self.token = token or settings.AI_RUNNER_TOKEN or ""

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url)

    def _headers(self, run_id: str | None = None) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self.token:
            headers["X-Runner-Token"] = self.token
        if run_id:
            headers["X-Run-Id"] = run_id
        return headers

    async def health(self) -> dict[str, Any]:
        """Gọi GET /health trên ai-runner."""
        if not self.is_configured:
            return {"ok": False, "error": "Chưa cấu hình AI_RUNNER_URL"}
        try:
            url = f"{self.base_url}/health"
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(url, headers=self._headers())
                if resp.status_code == 200:
                    return resp.json()
                return {"ok": False, "status_code": resp.status_code, "text": resp.text[:200]}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    async def abort(self, run_id: str) -> bool:
        """Gửi yêu cầu huỷ lượt đang chạy tới ai-runner."""
        if not self.is_configured or not run_id:
            return False
        try:
            url = f"{self.base_url}/abort"
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.post(url, json={"run_id": run_id}, headers=self._headers())
                return resp.status_code == 200
        except Exception as exc:  # noqa: BLE001
            logger.warning("Lỗi khi gửi yêu cầu abort tới ai-runner: %s", exc)
            return False

    async def stream_run(
        self,
        prompt: str,
        session_id: str | None,
        run_token: str,
        run_id: str | None = None,
        timeout_s: float = 150.0,
    ) -> AsyncIterator[dict[str, Any]]:
        """Gọi POST /run và stream các sự kiện NDJSON từ ai-runner."""
        if not self.is_configured:
            yield {
                "type": "error",
                "code": "AI_UNAVAILABLE",
                "message": "Hệ thống chưa kết nối dịch vụ AI. Vui lòng liên hệ quản trị viên.",
            }
            return

        payload: dict[str, Any] = {
            "prompt": prompt,
            "session_id": session_id,
            "env": {"MF_RUN_TOKEN": run_token},
            "timeout_s": int(timeout_s),
        }

        url = f"{self.base_url}/run"
        try:
            # Cho phép httpx timeout dài hơn một chút so với runner timeout
            client_timeout = httpx.Timeout(timeout_s + 10.0, connect=5.0)
            async with (
                httpx.AsyncClient(timeout=client_timeout) as client,
                client.stream("POST", url, json=payload, headers=self._headers(run_id)) as response,
            ):
                if response.status_code != 200:
                    err_text = await response.aread()
                    yield {
                        "type": "error",
                        "code": "AI_UNAVAILABLE",
                        "message": "Dịch vụ AI phản hồi lỗi kết nối.",
                        "detail": err_text.decode("utf-8", errors="replace")[:300],
                    }
                    return

                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                        if isinstance(event, dict):
                            yield event
                    except json.JSONDecodeError:
                        logger.warning("Không thể parse dòng NDJSON từ ai-runner: %s", line[:100])
        except httpx.TimeoutException:
            yield {
                "type": "error",
                "code": "AI_TIMEOUT",
                "message": "Trợ lý AI phản hồi quá thời gian cho phép. Vui lòng thử lại.",
            }
        except Exception as exc:  # noqa: BLE001
            logger.error("Lỗi kết nối tới ai-runner: %s", exc)
            yield {
                "type": "error",
                "code": "AI_UNAVAILABLE",
                "message": "Không kết nối được tới dịch vụ AI. Vui lòng thử lại sau.",
                "detail": str(exc)[:300],
            }


class FakeRunner:
    """Mock runner cho testing: scriptable sequences và mô phỏng tương tác MCP."""

    def __init__(self, events: list[dict[str, Any]] | None = None) -> None:
        self.events: list[dict[str, Any]] = list(events or [])
        self.aborted_runs: list[str] = []
        self.health_response: dict[str, Any] = {
            "ok": True,
            "opencode_version": "1.19.0",
            "model": "fake-model",
            "queue_length": 0,
            "active": 0,
            "last_error": None,
        }
        self.on_run_hook: Any = None

    def set_events(self, events: list[dict[str, Any]]) -> None:
        self.events = list(events)

    async def health(self) -> dict[str, Any]:
        return dict(self.health_response)

    async def abort(self, run_id: str) -> bool:
        self.aborted_runs.append(run_id)
        return True

    async def stream_run(
        self,
        prompt: str,
        session_id: str | None,
        run_token: str,
        run_id: str | None = None,
        timeout_s: float = 150.0,
    ) -> AsyncIterator[dict[str, Any]]:
        if self.on_run_hook:
            await self.on_run_hook(prompt, session_id, run_token, run_id)
        for ev in self.events:
            yield dict(ev)


# Singleton mặc định cho ứng dụng
default_runner = RunnerClient()
