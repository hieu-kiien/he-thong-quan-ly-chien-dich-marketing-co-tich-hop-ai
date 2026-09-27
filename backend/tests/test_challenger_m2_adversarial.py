"""Adversarial and Empirical Stress-Testing Suite for Milestone M2.
Author: Challenger M2-1 (Adversarial Critic & Domain Specialist)
Focus:
  1. CPA Calculation Stress: Zero-division, adversarial metric inputs, float precision rounding across all endpoints.
  2. Schedule Cancellation: PLANNED -> CANCELLED, content stays APPROVED, idempotent cancel, EXECUTED -> 400, RBAC/tenant isolation.
  3. Rescheduling: CANCELLED -> PLANNED, scheduled_at update, EXECUTED -> 400, unapproved content -> 400, RBAC/tenant isolation.
  4. Worker Integration: Cancelled schedules ignored by worker; revived schedules processed when due.
"""

import pytest
from datetime import datetime, timezone, timedelta
from typing import Dict
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.entities import Campaign, CampaignMetric, MarketingContent, MarketingSchedule, User, Workspace, WorkspaceMember
from app.schemas.schemas import KPISummaryResponse
from app.services.scheduler.worker import process_due_schedules


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
def foreign_user_headers(client: TestClient, db_session: Session) -> Dict[str, str]:
    """A user who is NOT a member of Workspace 1 nor campaign owner."""
    from app.core.security import hash_password
    foreign_user = User(
        email="foreign_intruder@adversary.com",
        full_name="Foreign Intruder",
        password_hash=hash_password("Intruder@123"),
        role="MARKETER",
        status="ACTIVE"
    )
    db_session.add(foreign_user)
    db_session.commit()
    db_session.refresh(foreign_user)

    resp = client.post("/api/v1/auth/login", json={"email": "foreign_intruder@adversary.com", "password": "Intruder@123"})
    assert resp.status_code == 200, f"Foreign login failed: {resp.text}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


# ==============================================================================
# SECTION 1: CPA CALCULATION ADVERSARIAL STRESS TESTS
# ==============================================================================

@pytest.mark.parametrize("cost,conversions,views,clicks,expected_cpa", [
    # Zero conversions edge cases
    (0.0, 0, 0, 0, 0.0),                  # All zero metrics
    (100_000_000.0, 0, 50000, 1000, 0.0),  # High cost, 0 conversions -> Zero-division safe
    (999_999_999_999.0, 0, 0, 0, 0.0),    # Astronomical cost, 0 conversions
    (0.01, 0, 10, 1, 0.0),                 # Tiny cost, 0 conversions
    # Zero cost edge cases
    (0.0, 500, 10000, 2000, 0.0),          # Positive conversions, 0 cost -> 0.0
    # Precision and float rounding (round(x, 2))
    (10.0, 3, 100, 20, 3.33),              # 10 / 3 = 3.3333333333333335 -> 3.33
    (100.0, 7, 200, 50, 14.29),            # 100 / 7 = 14.285714285714286 -> 14.29
    (2.0, 3, 100, 20, 0.67),               # 2 / 3 = 0.6666666666666666 -> 0.67
    (1.0, 6, 100, 20, 0.17),               # 1 / 6 = 0.16666666666666666 -> 0.17
    (3.0, 8, 100, 20, 0.38),               # 3 / 8 = 0.375 -> 0.38
    (5_000_000.0, 100, 10000, 500, 50000.0), # Realistic VND figures
    (15_432_100.0, 321, 50000, 1500, 48075.08), # 15432100 / 321 = 48075.07788... -> 48075.08
])
def test_adv_01_cpa_adversarial_matrix(
    client: TestClient,
    manager_headers: Dict[str, str],
    db_session: Session,
    cost: float,
    conversions: int,
    views: int,
    clicks: int,
    expected_cpa: float
):
    """Stress-test CPA calculation across adversarial inputs and rounding boundaries."""
    camp = Campaign(
        name=f"CPA Stress Campaign {cost}_{conversions}",
        workspace_id=1,
        owner_id=1,
        product_id=1,
        objective="Adversarial stress test",
        audience="Target",
        start_date="2026-10-01",
        end_date="2026-10-31",
        budget=1_000_000_000.0,
        status="ACTIVE"
    )
    db_session.add(camp)
    db_session.commit()
    db_session.refresh(camp)

    metric = CampaignMetric(
        campaign_id=camp.id,
        channel_id=1,
        metric_date="2026-10-10",
        views=views,
        clicks=clicks,
        conversions=conversions,
        cost=cost,
        revenue=cost * 2.5
    )
    db_session.add(metric)
    db_session.commit()

    resp = client.get(f"/api/v1/campaigns/{camp.id}/kpi", headers=manager_headers)
    assert resp.status_code == 200, f"Expected 200 OK, got: {resp.text}"
    data = resp.json()

    assert "cpa_avg" in data
    assert data["cpa_avg"] == expected_cpa
    assert data["total_conversions"] == conversions
    assert data["total_cost"] == round(cost, 2)


def test_adv_02_cpa_multi_record_aggregation(
    client: TestClient,
    manager_headers: Dict[str, str],
    db_session: Session
):
    """Adversarial multi-record aggregation: one record with 0 conversions and one with conversions."""
    camp = Campaign(
        name="CPA Multi-Record Aggregation Campaign",
        workspace_id=1,
        owner_id=1,
        product_id=1,
        objective="Multi-record CPA aggregation",
        audience="General",
        start_date="2026-10-01",
        end_date="2026-10-31",
        budget=10_000_000.0,
        status="ACTIVE"
    )
    db_session.add(camp)
    db_session.commit()
    db_session.refresh(camp)

    # Record 1: 0 conversions, 50,000 cost
    m1 = CampaignMetric(
        campaign_id=camp.id,
        channel_id=1,
        metric_date="2026-10-01",
        views=1000,
        clicks=100,
        conversions=0,
        cost=50000.0,
        revenue=0.0
    )
    # Record 2: 5 conversions, 50,000 cost
    m2 = CampaignMetric(
        campaign_id=camp.id,
        channel_id=2,
        metric_date="2026-10-02",
        views=2000,
        clicks=200,
        conversions=5,
        cost=50000.0,
        revenue=200000.0
    )
    db_session.add_all([m1, m2])
    db_session.commit()

    resp = client.get(f"/api/v1/campaigns/{camp.id}/kpi", headers=manager_headers)
    assert resp.status_code == 200
    data = resp.json()

    # Total cost = 100,000, Total conversions = 5 -> CPA = 20,000.0
    assert data["total_cost"] == 100000.0
    assert data["total_conversions"] == 5
    assert data["cpa_avg"] == 20000.0


def test_adv_03_all_dashboard_endpoints_consistency(
    client: TestClient,
    manager_headers: Dict[str, str]
):
    """Check that all global dashboard endpoints return consistent cpa_avg in their KPI dict."""
    paths = [
        "/api/v1/analytics/dashboard",
        "/api/v1/metrics/dashboard",
        "/api/v1/metrics/overview"
    ]
    results = []
    for path in paths:
        resp = client.get(path, headers=manager_headers)
        assert resp.status_code == 200, f"Endpoint {path} failed: {resp.text}"
        data = resp.json()
        assert "kpi" in data, f"Missing 'kpi' in {path}"
        assert "cpa_avg" in data["kpi"], f"Missing 'cpa_avg' in kpi of {path}"
        results.append(data["kpi"]["cpa_avg"])

    # Ensure all endpoints return the exact same value
    assert len(set(results)) == 1, f"Inconsistent cpa_avg across dashboard endpoints: {results}"


# ==============================================================================
# SECTION 2: SCHEDULE CANCELLATION ADVERSARIAL STRESS TESTS
# ==============================================================================

def test_adv_04_cancel_planned_leaves_content_approved(
    client: TestClient,
    manager_headers: Dict[str, str],
    db_session: Session
):
    """Cancelling a PLANNED schedule transitions it to CANCELLED and ensures content remains APPROVED."""
    content = MarketingContent(
        campaign_id=1,
        channel_id=1,
        title="Content to Cancel",
        body="Body of content",
        cta="Click here",
        status="APPROVED",
        created_by=1,
        workspace_id=1
    )
    db_session.add(content)
    db_session.commit()
    db_session.refresh(content)

    schedule = MarketingSchedule(
        content_id=content.id,
        scheduled_at="2026-11-20 09:00",
        timezone="Asia/Ho_Chi_Minh",
        status="PLANNED",
        created_by=1
    )
    db_session.add(schedule)
    db_session.commit()
    db_session.refresh(schedule)

    # 1. Cancel via POST /schedules/{id}/cancel
    resp_post = client.post(f"/api/v1/schedules/{schedule.id}/cancel", headers=manager_headers)
    assert resp_post.status_code == 200
    assert resp_post.json()["status"] == "CANCELLED"

    db_session.refresh(content)
    assert content.status == "APPROVED", "Content status must remain APPROVED after cancellation"

    # Reset to PLANNED
    schedule.status = "PLANNED"
    db_session.commit()

    # 2. Cancel via DELETE /schedules/{id}
    resp_del = client.delete(f"/api/v1/schedules/{schedule.id}", headers=manager_headers)
    assert resp_del.status_code == 200
    assert resp_del.json()["status"] == "CANCELLED"

    db_session.refresh(content)
    assert content.status == "APPROVED", "Content status must remain APPROVED after DELETE cancellation"


def test_adv_05_cancel_executed_schedule_returns_400(
    client: TestClient,
    manager_headers: Dict[str, str],
    db_session: Session
):
    """Cancelling an already EXECUTED schedule MUST return HTTP 400 Bad Request."""
    content = MarketingContent(
        campaign_id=1,
        channel_id=1,
        title="Content already executed",
        body="Body",
        cta="Click",
        status="PUBLISHED",
        created_by=1,
        workspace_id=1
    )
    db_session.add(content)
    db_session.commit()
    db_session.refresh(content)

    schedule = MarketingSchedule(
        content_id=content.id,
        scheduled_at="2026-08-01 10:00",
        timezone="Asia/Ho_Chi_Minh",
        status="EXECUTED",
        created_by=1
    )
    db_session.add(schedule)
    db_session.commit()
    db_session.refresh(schedule)

    # POST cancel -> 400
    resp_post = client.post(f"/api/v1/schedules/{schedule.id}/cancel", headers=manager_headers)
    assert resp_post.status_code == 400
    assert "EXECUTED" in resp_post.json()["detail"]

    # DELETE cancel -> 400
    resp_del = client.delete(f"/api/v1/schedules/{schedule.id}", headers=manager_headers)
    assert resp_del.status_code == 400
    assert "EXECUTED" in resp_del.json()["detail"]


def test_adv_06_cancel_already_cancelled_is_idempotent(
    client: TestClient,
    manager_headers: Dict[str, str],
    db_session: Session
):
    """Cancelling a schedule that is already CANCELLED is idempotent and returns 200."""
    content = MarketingContent(
        campaign_id=1,
        channel_id=1,
        title="Double Cancel Content",
        body="Body",
        cta="Click",
        status="APPROVED",
        created_by=1,
        workspace_id=1
    )
    db_session.add(content)
    db_session.commit()
    db_session.refresh(content)

    schedule = MarketingSchedule(
        content_id=content.id,
        scheduled_at="2026-11-20 09:00",
        timezone="Asia/Ho_Chi_Minh",
        status="CANCELLED",
        created_by=1
    )
    db_session.add(schedule)
    db_session.commit()
    db_session.refresh(schedule)

    resp = client.post(f"/api/v1/schedules/{schedule.id}/cancel", headers=manager_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "CANCELLED"


def test_adv_07_cancel_schedule_unauthorized_forbidden(
    client: TestClient,
    foreign_user_headers: Dict[str, str],
    db_session: Session
):
    """A user outside the workspace / unauthorized cannot cancel the schedule (HTTP 403 Forbidden)."""
    content = MarketingContent(
        campaign_id=1,
        channel_id=1,
        title="Protected Content",
        body="Body",
        cta="Click",
        status="APPROVED",
        created_by=1,
        workspace_id=1
    )
    db_session.add(content)
    db_session.commit()
    db_session.refresh(content)

    schedule = MarketingSchedule(
        content_id=content.id,
        scheduled_at="2026-11-20 09:00",
        timezone="Asia/Ho_Chi_Minh",
        status="PLANNED",
        created_by=1
    )
    db_session.add(schedule)
    db_session.commit()
    db_session.refresh(schedule)

    resp = client.post(f"/api/v1/schedules/{schedule.id}/cancel", headers=foreign_user_headers)
    assert resp.status_code == 403, f"Expected 403 Forbidden, got {resp.status_code}: {resp.text}"


# ==============================================================================
# SECTION 3: RESCHEDULING ADVERSARIAL STRESS TESTS
# ==============================================================================

def test_adv_08_reschedule_resets_cancelled_to_planned(
    client: TestClient,
    manager_headers: Dict[str, str],
    db_session: Session
):
    """Updating scheduled_at resets a CANCELLED schedule back to PLANNED."""
    content = MarketingContent(
        campaign_id=1,
        channel_id=1,
        title="Rescheduled Content",
        body="Body",
        cta="Click",
        status="APPROVED",
        created_by=1,
        workspace_id=1
    )
    db_session.add(content)
    db_session.commit()
    db_session.refresh(content)

    schedule = MarketingSchedule(
        content_id=content.id,
        scheduled_at="2026-11-01 08:00",
        timezone="Asia/Ho_Chi_Minh",
        status="CANCELLED",
        created_by=1
    )
    db_session.add(schedule)
    db_session.commit()
    db_session.refresh(schedule)

    new_time = "2026-12-15 14:00"
    resp = client.put(
        f"/api/v1/schedules/{schedule.id}",
        json={"scheduled_at": new_time, "timezone": "Asia/Ho_Chi_Minh"},
        headers=manager_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["scheduled_at"] == new_time
    assert data["status"] == "PLANNED", "Status must reset from CANCELLED to PLANNED"

    # Verify directly in DB
    db_session.refresh(schedule)
    assert schedule.status == "PLANNED"
    assert schedule.scheduled_at == new_time


def test_adv_09_reschedule_executed_returns_400(
    client: TestClient,
    manager_headers: Dict[str, str],
    db_session: Session
):
    """Rescheduling an already EXECUTED schedule returns HTTP 400 Bad Request."""
    content = MarketingContent(
        campaign_id=1,
        channel_id=1,
        title="Executed Content",
        body="Body",
        cta="Click",
        status="PUBLISHED",
        created_by=1,
        workspace_id=1
    )
    db_session.add(content)
    db_session.commit()
    db_session.refresh(content)

    schedule = MarketingSchedule(
        content_id=content.id,
        scheduled_at="2026-08-01 10:00",
        timezone="Asia/Ho_Chi_Minh",
        status="EXECUTED",
        created_by=1
    )
    db_session.add(schedule)
    db_session.commit()
    db_session.refresh(schedule)

    resp = client.put(
        f"/api/v1/schedules/{schedule.id}",
        json={"scheduled_at": "2026-12-01 10:00"},
        headers=manager_headers
    )
    assert resp.status_code == 400
    assert "EXECUTED" in resp.json()["detail"]


def test_adv_10_reschedule_fails_if_content_not_approved(
    client: TestClient,
    manager_headers: Dict[str, str],
    db_session: Session
):
    """If content was revoked (e.g. reverted to AI_DRAFT or REJECTED), rescheduling must fail with HTTP 400."""
    content = MarketingContent(
        campaign_id=1,
        channel_id=1,
        title="Revoked Content",
        body="Body",
        cta="Click",
        status="AI_DRAFT",  # Content is no longer APPROVED!
        created_by=1,
        workspace_id=1
    )
    db_session.add(content)
    db_session.commit()
    db_session.refresh(content)

    schedule = MarketingSchedule(
        content_id=content.id,
        scheduled_at="2026-11-01 08:00",
        timezone="Asia/Ho_Chi_Minh",
        status="CANCELLED",
        created_by=1
    )
    db_session.add(schedule)
    db_session.commit()
    db_session.refresh(schedule)

    resp = client.put(
        f"/api/v1/schedules/{schedule.id}",
        json={"scheduled_at": "2026-12-01 10:00"},
        headers=manager_headers
    )
    assert resp.status_code == 400
    assert "APPROVED" in resp.json()["detail"]


def test_adv_11_reschedule_patch_partial_update(
    client: TestClient,
    manager_headers: Dict[str, str],
    db_session: Session
):
    """PATCH allows partial updates: update only timezone or only scheduled_at."""
    content = MarketingContent(
        campaign_id=1,
        channel_id=1,
        title="Partial Update Content",
        body="Body",
        cta="Click",
        status="APPROVED",
        created_by=1,
        workspace_id=1
    )
    db_session.add(content)
    db_session.commit()
    db_session.refresh(content)

    schedule = MarketingSchedule(
        content_id=content.id,
        scheduled_at="2026-11-01 08:00",
        timezone="Asia/Ho_Chi_Minh",
        status="CANCELLED",
        created_by=1
    )
    db_session.add(schedule)
    db_session.commit()
    db_session.refresh(schedule)

    # Patch only timezone
    resp = client.patch(
        f"/api/v1/schedules/{schedule.id}",
        json={"timezone": "UTC"},
        headers=manager_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["timezone"] == "UTC"
    assert data["scheduled_at"] == "2026-11-01 08:00"
    assert data["status"] == "PLANNED"  # Still reactivated to PLANNED


# ==============================================================================
# SECTION 4: WORKER INTEGRATION & STATE MACHINE INVARIANTS
# ==============================================================================

def test_adv_12_worker_ignores_cancelled_schedule(db_session: Session):
    """The background worker must NEVER execute a CANCELLED schedule, even if scheduled_at <= now()."""
    content = MarketingContent(
        campaign_id=1,
        channel_id=1,
        title="Cancelled but past due",
        body="Body",
        cta="Click",
        status="APPROVED",
        created_by=1,
        workspace_id=1
    )
    db_session.add(content)
    db_session.commit()
    db_session.refresh(content)

    cancelled_schedule = MarketingSchedule(
        content_id=content.id,
        scheduled_at="2026-01-01 00:00",  # Far past
        timezone="Asia/Ho_Chi_Minh",
        status="CANCELLED",
        created_by=1
    )
    db_session.add(cancelled_schedule)
    db_session.commit()
    db_session.refresh(cancelled_schedule)

    # Run worker
    processed_ids = process_due_schedules(db_session)
    assert cancelled_schedule.id not in processed_ids

    db_session.refresh(cancelled_schedule)
    db_session.refresh(content)
    assert cancelled_schedule.status == "CANCELLED"
    assert content.status == "APPROVED"  # Must NOT be published!


def test_adv_13_worker_executes_revived_schedule(
    client: TestClient,
    manager_headers: Dict[str, str],
    db_session: Session
):
    """A CANCELLED schedule revived to PLANNED via rescheduling with due time MUST be executed by worker."""
    content = MarketingContent(
        campaign_id=1,
        channel_id=1,
        title="Revived and Due",
        body="Body",
        cta="Click",
        status="APPROVED",
        created_by=1,
        workspace_id=1
    )
    db_session.add(content)
    db_session.commit()
    db_session.refresh(content)

    schedule = MarketingSchedule(
        content_id=content.id,
        scheduled_at="2099-01-01 00:00",
        timezone="Asia/Ho_Chi_Minh",
        status="CANCELLED",
        created_by=1
    )
    db_session.add(schedule)
    db_session.commit()
    db_session.refresh(schedule)

    # Reschedule to a past time
    resp = client.put(
        f"/api/v1/schedules/{schedule.id}",
        json={"scheduled_at": "2026-01-01 12:00"},
        headers=manager_headers
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "PLANNED"

    # Trigger worker via API endpoint
    resp_worker = client.post("/api/v1/schedules/trigger-worker", headers=manager_headers)
    assert resp_worker.status_code == 200
    assert schedule.id in resp_worker.json()["processed_schedule_ids"]

    # Verify DB transitions
    db_session.refresh(schedule)
    db_session.refresh(content)
    assert schedule.status == "EXECUTED"
    assert content.status == "PUBLISHED"
