"""Kiểm thử xác nhận & từ chối đề xuất AI (CONTRACT §4, §5, §12)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.assistant import actions_service
from app.core.errors import Conflict, PermissionDenied
from app.core.timeutil import now_utc
from app.models import (
    AiAction,
    AiMessage,
    AiThread,
    Campaign,
    Content,
    Notification,
    User,
)
from app.models.enums import (
    AiActionStatus,
    AiMessageRole,
    AiMessageStatus,
    ContentOrigin,
    ContentStatus,
    ContentType,
)


@pytest.fixture
def test_action_fixture(
    db: Session,
    marketer1_user: User,
    sample_campaign: Campaign,
) -> tuple[AiThread, AiMessage, AiAction]:
    thread = AiThread(
        user_id=marketer1_user.id,
        campaign_id=sample_campaign.id,
        title="Phiên kiểm thử Actions",
        last_message_at=now_utc(),
    )
    db.add(thread)
    db.flush()

    message = AiMessage(
        thread_id=thread.id,
        role=AiMessageRole.ASSISTANT,
        content="Đã tạo đề xuất",
        status=AiMessageStatus.COMPLETE,
    )
    db.add(message)
    db.flush()

    action = AiAction(
        thread_id=thread.id,
        message_id=message.id,
        user_id=marketer1_user.id,
        tool="propose_content_drafts",
        args_json={
            "items": [
                {
                    "campaign_id": sample_campaign.id,
                    "channel_code": "FACEBOOK",
                    "content_type": ContentType.SOCIAL_POST.value,
                    "title": "Bài viết Cold Brew Thơm Ngon",
                    "body": "Đậm đà từng giọt cà phê ủ lạnh...",
                    "cta": "Mua 1 tặng 1",
                    "status": "PENDING_REVIEW",
                }
            ]
        },
        summary="Đề xuất tạo 1 bản nháp nội dung",
        status=AiActionStatus.PROPOSED,
    )
    db.add(action)
    db.commit()
    db.refresh(thread)
    db.refresh(message)
    db.refresh(action)
    return thread, message, action


def test_confirm_content_drafts_success(
    db: Session,
    marketer1_user: User,
    manager_user: User,
    test_action_fixture: tuple[AiThread, AiMessage, AiAction],
):
    _, message, action = test_action_fixture

    # Confirm action as marketer1_user
    confirmed = actions_service.confirm(db, marketer1_user, action.id)

    assert confirmed.status == AiActionStatus.EXECUTED
    assert confirmed.executed_at is not None
    assert confirmed.result_json is not None
    assert "contents" in confirmed.result_json
    assert len(confirmed.result_json["contents"]) == 1

    content_item = confirmed.result_json["contents"][0]
    content_id = content_item["id"]
    assert content_item["link"] == f"/contents/{content_id}"
    assert content_item["status"] == "PENDING_REVIEW"

    # Verify content in DB has origin=AI and correct ai_message_id
    created = db.get(Content, content_id)
    assert created is not None
    assert created.origin == ContentOrigin.AI
    assert created.ai_message_id == message.id
    assert created.status == ContentStatus.PENDING_REVIEW
    assert created.title == "Bài viết Cold Brew Thơm Ngon"

    # Verify notification sent to manager
    notif = db.query(Notification).filter(Notification.user_id == manager_user.id).first()
    assert notif is not None
    assert "gửi duyệt nội dung" in notif.message


def test_confirm_non_owner_forbidden(
    db: Session,
    marketer2_user: User,
    test_action_fixture: tuple[AiThread, AiMessage, AiAction],
):
    _, _, action = test_action_fixture

    # Marketer 2 tries to confirm Marketer 1's action -> PermissionDenied (403)
    with pytest.raises(PermissionDenied):
        actions_service.confirm(db, marketer2_user, action.id)


def test_manager_cannot_confirm_or_see_others_actions(
    db: Session,
    manager_user: User,
    test_action_fixture: tuple[AiThread, AiMessage, AiAction],
):
    _, _, action = test_action_fixture

    # Phiên chat là riêng tư: Quản lý cũng không được xác nhận/từ chối hay xem đề xuất của người khác
    with pytest.raises(PermissionDenied):
        actions_service.confirm(db, manager_user, action.id)
    with pytest.raises(PermissionDenied):
        actions_service.reject(db, manager_user, action.id)
    assert actions_service.list_actions(db, manager_user) == []
    assert db.get(AiAction, action.id).status == AiActionStatus.PROPOSED


def test_double_confirm_conflict(
    db: Session,
    marketer1_user: User,
    test_action_fixture: tuple[AiThread, AiMessage, AiAction],
):
    _, _, action = test_action_fixture

    # First confirm succeeds
    actions_service.confirm(db, marketer1_user, action.id)

    # Second confirm -> Conflict (409)
    with pytest.raises(Conflict):
        actions_service.confirm(db, marketer1_user, action.id)


def test_confirm_with_args_override(
    db: Session,
    marketer1_user: User,
    sample_campaign: Campaign,
    test_action_fixture: tuple[AiThread, AiMessage, AiAction],
):
    _, _, action = test_action_fixture

    # Override title and set status to DRAFT
    override = {
        "items": [
            {
                "campaign_id": sample_campaign.id,
                "channel_code": "FACEBOOK",
                "content_type": ContentType.SOCIAL_POST.value,
                "title": "Tiêu đề đã được sửa bởi người dùng",
                "body": "Nội dung giữ nguyên",
                "cta": None,
                "status": "DRAFT",
            }
        ]
    }
    confirmed = actions_service.confirm(db, marketer1_user, action.id, args_override=override)

    content_id = confirmed.result_json["contents"][0]["id"]
    created = db.get(Content, content_id)
    assert created.title == "Tiêu đề đã được sửa bởi người dùng"
    assert created.status == ContentStatus.DRAFT


def test_reject_action(
    db: Session,
    marketer1_user: User,
    marketer2_user: User,
    test_action_fixture: tuple[AiThread, AiMessage, AiAction],
):
    _, _, action = test_action_fixture

    # Marketer 2 cannot reject
    with pytest.raises(PermissionDenied):
        actions_service.reject(db, marketer2_user, action.id)

    # Marketer 1 rejects
    rejected = actions_service.reject(db, marketer1_user, action.id)
    assert rejected.status == AiActionStatus.REJECTED

    # Cannot reject again
    with pytest.raises(Conflict):
        actions_service.reject(db, marketer1_user, action.id)


def test_actions_api_endpoints(
    client: TestClient,
    marketer1_headers: dict[str, str],
    marketer2_headers: dict[str, str],
    test_action_fixture: tuple[AiThread, AiMessage, AiAction],
):
    thread, _, action = test_action_fixture

    # 1. GET /assistant/actions
    resp = client.get("/api/v1/assistant/actions", headers=marketer1_headers)
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 1
    assert items[0]["id"] == action.id

    # Filter by thread_id
    resp = client.get(f"/api/v1/assistant/actions?thread_id={thread.id}", headers=marketer1_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # 2. POST /assistant/actions/{id}/confirm as non-owner -> 403
    resp = client.post(f"/api/v1/assistant/actions/{action.id}/confirm", headers=marketer2_headers)
    assert resp.status_code == 403

    # 3. POST /assistant/actions/{id}/confirm as owner -> 200
    resp = client.post(f"/api/v1/assistant/actions/{action.id}/confirm", headers=marketer1_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "EXECUTED"
    assert "contents" in data["result_json"]


def test_confirm_validation_error_keeps_proposal_editable(
    db: Session,
    marketer1_user: User,
    test_action_fixture: tuple[AiThread, AiMessage, AiAction],
):
    """Gõ sai dữ liệu khi sửa thẻ đề xuất không được khoá thẻ vĩnh viễn: sửa lại rồi xác nhận được."""
    from app.core.errors import ValidationFailed

    _, _, action = test_action_fixture
    bad = {"items": [{**action.args_json["items"][0], "channel_code": "KENH_KHONG_TON_TAI"}]}

    with pytest.raises(ValidationFailed):
        actions_service.confirm(db, marketer1_user, action.id, args_override=bad)

    db.refresh(action)
    assert action.status == AiActionStatus.PROPOSED
    assert action.error  # hiển thị lý do cho người dùng
    assert db.query(Content).filter(Content.ai_message_id == action.message_id).count() == 0

    fixed = actions_service.confirm(db, marketer1_user, action.id)
    assert fixed.status == AiActionStatus.EXECUTED
    assert fixed.error is None


def test_confirm_metrics_validates_all_rows_before_writing(
    db: Session,
    marketer1_user: User,
    sample_campaign: Campaign,
    test_action_fixture: tuple[AiThread, AiMessage, AiAction],
):
    """Một dòng lỗi thì KHÔNG dòng nào được ghi (mỗi upsert tự commit nên phải kiểm tra trước)."""
    from app.core.errors import ValidationFailed
    from app.core.timeutil import today_vn
    from app.models import Metric

    thread, message, _ = test_action_fixture
    good = {
        "campaign_id": sample_campaign.id,
        "channel_code": "FACEBOOK",
        "metric_date": today_vn().isoformat(),
        "views": 100,
        "clicks": 10,
        "conversions": 1,
        "cost": 50000,
    }
    bad = {**good, "metric_date": "2026-01-02", "clicks": 999}  # clicks > views
    action = AiAction(
        thread_id=thread.id,
        message_id=message.id,
        user_id=marketer1_user.id,
        tool="propose_metrics",
        args_json={"rows": [good, bad]},
        summary="Đề xuất ghi 2 dòng số liệu",
        status=AiActionStatus.PROPOSED,
    )
    db.add(action)
    db.commit()

    with pytest.raises(ValidationFailed):
        actions_service.confirm(db, marketer1_user, action.id)

    assert db.query(Metric).filter(Metric.campaign_id == sample_campaign.id).count() == 0
    db.refresh(action)
    assert action.status == AiActionStatus.PROPOSED
