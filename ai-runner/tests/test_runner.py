"""Unit tests for Runner core engine using fake_opencode."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from app.config import Settings
from app.events import AI_EMPTY_RESPONSE, AI_RATE_LIMITED, AI_TIMEOUT, TurnState, parse_line
from app.runner import Runner, RunRequestData

FAKE_BIN = str(Path(__file__).parent / "fake_opencode.py")


def make_runner(
    timeout_s: float = 5.0,
    concurrency: int = 1,
    fallback_models: list[str] | None = None,
) -> Runner:
    settings = Settings(
        opencode_bin=FAKE_BIN,
        timeout_s=timeout_s,
        concurrency=concurrency,
        fallback_models=fallback_models or [],
        kill_grace_s=0.2,
    )
    return Runner(settings)


@pytest.mark.asyncio
async def test_probe_version():
    runner = make_runner()
    version = await runner.probe_version()
    assert version == "opencode 1.19.0"
    assert runner.opencode_version == "opencode 1.19.0"


@pytest.mark.asyncio
async def test_success_run():
    runner = make_runner()
    handle = runner.new_handle("test_run_success")
    req = RunRequestData(prompt="Xin chào")
    events = [e async for e in runner.stream(req, handle)]

    types = [e["type"] for e in events]
    assert types[0] == "run"
    assert "session" in types
    assert "text" in types
    assert "done" in types

    text_ev = next(e for e in events if e["type"] == "text")
    assert "Xin chào" in text_ev["text"]
    done_ev = next(e for e in events if e["type"] == "done")
    assert done_ev["latency_ms"] >= 0


@pytest.mark.asyncio
async def test_tool_calling_run():
    runner = make_runner()
    handle = runner.new_handle("test_run_tool")
    req = RunRequestData(prompt="Cho tôi số liệu tool chiến dịch #5")
    events = [e async for e in runner.stream(req, handle)]

    types = [e["type"] for e in events]
    assert "tool" in types
    assert "text" in types
    assert "done" in types

    tool_ev = next(e for e in events if e["type"] == "tool")
    assert tool_ev["name"] == "get_campaign_stats"  # stripped prefix
    assert tool_ev["status"] == "done"
    assert tool_ev["input"] == {"campaign_id": 5}


@pytest.mark.asyncio
async def test_freetier_rate_limited():
    runner = make_runner()
    handle = runner.new_handle("test_run_freetier")
    req = RunRequestData(prompt="Hãy giả lập freetier")
    events = [e async for e in runner.stream(req, handle)]

    err_ev = next((e for e in events if e["type"] == "error"), None)
    assert err_ev is not None
    assert err_ev["code"] == AI_RATE_LIMITED
    assert "giới hạn" in err_ev["message"].lower() or "free" in err_ev.get("detail", "").lower()


@pytest.mark.asyncio
async def test_usage_limit_in_logs_fails_fast_and_cools_down():
    # opencode only logs "Free usage limit reached" on stderr and then retries forever.
    runner = make_runner(timeout_s=20.0, fallback_models=["opencode/glm-5.3-flash-free"])
    loop = asyncio.get_running_loop()

    started = loop.time()
    handle = runner.new_handle("test_usage_limit_1")
    events = [e async for e in runner.stream(RunRequestData(prompt="usagelimit"), handle)]
    elapsed = loop.time() - started

    err_ev = next(e for e in events if e["type"] == "error")
    assert err_ev["code"] == AI_RATE_LIMITED
    assert elapsed < 10, f"should fail fast, took {elapsed:.1f}s"  # no fallback, no timeout wait
    assert runner.cooldown_remaining_s > 0

    # During cooldown the runner answers immediately without spawning opencode.
    started = loop.time()
    handle2 = runner.new_handle("test_usage_limit_2")
    events2 = [e async for e in runner.stream(RunRequestData(prompt="Xin chào"), handle2)]
    assert [e["type"] for e in events2] == ["run", "error"]
    assert events2[1]["code"] == AI_RATE_LIMITED
    assert "cooldown" in events2[1].get("detail", "")
    assert loop.time() - started < 1


@pytest.mark.asyncio
async def test_hang_timeout():
    # Set short timeout so test finishes quickly
    runner = make_runner(timeout_s=0.5)
    handle = runner.new_handle("test_run_hang")
    req = RunRequestData(prompt="hang immediately", timeout_s=0.5)
    events = [e async for e in runner.stream(req, handle)]

    err_ev = next((e for e in events if e["type"] == "error"), None)
    assert err_ev is not None
    assert err_ev["code"] == AI_TIMEOUT


@pytest.mark.asyncio
async def test_empty_response():
    runner = make_runner()
    handle = runner.new_handle("test_run_empty")
    req = RunRequestData(prompt="empty response")
    events = [e async for e in runner.stream(req, handle)]

    err_ev = next((e for e in events if e["type"] == "error"), None)
    assert err_ev is not None
    assert err_ev["code"] == AI_EMPTY_RESPONSE


@pytest.mark.asyncio
async def test_abort_active_run():
    runner = make_runner()
    handle = runner.new_handle("test_run_abort")
    req = RunRequestData(prompt="hang to allow abort", timeout_s=5.0)

    async def consume():
        evs = []
        async for e in runner.stream(req, handle):
            evs.append(e)
        return evs

    task = asyncio.create_task(consume())
    await asyncio.sleep(0.1)

    aborted = await runner.abort("test_run_abort")
    assert aborted is True

    events = await task
    err_ev = next((e for e in events if e["type"] == "error"), None)
    assert err_ev is not None
    assert err_ev["code"] == "AI_ABORTED"


@pytest.mark.asyncio
async def test_queue_ordering():
    # Concurrency 1: run2 must be queued behind run1
    runner = make_runner(concurrency=1)
    h1 = runner.new_handle("run_1")
    h2 = runner.new_handle("run_2")

    r1_events = []
    r2_events = []

    async def worker1():
        async for e in runner.stream(RunRequestData(prompt="slow run 1"), h1):
            r1_events.append(e)

    async def worker2():
        async for e in runner.stream(RunRequestData(prompt="slow run 2"), h2):
            r2_events.append(e)

    t1 = asyncio.create_task(worker1())
    await asyncio.sleep(0.05)
    t2 = asyncio.create_task(worker2())

    await asyncio.gather(t1, t2)

    # h2 must have received a queued event with position 1
    queued_events = [e for e in r2_events if e.get("type") == "queued"]
    assert len(queued_events) >= 1
    assert queued_events[0]["position"] == 1


@pytest.mark.asyncio
async def test_model_fallback_on_error():
    # When primary model fails, runner falls back to secondary model
    runner = make_runner(fallback_models=["opencode/glm-5.3-flash-free"])
    handle = runner.new_handle("run_fallback")
    req = RunRequestData(prompt="test fallback", model="opencode/bad-model")
    events = [e async for e in runner.stream(req, handle)]

    types = [e["type"] for e in events]
    assert "done" in types
    done_ev = next(e for e in events if e["type"] == "done")
    assert done_ev["model"] == "opencode/glm-5.3-flash-free"


@pytest.mark.asyncio
async def test_stale_session_retry():
    runner = make_runner()
    handle = runner.new_handle("run_stale_sess")
    req = RunRequestData(prompt="retry without session", session_id="ses_stale_123")
    events = [e async for e in runner.stream(req, handle)]

    types = [e["type"] for e in events]
    assert "done" in types
    done_ev = next(e for e in events if e["type"] == "done")
    assert done_ev["session_id"] == "ses_test_simple_123"


def test_parse_line_text_delta_and_step():
    state = TurnState()
    ev_step = parse_line('{"type":"step_start","sessionID":"ses_1"}', state)
    assert ev_step == [{"type": "session", "id": "ses_1"}, {"type": "step"}]

    ev_d1 = parse_line('{"type":"text_delta","sessionID":"ses_1","partID":"p1","delta":"Xin "}', state)
    assert ev_d1 == [{"type": "text_delta", "part_id": "p1", "delta": "Xin "}]
    assert state.has_text is True
    assert state.emitted_output is True

    ev_final = parse_line('{"type":"text","sessionID":"ses_1","part":{"id":"p1","text":"Xin chào"}}', state)
    assert ev_final == [{"type": "text", "text": "Xin chào"}]
    assert "p1" not in state.part_deltas
    assert state.texts == ["Xin chào"]

