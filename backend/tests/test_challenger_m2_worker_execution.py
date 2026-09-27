"""Adversarial and Empirical Challenge Test Suite for Milestone M2:
Background Scheduler Worker Execution & Content Publishing Lifecycle.
Authored by Challenger 2 (Empirical Challenger).
"""

import pytest
from datetime import datetime, timezone, timedelta
from typing import Dict
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.entities import Campaign, MarketingContent, MarketingSchedule, User
from app.services.scheduler.worker import (
    process_due_schedules,
    parse_scheduled_datetime,
    get_tz_from_name,
    VN_TIMEZONE
)


@pytest.fixture
def manager_headers(client: TestClient) -> Dict[str, str]:
    resp = client.post("/api/v1/auth/login", json={"email": "manager@gmail.com", "password": "Manager@123"})
    assert resp.status_code == 200, f"Manager login failed: {resp.text}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
def marketer_headers(client: TestClient) -> Dict[str, str]:
    resp = client.post("/api/v1/auth/login", json={"email": "marketer@gmail.com", "password": "Marketer@123"})
    assert resp.status_code == 200, f"Marketer login failed: {resp.text}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
def create_test_content(db_session: Session):
    """Helper factory to create MarketingContent with specific status."""
    def _create(title: str, status: str = "APPROVED", workspace_id: int = 1) -> MarketingContent:
        content = MarketingContent(
            campaign_id=1,
            channel_id=1,
            title=title,
            body=f"Body for {title}",
            cta="Click here",
            status=status,
            created_by=1,
            workspace_id=workspace_id
        )
        db_session.add(content)
        db_session.commit()
        db_session.refresh(content)
        return content
    return _create


# ==============================================================================
# Challenge 1: Core Worker Auto-Execution (Requirement 1)
# ==============================================================================

def test_challenger_m2_01_worker_execution_lifecycle_via_endpoint(
    client: TestClient,
    manager_headers: Dict[str, str],
    create_test_content,
    db_session: Session
):
    """Verify that an APPROVED content scheduled in the past/now transitions
    to PUBLISHED and schedule transitions to EXECUTED when POST /schedules/trigger-worker is invoked.
    """
    # 1. Create APPROVED content
    content = create_test_content("Challenger Post Due Past", status="APPROVED")
    assert content.status == "APPROVED"

    # 2. Schedule it with scheduled_at in the past
    past_time = (datetime.now(VN_TIMEZONE) - timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
    schedule_resp = client.post(
        f"/api/v1/contents/{content.id}/schedule",
        json={"scheduled_at": past_time, "timezone": "Asia/Ho_Chi_Minh"},
        headers=manager_headers
    )
    assert schedule_resp.status_code == 201
    schedule_data = schedule_resp.json()
    schedule_id = schedule_data["id"]
    assert schedule_data["status"] == "PLANNED"

    # 3. Trigger worker via POST /schedules/trigger-worker
    trigger_resp = client.post("/api/v1/schedules/trigger-worker", headers=manager_headers)
    assert trigger_resp.status_code == 200
    trigger_data = trigger_resp.json()
    assert schedule_id in trigger_data["processed_schedule_ids"]
    assert trigger_data["count"] >= 1

    # 4. Verify in database that schedule status == EXECUTED and content status == PUBLISHED
    db_session.expire_all()
    updated_schedule = db_session.query(MarketingSchedule).filter(MarketingSchedule.id == schedule_id).first()
    updated_content = db_session.query(MarketingContent).filter(MarketingContent.id == content.id).first()

    assert updated_schedule is not None
    assert updated_schedule.status == "EXECUTED"
    assert updated_content is not None
    assert updated_content.status == "PUBLISHED"


def test_challenger_m2_02_worker_direct_callable_and_idempotency(
    create_test_content,
    db_session: Session
):
    """Verify process_due_schedules callable works directly and is strictly idempotent."""
    content = create_test_content("Challenger Direct Callable Post", status="APPROVED")
    past_time = (datetime.now(VN_TIMEZONE) - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")

    schedule = MarketingSchedule(
        content_id=content.id,
        scheduled_at=past_time,
        timezone="Asia/Ho_Chi_Minh",
        status="PLANNED",
        created_by=1
    )
    db_session.add(schedule)
    db_session.commit()
    db_session.refresh(schedule)

    # First execution: must process
    processed_1 = process_due_schedules(db_session)
    assert schedule.id in processed_1

    db_session.refresh(schedule)
    db_session.refresh(content)
    assert schedule.status == "EXECUTED"
    assert content.status == "PUBLISHED"

    # Second execution immediately after: must be NO-OP (idempotent, return empty or not include schedule.id)
    processed_2 = process_due_schedules(db_session)
    assert schedule.id not in processed_2


# ==============================================================================
# Challenge 2: Adversarial State Machine & Protection Shields
# ==============================================================================

def test_challenger_m2_03_adversarial_draft_content_never_published_by_worker(
    create_test_content,
    db_session: Session
):
    """Adversarial Scenario: If a schedule is due, but the content status is DRAFT or REJECTED
    (e.g., someone reset it after scheduling), worker MUST NOT publish it!
    """
    draft_content = create_test_content("Draft Tampered Post", status="DRAFT")
    past_time = (datetime.now(VN_TIMEZONE) - timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")

    schedule = MarketingSchedule(
        content_id=draft_content.id,
        scheduled_at=past_time,
        timezone="Asia/Ho_Chi_Minh",
        status="PLANNED",
        created_by=1
    )
    db_session.add(schedule)
    db_session.commit()

    processed = process_due_schedules(db_session)
    assert schedule.id in processed

    db_session.refresh(draft_content)
    # CRITICAL: Content MUST NOT be PUBLISHED! It was DRAFT!
    assert draft_content.status == "DRAFT"


def test_challenger_m2_04_adversarial_cancelled_schedule_is_never_executed(
    create_test_content,
    db_session: Session
):
    """Adversarial Scenario: A schedule was CANCELLED before the scheduled time arrived.
    When time passes and worker runs, it must NOT execute CANCELLED schedules.
    """
    content = create_test_content("Cancelled Schedule Post", status="APPROVED")
    past_time = (datetime.now(VN_TIMEZONE) - timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")

    schedule = MarketingSchedule(
        content_id=content.id,
        scheduled_at=past_time,
        timezone="Asia/Ho_Chi_Minh",
        status="CANCELLED",
        created_by=1
    )
    db_session.add(schedule)
    db_session.commit()

    processed = process_due_schedules(db_session)
    assert schedule.id not in processed

    db_session.refresh(schedule)
    db_session.refresh(content)
    assert schedule.status == "CANCELLED"
    assert content.status == "APPROVED"  # Content remains APPROVED, not PUBLISHED


def test_challenger_m2_05_adversarial_future_schedule_boundary(
    create_test_content,
    db_session: Session
):
    """Verify schedule set in future (+2 hours) is not prematurely executed."""
    content = create_test_content("Future Schedule Post", status="APPROVED")
    future_time = (datetime.now(VN_TIMEZONE) + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")

    schedule = MarketingSchedule(
        content_id=content.id,
        scheduled_at=future_time,
        timezone="Asia/Ho_Chi_Minh",
        status="PLANNED",
        created_by=1
    )
    db_session.add(schedule)
    db_session.commit()

    processed = process_due_schedules(db_session)
    assert schedule.id not in processed

    db_session.refresh(schedule)
    db_session.refresh(content)
    assert schedule.status == "PLANNED"
    assert content.status == "APPROVED"


# ==============================================================================
# Challenge 3: Stress & Resilience (Batch, Malformed, Orphan)
# ==============================================================================

def test_challenger_m2_06_batch_multi_schedule_concurrency(
    create_test_content,
    db_session: Session
):
    """Stress Test: 5 due schedules processed in a single batch worker run."""
    schedules = []
    contents = []
    past_time = (datetime.now(VN_TIMEZONE) - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")

    for i in range(5):
        c = create_test_content(f"Batch Post {i}", status="APPROVED")
        s = MarketingSchedule(
            content_id=c.id,
            scheduled_at=past_time,
            timezone="Asia/Ho_Chi_Minh",
            status="PLANNED",
            created_by=1
        )
        db_session.add(s)
        contents.append(c)
        schedules.append(s)

    db_session.commit()

    processed = process_due_schedules(db_session)
    for s in schedules:
        assert s.id in processed

    for c in contents:
        db_session.refresh(c)
        assert c.status == "PUBLISHED"

    for s in schedules:
        db_session.refresh(s)
        assert s.status == "EXECUTED"


def test_challenger_m2_07_malformed_datetime_resilience(
    create_test_content,
    db_session: Session
):
    """Resilience Test: One schedule has completely invalid datetime string.
    Worker must log warning and continue without crashing, successfully executing valid schedules.
    """
    valid_content = create_test_content("Valid Post Beside Malformed", status="APPROVED")
    past_time = (datetime.now(VN_TIMEZONE) - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")

    bad_schedule = MarketingSchedule(
        content_id=valid_content.id,
        scheduled_at="INVALID_DATE_STRING_12345",
        timezone="Asia/Ho_Chi_Minh",
        status="PLANNED",
        created_by=1
    )
    good_schedule = MarketingSchedule(
        content_id=valid_content.id,
        scheduled_at=past_time,
        timezone="Asia/Ho_Chi_Minh",
        status="PLANNED",
        created_by=1
    )
    db_session.add_all([bad_schedule, good_schedule])
    db_session.commit()

    # Worker must NOT crash with ValueError
    processed = process_due_schedules(db_session)
    assert good_schedule.id in processed
    assert bad_schedule.id not in processed

    db_session.refresh(bad_schedule)
    assert bad_schedule.status == "PLANNED"  # Bad schedule remains unexecuted


def test_challenger_m2_08_fk_constraint_and_cascade_delete_resilience(
    create_test_content,
    db_session: Session
):
    """Resilience Test:
    1. Foreign Key constraint prevents orphan schedules with invalid content_id.
    2. Deleting content with cascade cleans up schedule or worker safely handles if content missing.
    """
    past_time = (datetime.now(VN_TIMEZONE) - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")

    # 1. Attempting to insert an invalid content_id raises IntegrityError due to FK constraint
    orphan_schedule = MarketingSchedule(
        content_id=9999999,  # Non-existent content
        scheduled_at=past_time,
        timezone="Asia/Ho_Chi_Minh",
        status="PLANNED",
        created_by=1
    )
    db_session.add(orphan_schedule)
    with pytest.raises(Exception):
        db_session.commit()
    db_session.rollback()

    # 2. Test cascade delete: create content & schedule, then verify cascade or worker handling
    content = create_test_content("Content To Delete", status="APPROVED")
    schedule = MarketingSchedule(
        content_id=content.id,
        scheduled_at=past_time,
        timezone="Asia/Ho_Chi_Minh",
        status="PLANNED",
        created_by=1
    )
    db_session.add(schedule)
    db_session.commit()
    sched_id = schedule.id

    # If content is deleted, schedule is deleted by cascade or handled safely
    db_session.delete(content)
    db_session.commit()

    # Run worker: must complete cleanly with 0 errors
    processed = process_due_schedules(db_session)
    assert sched_id not in processed


# ==============================================================================
# Challenge 4: Manual Publish Now API Endpoint Verification
# ==============================================================================

def test_challenger_m2_09_manual_publish_endpoint_lifecycle(
    client: TestClient,
    manager_headers: Dict[str, str],
    marketer_headers: Dict[str, str],
    create_test_content,
    db_session: Session
):
    """Verify POST /api/v1/contents/{id}/publish:
    1. Manager publishes APPROVED content -> HTTP 200, status becomes PUBLISHED.
    2. Manager publishes DRAFT content -> HTTP 400 Bad Request.
    3. Manager publishes already PUBLISHED content -> HTTP 400 Bad Request.
    4. Marketer attempts to publish -> HTTP 403 Forbidden (RBAC Guard).
    5. Non-existent content -> HTTP 404 Not Found.
    """
    # 1. Manager publishes APPROVED content -> PASS
    approved_post = create_test_content("Post for Manual Publish", status="APPROVED")
    resp_pub = client.post(f"/api/v1/contents/{approved_post.id}/publish", headers=manager_headers)
    assert resp_pub.status_code == 200
    assert resp_pub.json()["status"] == "PUBLISHED"

    # 2. Manager publishes DRAFT content -> 400
    draft_post = create_test_content("Draft Post Not Approved", status="DRAFT")
    resp_draft = client.post(f"/api/v1/contents/{draft_post.id}/publish", headers=manager_headers)
    assert resp_draft.status_code == 400
    assert "APPROVED" in resp_draft.json()["detail"]

    # 3. Manager publishes already PUBLISHED content -> 400
    resp_already = client.post(f"/api/v1/contents/{approved_post.id}/publish", headers=manager_headers)
    assert resp_already.status_code == 400
    assert "APPROVED" in resp_already.json()["detail"]

    # 4. Marketer attempts to publish -> 403 Forbidden
    approved_post_2 = create_test_content("Another Approved Post", status="APPROVED")
    resp_marketer = client.post(f"/api/v1/contents/{approved_post_2.id}/publish", headers=marketer_headers)
    assert resp_marketer.status_code == 403

    # 5. Non-existent content -> 404
    resp_404 = client.post("/api/v1/contents/999999/publish", headers=manager_headers)
    assert resp_404.status_code == 404


# ==============================================================================
# Challenge 5: Timezone Conversion Edge Cases
# ==============================================================================

def test_challenger_m2_10_timezone_offset_handling(db_session: Session):
    """Verify timezone offset resolution:
    - Asia/Ho_Chi_Minh (+07:00)
    - UTC (+00:00)
    - Custom format +07:00
    """
    tz_vn = get_tz_from_name("Asia/Ho_Chi_Minh")
    assert tz_vn.utcoffset(None) == timedelta(hours=7)

    tz_utc = get_tz_from_name("UTC")
    assert tz_utc.utcoffset(None) == timedelta(0)

    tz_custom = get_tz_from_name("+07:00")
    assert tz_custom.utcoffset(None) == timedelta(hours=7)

    # Test UTC vs VN time comparisons
    # 10:00 UTC == 17:00 VN
    dt_utc = parse_scheduled_datetime("2026-09-27T10:00:00Z")
    dt_vn = parse_scheduled_datetime("2026-09-27T17:00:00+07:00")
    assert dt_utc.astimezone(timezone.utc) == dt_vn.astimezone(timezone.utc)
