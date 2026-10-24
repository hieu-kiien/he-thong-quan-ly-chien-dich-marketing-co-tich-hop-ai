"""Kiểm thử SSE Stream, Threads CRUD, THREAD_BUSY, Stop, Regenerate & Runner Errors (CONTRACT §4, §6)."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Generator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.assistant import chat_service
from app.assistant.runner_client import FakeRunner
from app.models import AiMessage, AiThread, Campaign
from app.models.enums import AiMessageRole, AiMessageStatus


@pytest.fixture
def fake_runner_fixture() -> Generator[FakeRunner, None, None]:
    runner = FakeRunner()
    with patch.object(chat_service, "default_runner", runner):
        yield runner


def parse_sse_events(raw_text: str) -> list[tuple[str, dict]]:
    """Parse output text thành danh sách (event_type, json_data)."""
    events: list[tuple[str, dict]] = []
    for block in raw_text.strip().split("\n\n"):
        block = block.strip()
        if not block or block.startswith(":"):
            continue
        lines = block.splitlines()
        event_name = "message"
        data_str = ""
        for line in lines:
            if line.startswith("event: "):
                event_name = line[7:].strip()
            elif line.startswith("data: "):
                data_str = line[6:].strip()
        if data_str:
            try:
                events.append((event_name, json.loads(data_str)))
            except json.JSONDecodeError:
                continue
    return events


def test_threads_crud(
    client: TestClient,
    marketer1_headers: dict[str, str],
    sample_campaign: Campaign,
):
    # 1. Tạo phiên mới
    resp = client.post(
        "/api/v1/assistant/threads",
        json={"title": "Chiến dịch cà phê", "campaign_id": sample_campaign.id},
        headers=marketer1_headers,
    )
    assert resp.status_code == 201
    thread_data = resp.json()
    thread_id = thread_data["id"]
    assert thread_data["title"] == "Chiến dịch cà phê"
    assert thread_data["campaign_id"] == sample_campaign.id

    # 2. Xem chi tiết
    resp = client.get(f"/api/v1/assistant/threads/{thread_id}", headers=marketer1_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == thread_id

    # 3. Danh sách phiên & tìm kiếm q
    resp = client.get("/api/v1/assistant/threads?q=cà phê", headers=marketer1_headers)
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 1
    assert items[0]["id"] == thread_id

    # 4. Sửa phiên (ghim phiên)
    resp = client.patch(
        f"/api/v1/assistant/threads/{thread_id}",
        json={"pinned": True, "title": "Chiến dịch cà phê (Đã ghim)"},
        headers=marketer1_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["pinned"] is True

    # 5. Xoá phiên
    resp = client.delete(f"/api/v1/assistant/threads/{thread_id}", headers=marketer1_headers)
    assert resp.status_code == 204

    # Xác nhận đã xoá
    resp = client.get(f"/api/v1/assistant/threads/{thread_id}", headers=marketer1_headers)
    assert resp.status_code == 404


def test_sse_happy_path(
    client: TestClient,
    marketer1_headers: dict[str, str],
    fake_runner_fixture: FakeRunner,
    db: Session,
):
    runner = fake_runner_fixture
    # Thiết lập chuỗi sự kiện NDJSON của runner
    runner.set_events([
        {"type": "run", "run_id": "run_test_123"},
        {"type": "queued", "position": 1},
        {"type": "session", "id": "ses_opencode_456"},
        {"type": "text", "text": "Chào bạn! "},
        {"type": "text", "text": "Dưới đây là ý tưởng marketing."},
        {"type": "done", "model": "test-zen-model", "latency_ms": 1250},
    ])

    # 1. Tạo thread mặc định "Phiên mới"
    t_resp = client.post("/api/v1/assistant/threads", json={}, headers=marketer1_headers)
    thread_id = t_resp.json()["id"]

    # 2. Gửi tin nhắn và nhận stream SSE
    resp = client.post(
        f"/api/v1/assistant/threads/{thread_id}/messages",
        json={"content": "Gợi ý cho tôi 3 ý tưởng quảng cáo Facebook"},
        headers=marketer1_headers,
    )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]

    events = parse_sse_events(resp.text)
    event_names = [e[0] for e in events]

    assert "message_start" in event_names
    assert "status" in event_names
    assert "text" in event_names
    assert "message_end" in event_names

    # Kiểm tra nội dung text tích luỹ
    text_events = [e[1]["content"] for e in events if e[0] == "text"]
    assert "Chào bạn! Dưới đây là ý tưởng marketing." in text_events[-1]

    # Kiểm tra DB
    db_thread = db.get(AiThread, thread_id)
    assert db_thread is not None
    assert db_thread.opencode_session_id == "ses_opencode_456"
    # Tiêu đề được tự động đổi từ "Phiên mới" thành câu hỏi
    assert "Gợi ý cho tôi" in db_thread.title

    db_messages = db.query(AiMessage).filter(AiMessage.thread_id == thread_id).order_by(AiMessage.id).all()
    assert len(db_messages) == 2
    assert db_messages[0].role == AiMessageRole.USER
    assert db_messages[1].role == AiMessageRole.ASSISTANT
    assert db_messages[1].status == AiMessageStatus.COMPLETE
    assert db_messages[1].content == "Chào bạn! Dưới đây là ý tưởng marketing."
    assert db_messages[1].model == "test-zen-model"
    assert db_messages[1].latency_ms == 1250


def test_sse_runner_error(
    client: TestClient,
    marketer1_headers: dict[str, str],
    fake_runner_fixture: FakeRunner,
    db: Session,
):
    runner = fake_runner_fixture
    runner.set_events([
        {"type": "run", "run_id": "run_err_1"},
        {"type": "error", "code": "AI_RATE_LIMITED", "message": "Dịch vụ AI miễn phí đang bị giới hạn lượt dùng."},
    ])

    t_resp = client.post("/api/v1/assistant/threads", json={"title": "Test Error"}, headers=marketer1_headers)
    thread_id = t_resp.json()["id"]

    resp = client.post(
        f"/api/v1/assistant/threads/{thread_id}/messages",
        json={"content": "Viết email marketing"},
        headers=marketer1_headers,
    )
    assert resp.status_code == 200
    events = parse_sse_events(resp.text)
    err_events = [e for e in events if e[0] == "error"]
    assert len(err_events) == 1
    assert err_events[0][1]["code"] == "AI_RATE_LIMITED"

    # Kiểm tra DB lưu trạng thái ERROR
    asst_msg = (
        db.query(AiMessage)
        .filter(AiMessage.thread_id == thread_id, AiMessage.role == AiMessageRole.ASSISTANT)
        .first()
    )
    assert asst_msg is not None
    assert asst_msg.status == AiMessageStatus.ERROR
    assert asst_msg.error_code == "AI_RATE_LIMITED"


def test_thread_busy_conflict(
    client: TestClient,
    marketer1_headers: dict[str, str],
    db: Session,
):
    t_resp = client.post("/api/v1/assistant/threads", json={"title": "Test Busy"}, headers=marketer1_headers)
    thread_id = t_resp.json()["id"]

    # Giả lập lock đang chạy trên thread này
    asyncio.run(chat_service.register_turn(thread_id, 9999))
    try:
        resp = client.post(
            f"/api/v1/assistant/threads/{thread_id}/messages",
            json={"content": "Tin nhắn khi đang bận"},
            headers=marketer1_headers,
        )
        assert resp.status_code == 409
        data = resp.json()
        assert data["detail"]["code"] == "THREAD_BUSY"
    finally:
        asyncio.run(chat_service.unregister_turn(thread_id))


def test_stop_endpoint(
    client: TestClient,
    marketer1_headers: dict[str, str],
    db: Session,
):
    t_resp = client.post("/api/v1/assistant/threads", json={"title": "Test Stop"}, headers=marketer1_headers)
    thread_id = t_resp.json()["id"]

    # Gọi stop khi không có turn nào đang chạy
    resp = client.post(f"/api/v1/assistant/threads/{thread_id}/stop", headers=marketer1_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "not_running"


def test_regenerate_endpoint(
    client: TestClient,
    marketer1_headers: dict[str, str],
    fake_runner_fixture: FakeRunner,
    db: Session,
):
    fake_runner_fixture.set_events([
        {"type": "text", "text": "Nội dung phản hồi mới sau khi tạo lại."},
        {"type": "done", "model": "test-zen", "latency_ms": 500},
    ])

    t_resp = client.post("/api/v1/assistant/threads", json={"title": "Test Regenerate"}, headers=marketer1_headers)
    thread_id = t_resp.json()["id"]

    # Tạo cặp message trước đó
    user_msg = AiMessage(
        thread_id=thread_id,
        role=AiMessageRole.USER,
        content="Hãy viết 1 đoạn slogan",
        status=AiMessageStatus.COMPLETE,
    )
    asst_msg = AiMessage(
        thread_id=thread_id,
        role=AiMessageRole.ASSISTANT,
        content="Đoạn slogan cũ",
        status=AiMessageStatus.COMPLETE,
    )
    db.add_all([user_msg, asst_msg])
    db.commit()

    # Gọi regenerate trên asst_msg
    resp = client.post(f"/api/v1/assistant/messages/{asst_msg.id}/regenerate", headers=marketer1_headers)
    assert resp.status_code == 200
    events = parse_sse_events(resp.text)
    assert any(e[0] == "text" for e in events)


def test_status_endpoint(
    client: TestClient,
    marketer1_headers: dict[str, str],
    fake_runner_fixture: FakeRunner,
):
    resp = client.get("/api/v1/assistant/status", headers=marketer1_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "available" in data
    assert "runner" in data
    assert data["available"] is True
    assert "AI_RUNNER_TOKEN" not in resp.text
