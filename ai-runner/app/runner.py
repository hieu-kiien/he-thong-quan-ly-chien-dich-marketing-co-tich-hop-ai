"""Process management: FIFO queue with bounded concurrency, one `opencode run` process
per attempt, hard timeout, abort, model fallback and stale-session retry."""

from __future__ import annotations

import asyncio
import collections
import contextlib
import logging
import os
import signal
import subprocess
import time
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import Settings
from .events import (
    AI_ABORTED,
    AI_BUSY,
    AI_EMPTY_RESPONSE,
    AI_RATE_LIMITED,
    AI_TIMEOUT,
    AI_UNAVAILABLE,
    TurnState,
    error_event,
    is_model_error,
    is_rate_limited,
    is_session_error,
    parse_line,
)

log = logging.getLogger("ai_runner")

STREAM_LIMIT = 16 * 1024 * 1024  # max bytes per JSONL line (tool outputs can be large)
_BASE_ENV_KEYS = (
    "PATH",
    "HOME",
    "XDG_CONFIG_HOME",
    "XDG_DATA_HOME",
    "XDG_CACHE_HOME",
    "XDG_STATE_HOME",
    "TMPDIR",
    # Windows (local development / tests only)
    "SYSTEMROOT",
    "SYSTEMDRIVE",
    "TEMP",
    "TMP",
    "USERPROFILE",
    "APPDATA",
    "LOCALAPPDATA",
    "COMSPEC",
    "PATHEXT",
)


@dataclass
class RunRequestData:
    prompt: str
    session_id: str | None = None
    run_token: str | None = None
    timeout_s: float | None = None
    model: str | None = None
    run_id: str | None = None


@dataclass
class RunHandle:
    run_id: str
    created: float = field(default_factory=time.monotonic)
    aborted: bool = False
    acquired: bool = False
    proc: asyncio.subprocess.Process | None = None
    model: str | None = None


@dataclass
class _Attempt:
    rc: int | None = None
    timed_out: bool = False
    stderr_tail: str = ""


class QueueFullError(Exception):
    pass


class Runner:
    def __init__(self, settings: Settings) -> None:
        self.s = settings
        self._cond: asyncio.Condition | None = None
        self._active = 0
        self._waiting: list[RunHandle] = []
        self.runs: dict[str, RunHandle] = {}
        self.opencode_version: str | None = None
        self.last_error: str | None = None

    # ------------------------------------------------------------------ info
    @property
    def cond(self) -> asyncio.Condition:
        if self._cond is None:
            self._cond = asyncio.Condition()
        return self._cond

    @property
    def queue_length(self) -> int:
        return len(self._waiting)

    @property
    def active(self) -> int:
        return self._active

    def agent_file(self) -> Path | None:
        base = Path(self.s.sandbox_dir) / ".opencode"
        for sub in ("agent", "agents"):
            candidate = base / sub / f"{self.s.agent}.md"
            if candidate.is_file():
                return candidate
        return None

    async def probe_version(self) -> str | None:
        """`opencode --version` — cheap health probe that never calls a model."""
        try:
            proc = await asyncio.create_subprocess_exec(
                *self.s.opencode_cmd,
                "--version",
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.s.sandbox_dir,
                env=self._child_env(None),
            )
            out, _ = await asyncio.wait_for(proc.communicate(), timeout=20)
            version = out.decode("utf-8", "replace").strip().splitlines()
            self.opencode_version = version[-1] if version and proc.returncode == 0 else None
        except (OSError, asyncio.TimeoutError) as exc:
            log.warning("opencode --version failed: %s", exc)
            self.opencode_version = None
        return self.opencode_version

    # ----------------------------------------------------------------- abort
    async def abort(self, run_id: str) -> bool:
        handle = self.runs.get(run_id)
        if handle is None:
            return False
        handle.aborted = True
        if handle.proc is not None and handle.proc.returncode is None:
            asyncio.get_running_loop().create_task(self._terminate(handle.proc))
        async with self.cond:
            self.cond.notify_all()
        return True

    # ------------------------------------------------------------------ main
    def new_handle(self, run_id: str | None) -> RunHandle:
        rid = run_id or uuid.uuid4().hex
        if rid in self.runs:
            raise KeyError(rid)
        handle = RunHandle(run_id=rid)
        self.runs[rid] = handle
        return handle

    async def stream(self, req: RunRequestData, handle: RunHandle) -> AsyncIterator[dict[str, Any]]:
        """Full lifecycle of one /run request as NDJSON-able dicts."""
        yield {"type": "run", "run_id": handle.run_id}
        try:
            try:
                async for event in self._acquire(handle):
                    yield event
            except QueueFullError:
                yield error_event(AI_BUSY)
                return
            if not handle.acquired:
                yield error_event(AI_ABORTED if handle.aborted else AI_BUSY)
                return
            async for event in self._execute(req, handle):
                if event.get("type") == "error":
                    self.last_error = f"{event.get('code')}: {event.get('detail') or event.get('message')}"
                yield event
        finally:
            await self._release(handle)
            self.runs.pop(handle.run_id, None)

    # ----------------------------------------------------------------- queue
    async def _acquire(self, handle: RunHandle) -> AsyncIterator[dict[str, Any]]:
        async with self.cond:
            if self._active < self.s.concurrency and not self._waiting:
                self._active += 1
                handle.acquired = True
                return
            if len(self._waiting) >= self.s.max_queue:
                raise QueueFullError
            self._waiting.append(handle)
        last_pos = None
        queue_deadline = time.monotonic() + max(self.s.timeout_s * 2, 60)
        try:
            while True:
                async with self.cond:
                    if handle.aborted:
                        return
                    if self._waiting and self._waiting[0] is handle and self._active < self.s.concurrency:
                        self._waiting.pop(0)
                        self._active += 1
                        handle.acquired = True
                        self.cond.notify_all()
                        return
                    pos = self._waiting.index(handle) + 1
                if pos != last_pos:
                    last_pos = pos
                    yield {"type": "queued", "position": pos}
                if time.monotonic() > queue_deadline:
                    return
                async with self.cond:
                    with contextlib.suppress(asyncio.TimeoutError):
                        await asyncio.wait_for(self.cond.wait(), timeout=1.0)
        finally:
            if not handle.acquired:
                async with self.cond:
                    if handle in self._waiting:
                        self._waiting.remove(handle)
                    self.cond.notify_all()

    async def _release(self, handle: RunHandle) -> None:
        if handle.proc is not None and handle.proc.returncode is None:
            await self._terminate(handle.proc)
        if handle.acquired:
            handle.acquired = False
            async with self.cond:
                self._active -= 1
                self.cond.notify_all()

    # ------------------------------------------------------------- execution
    def _models(self, override: str | None) -> list[str | None]:
        first = override or self.s.model
        models: list[str | None] = [first]
        for m in self.s.fallback_models:
            if m not in models:
                models.append(m)
        return models

    def _child_env(self, run_token: str | None) -> dict[str, str]:
        env: dict[str, str] = {}
        for key in (*_BASE_ENV_KEYS, *self.s.passthrough_env):
            value = os.environ.get(key)
            if value is not None and key != "RUNNER_TOKEN":
                env[key] = value
        env.setdefault("PATH", "/usr/local/bin:/usr/bin:/bin")
        env["LANG"] = "C.UTF-8"
        env["LC_ALL"] = "C.UTF-8"
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        env["OPENCODE_DISABLE_AUTOUPDATE"] = "1"
        env["MF_RUN_TOKEN"] = run_token or ""
        return env

    def build_cmd(self, model: str | None, session_id: str | None, run_id: str, prompt: str = "") -> list[str]:
        cmd = [*self.s.opencode_cmd, "run", "--agent", self.s.agent, "--format", "json"]
        if self.s.pure:
            cmd.append("--pure")
        if model:
            cmd += ["-m", model]
        if session_id:
            cmd += ["-s", session_id]
        else:
            # An explicit title avoids an extra "title" model call for new sessions.
            cmd += ["--title", f"mf-{run_id[:24]}"]
        if prompt:
            cmd += ["--", prompt]
        return cmd

    async def _execute(self, req: RunRequestData, handle: RunHandle) -> AsyncIterator[dict[str, Any]]:
        started = time.monotonic()
        timeout = min(req.timeout_s or self.s.timeout_s, self.s.timeout_s)
        deadline = started + timeout
        models = self._models(req.model)
        index = 0
        session_id = req.session_id
        session_retry_done = False

        while True:
            model = models[index]
            handle.model = model
            state = TurnState()
            attempt = _Attempt()
            cmd = self.build_cmd(model, session_id, handle.run_id, req.prompt)
            async for event in self._attempt(cmd, req, handle, state, attempt, deadline):
                yield event

            if handle.aborted:
                yield error_event(AI_ABORTED)
                return
            if attempt.timed_out:
                yield error_event(AI_TIMEOUT, detail=f"timeout after {timeout:.0f}s")
                return

            failure_text = f"{state.error_raw or ''}\n{attempt.stderr_tail}"
            failed = state.error_raw is not None or (attempt.rc not in (0, None))

            if failed and not state.emitted_output:
                if session_id and not session_retry_done and is_session_error(failure_text):
                    log.info("run %s: session %s not found, retrying without session", handle.run_id, session_id)
                    session_id = None
                    session_retry_done = True
                    continue
                if (is_rate_limited(failure_text) or is_model_error(failure_text)) and index + 1 < len(models):
                    log.info("run %s: model %s failed (%s); falling back to %s",
                             handle.run_id, model, state.error_short, models[index + 1])
                    index += 1
                    continue

            if failed:
                code = AI_RATE_LIMITED if is_rate_limited(failure_text) else AI_UNAVAILABLE
                detail = state.error_short or attempt.stderr_tail.strip()[-400:] or f"exit code {attempt.rc}"
                yield error_event(code, detail=detail)
                return
            if not state.has_text:
                yield error_event(AI_EMPTY_RESPONSE)
                return
            yield {
                "type": "done",
                "model": model or "default",
                "latency_ms": int((time.monotonic() - started) * 1000),
                "session_id": state.session_id,
                "tokens": state.tokens,
            }
            return

    async def _attempt(
        self,
        cmd: list[str],
        req: RunRequestData,
        handle: RunHandle,
        state: TurnState,
        attempt: _Attempt,
        deadline: float,
    ) -> AsyncIterator[dict[str, Any]]:
        kwargs: dict[str, Any] = {}
        if os.name == "posix":
            kwargs["start_new_session"] = True
        else:  # pragma: no cover - Windows dev only
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        if handle.aborted:
            return
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.s.sandbox_dir,
            env=self._child_env(req.run_token),
            limit=STREAM_LIMIT,
            **kwargs,
        )
        handle.proc = proc
        stderr_buf: collections.deque[bytes] = collections.deque(maxlen=64)
        stderr_task = asyncio.get_running_loop().create_task(self._drain(proc.stderr, stderr_buf))
        try:
            assert proc.stdout is not None
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    attempt.timed_out = True
                    break
                try:
                    raw = await asyncio.wait_for(proc.stdout.readline(), timeout=remaining)
                except asyncio.TimeoutError:
                    attempt.timed_out = True
                    break
                except ValueError:  # line longer than STREAM_LIMIT
                    continue
                if not raw:
                    break
                for event in parse_line(raw.decode("utf-8", "replace"), state):
                    yield event
            if attempt.timed_out:
                await self._terminate(proc)
            else:
                try:
                    await asyncio.wait_for(proc.wait(), timeout=max(1.0, deadline - time.monotonic()))
                except asyncio.TimeoutError:
                    attempt.timed_out = True
                    await self._terminate(proc)
            attempt.rc = proc.returncode
        finally:
            if proc.returncode is None:
                # Client disconnected / generator closed: kill without blocking the caller.
                self._kill_group(proc, signal.SIGKILL if os.name == "posix" else None)
            else:
                # Reap stragglers left in the process group (e.g. helper subprocesses).
                self._kill_group(proc, signal.SIGKILL if os.name == "posix" else None)
            with contextlib.suppress(Exception):
                await asyncio.wait_for(asyncio.shield(stderr_task), timeout=2)
            stderr_task.cancel()
            attempt.stderr_tail = b"".join(stderr_buf).decode("utf-8", "replace")[-4000:]
            handle.proc = None

    @staticmethod
    async def _drain(stream: asyncio.StreamReader | None, buf: collections.deque[bytes]) -> None:
        if stream is None:
            return
        while True:
            chunk = await stream.read(4096)
            if not chunk:
                return
            buf.append(chunk)

    @staticmethod
    def _kill_group(proc: asyncio.subprocess.Process, sig: Any) -> None:
        if os.name == "posix":
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.killpg(proc.pid, sig)
        else:  # pragma: no cover - Windows dev only
            if proc.returncode is None:
                with contextlib.suppress(ProcessLookupError, OSError):
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=False,
                    )

    async def _terminate(self, proc: asyncio.subprocess.Process) -> None:
        """SIGTERM the whole process group, then SIGKILL after the grace period."""
        if proc.returncode is not None:
            return
        self._kill_group(proc, signal.SIGTERM if os.name == "posix" else None)
        try:
            await asyncio.wait_for(proc.wait(), timeout=self.s.kill_grace_s)
        except asyncio.TimeoutError:
            self._kill_group(proc, signal.SIGKILL if os.name == "posix" else None)
            with contextlib.suppress(asyncio.TimeoutError):
                await asyncio.wait_for(proc.wait(), timeout=5)
