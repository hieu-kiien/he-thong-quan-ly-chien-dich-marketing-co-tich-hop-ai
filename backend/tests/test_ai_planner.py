"""Test Workstream G + H — AI Campaign Planner (kind=plan + plan/apply).

- G: hàng đợi `ai_jobs` nhận `kind=plan`; 3 map trong ai_jobs.py, CHECK constraint
  của bảng và JOB_KINDS phải CÙNG một tập giá trị — lệch là job chết âm thầm.
- H: `POST /ai/plan` sinh kế hoạch (offline -> Smart Fallback có kiểm soát) và
  `POST /campaigns/{id}/plan/apply` ghi vào CSDL theo đúng thứ tự
  "validate toàn bộ TRƯỚC, ghi SAU" + idempotency bắt buộc.

Mạng bị chặn ở conftest nên `/ai/plan` luôn rơi vào template fallback — đây là
đường thật sẽ chạy trên môi trường không có API key, nên test bám vào đó.
"""

import json

import pytest
from sqlalchemy.schema import CreateTable

from app.core.config import settings
from app.models.entities import (
    AIJob,
    Campaign,
    CampaignBudgetAllocation,
    CampaignKPITarget,
    CampaignPlanApplication,
    MarketingChannel,
    Task,
)

JOBS_API = "/api/v1/ai/jobs"
PLAN_API = "/api/v1/ai/plan"

CAMPAIGN_1_ID = 1  # Seed: owner=marketer@gmail.com, workspace alpha, 2026-09-01 -> 2026-09-30, budget 15.000.000


@pytest.fixture
def ai_fallback_off(monkeypatch):
    """Tắt Smart Fallback: thiếu key/lỗi mạng phải thành 502, không trả bản nháp.

    Cùng mẫu với `ai_completely_disabled` trong test_offline (chỉ tinh giản phần
    cần cho endpoint plan). `reset_ai_service_overrides` của conftest khôi phục
    singleton sau mỗi test nên monkeypatch ở đây an toàn.
    """
    monkeypatch.setattr(settings, "AI_ENABLE_FALLBACK", False, raising=False)
    from app.services.ai.ai_service import ai_service

    for attr in ("_fallback_enabled", "_api_key"):
        monkeypatch.setattr(ai_service, attr, None, raising=False)
    return settings


# ==============================================================================
# G: kind maps / CHECK constraint / enqueue
# ==============================================================================
def test_kind_maps_are_aligned_with_job_kinds():
    """3 map trong ai_jobs.py phải bao trùm ĐÚNG JOB_KINDS, và DDL bảng cũng vậy.

    Lệch ở đây nghĩa là enqueue nhận job nhưng worker không tra được endpoint
    (hoặc DB chặn kind trước khi vào hàng đợi) — job treo ở trạng thái queued
    vĩnh viễn, loại lỗi khó thấy nhất của cả cụm bất đồng bộ.
    """
    from app.api.v1 import ai as ai_endpoints
    from app.api.v1 import ai_jobs as ai_jobs_module
    from app.services.jobs import queue as job_queue

    kinds = set(job_queue.JOB_KINDS)
    assert set(ai_jobs_module._KIND_REQUEST_MODELS) == kinds
    assert set(ai_jobs_module._KIND_QUOTA_PREFIX) == kinds
    assert set(ai_jobs_module._KIND_SYNC_ENDPOINT) == kinds

    # kind=plan: campaign_id BẮT BUỘC, quota tách riêng, endpoint thật có tồn tại.
    plan_model = ai_jobs_module._KIND_REQUEST_MODELS[job_queue.KIND_PLAN]
    assert plan_model.model_fields["campaign_id"].is_required()
    assert ai_jobs_module._KIND_QUOTA_PREFIX[job_queue.KIND_PLAN] == "ai:plan"
    assert ai_jobs_module._KIND_SYNC_ENDPOINT[job_queue.KIND_PLAN] == "generate_plan"
    assert callable(getattr(ai_endpoints, "generate_plan", None))

    # CHECK constraint của bảng ai_jobs (tạo từ metadata) phải chứa 'plan',
    # nếu không CSDL cũ/tươi từ metadata cũng chặn đúng kind mới.
    ddl = str(CreateTable(AIJob.__table__))
    assert "'plan'" in ddl, f"DDL ai_jobs thiếu 'plan' trong CHECK kind: {ddl}"


def test_enqueue_plan_job_returns_202(client, db_session, manager_headers):
    resp = client.post(
        JOBS_API,
        json={"kind": "plan", "campaign_id": CAMPAIGN_1_ID},
        headers=manager_headers,
    )
    assert resp.status_code == 202, resp.text
    body = resp.json()
    assert body["kind"] == "plan"

    row = db_session.query(AIJob).filter(AIJob.id == body["job_id"]).first()
    assert row is not None
    assert row.kind == "plan"
    assert row.workspace_id is not None, "job phải mang tenant ngay lúc nhận"
    payload = json.loads(row.payload_json)
    assert payload["campaign_id"] == CAMPAIGN_1_ID


def test_execute_ai_job_plan_reruns_sync_endpoint(client, db_session, monkeypatch, manager_headers):
    """Worker kind=plan phải gọi LẠI endpoint đồng bộ generate_plan."""
    from app.api.v1 import ai as ai_endpoints
    from app.api.v1.ai_jobs import execute_ai_job
    from app.schemas.schemas import AIPlanResponse

    seen = {}

    def _stub_endpoint(req, current_user, db):
        seen["campaign_id"] = req.campaign_id
        seen["prompt_version"] = req.prompt_version
        seen["user_id"] = current_user.id
        return AIPlanResponse(
            summary="Kế hoạch từ stub",
            budget_split=[{"channel_code": "facebook", "planned_amount": 1000.0}],
            tasks=[{
                "title": "T1",
                "task_type": "ADS",
                "priority": "HIGH",
                "due_offset_days": 1,
            }],
            model_used="stub-model",
            prompt_version=req.prompt_version,
        )

    monkeypatch.setattr(ai_endpoints, "generate_plan", _stub_endpoint)

    job_id = client.post(
        JOBS_API,
        json={"kind": "plan", "campaign_id": CAMPAIGN_1_ID, "prompt_version": "v3"},
        headers=manager_headers,
    ).json()["job_id"]
    job = db_session.query(AIJob).filter(AIJob.id == job_id).first()
    result = execute_ai_job(db=db_session, job=job)

    assert seen["campaign_id"] == CAMPAIGN_1_ID
    assert seen["prompt_version"] == "v3"
    assert seen["user_id"] == job.user_id
    assert result["model_used"] == "stub-model"
    assert result["task_type"] == "PLAN"


# ==============================================================================
# H1: POST /ai/plan — sinh kế hoạch (offline -> fallback hợp lệ)
# ==============================================================================
def test_sync_plan_returns_valid_offline_fallback(client, db_session, manager_headers):
    resp = client.post(PLAN_API, json={"campaign_id": CAMPAIGN_1_ID}, headers=manager_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()

    # Nguồn gốc phải nói đúng: không có key -> template, không bao giờ "AI thật".
    assert body["task_type"] == "PLAN"
    assert body["is_fallback"] is True
    assert body["model_provider"] == "template-fallback-engine"
    assert body["warnings"], "fallback phải cảnh báo người dùng rõ nguồn gốc"

    # Không bịa số: tổng phân bổ <= ngân sách thật của campaign 1.
    budget = 15000000.0
    assert body["budget_split"], "kế hoạch phải có ít nhất 1 dòng phân bổ"
    total = sum(float(x["planned_amount"]) for x in body["budget_split"])
    assert total <= budget + 1e-6, f"fallback phân bổ {total} vượt ngân sách {budget}"

    active_codes = {
        c.code
        for c in db_session.query(MarketingChannel).filter(MarketingChannel.status == "ACTIVE").all()
    }
    for item in body["budget_split"]:
        assert item["channel_code"] in active_codes, "chỉ được phân bổ vào kênh ACTIVE có thật"
        assert item["is_ai_estimate"] is True, "số AI phải gắn nhãn ước tính"

    # Task nằm trọn trong khoảng chiến dịch (max offset = (30/09 - 01/09) = 29).
    assert len(body["tasks"]) >= 1
    for t in body["tasks"]:
        assert 0 <= t["due_offset_days"] <= 29, t
        assert t["task_type"] in ("CONTENT", "DESIGN", "VIDEO", "ADS", "RESEARCH", "OTHER")
        assert t["priority"] in ("LOW", "MEDIUM", "HIGH", "URGENT")


def test_sync_plan_requires_ownership_and_tenant(client, db_session, beta_marketer_headers, approver_headers):
    # Beta workspace không thuộc chiến dịch alpha -> 403 (cách ly tenant).
    resp = client.post(PLAN_API, json={"campaign_id": CAMPAIGN_1_ID}, headers=beta_marketer_headers)
    assert resp.status_code == 403, resp.text

    # Client approver là ws member nhưng không phải owner/member chiến dịch -> 403.
    resp = client.post(PLAN_API, json={"campaign_id": CAMPAIGN_1_ID}, headers=approver_headers)
    assert resp.status_code == 403, resp.text

    resp = client.post(PLAN_API, json={"campaign_id": 999999}, headers=approver_headers)
    assert resp.status_code in (403, 404)


def test_sync_plan_fails_loudly_when_fallback_disabled(client, manager_headers, ai_fallback_off):
    """Tắt fallback -> 502, KHÔNG trả bản nháp giả mạo là kế hoạch thật."""
    resp = client.post(PLAN_API, json={"campaign_id": CAMPAIGN_1_ID}, headers=manager_headers)
    assert resp.status_code == 502, resp.text
    assert "budget_split" not in resp.text
    assert "tasks" not in resp.text


# ==============================================================================
# H2: fallback thuần — không bao giờ vượt ngân sách, luôn validate được
# ==============================================================================
def test_fallback_campaign_plan_never_exceeds_budget():
    from app.schemas.schemas import AIPlanResponse
    from app.services.ai.ai_service import ai_service

    for budget in (15000000.0, 9999.99, 0.0, 1.0):
        out = ai_service._generate_fallback_campaign_plan(
            {"campaign_name": "C", "budget_amount": budget, "channel_codes": ["facebook", "email", "blog"]}
        )
        assert out["is_fallback"] is True
        assert out["model_provider"] == "template-fallback-engine"
        assert out["warnings"]
        total = sum(float(x["planned_amount"]) for x in out["budget_split"])
        assert total <= budget + 1e-6, f"budget={budget}: tổng {total} vượt ngân sách"
        assert len(out["budget_split"]) == 3

    # Không có kênh -> vẫn 1 dòng để schema hợp lệ, kèm warning trung thực.
    out = ai_service._generate_fallback_campaign_plan({"budget_amount": 1000000.0})
    assert len(out["budget_split"]) == 1
    assert any("kênh" in w for w in out["warnings"])

    # Mọi fallback phải vượt qua CÙNG schema mà endpoint trả về.
    AIPlanResponse.model_validate(
        {**out, "model_used": "m", "prompt_version": "v3", "task_type": "PLAN"}
    )


# ==============================================================================
# H3: POST /campaigns/{id}/plan/apply — thành công + đánh dấu is_ai_estimate
# ==============================================================================
def _plan_from_ai(client, headers, campaign_id: int = CAMPAIGN_1_ID) -> dict:
    resp = client.post(PLAN_API, json={"campaign_id": campaign_id}, headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_apply_plan_success_marks_ai_estimate_and_creates_tasks(client, db_session, manager_headers):
    plan = _plan_from_ai(client, manager_headers)

    payload = {
        "budget_split": plan["budget_split"],
        "kpi_targets": [
            {"metric_name": "plan_leads", "target_value": 42, "unit": "count"},
        ],
        "tasks": plan["tasks"],
        "idempotency_key": "planner-apply-success-001",
    }
    before_tasks = db_session.query(Task).filter(Task.campaign_id == CAMPAIGN_1_ID).count()

    resp = client.post(
        f"/api/v1/campaigns/{CAMPAIGN_1_ID}/plan/apply",
        json=payload,
        headers=manager_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["campaign_id"] == CAMPAIGN_1_ID
    assert body["deduplicated"] is False
    assert body["tasks_created"] == len(payload["tasks"]) - body["tasks_skipped"]
    assert body["tasks_created"] >= 1, "kế hoạch mới phải tạo được task"

    # Phân bổ: đã ghi, gắn nhãn AI, tổng <= ngân sách.
    allocs = (
        db_session.query(CampaignBudgetAllocation)
        .filter(CampaignBudgetAllocation.campaign_id == CAMPAIGN_1_ID)
        .all()
    )
    assert allocs, "apply phải ghi phân bổ ngân sách"
    assert all(a.is_ai_estimate for a in allocs), "dòng do AI sinh phải mang is_ai_estimate=True"
    assert sum(float(a.planned_amount) for a in allocs) <= 15000000.0 + 1e-6

    # KPI: ghi với nhãn AI.
    kpi = (
        db_session.query(CampaignKPITarget)
        .filter(
            CampaignKPITarget.campaign_id == CAMPAIGN_1_ID,
            CampaignKPITarget.metric_name == "plan_leads",
        )
        .first()
    )
    assert kpi is not None and kpi.is_ai_estimate is True
    assert float(kpi.target_value) == 42

    # Task: TODO, creator là người bấm áp dụng, due_date = start + offset.
    after_tasks = db_session.query(Task).filter(Task.campaign_id == CAMPAIGN_1_ID).count()
    assert after_tasks - before_tasks == body["tasks_created"]
    created = (
        db_session.query(Task)
        .filter(Task.campaign_id == CAMPAIGN_1_ID, Task.status == "TODO")
        .all()
    )
    assert created, "task mới phải ở trạng thái TODO"
    assert any(t.due_date == "2026-09-01" for t in created), (
        "task offset 0 phải rơi vào đúng start_date của chiến dịch"
    )

    # Nhật ký idempotency: hash 64 ký tự, snapshot JSON đọc được.
    app_row = (
        db_session.query(CampaignPlanApplication)
        .filter(
            CampaignPlanApplication.campaign_id == CAMPAIGN_1_ID,
            CampaignPlanApplication.idempotency_key == "planner-apply-success-001",
        )
        .first()
    )
    assert app_row is not None
    assert len(app_row.plan_hash) == 64
    snapshot = json.loads(app_row.plan_json)
    assert snapshot["budget_split"] and snapshot["tasks"]


# ==============================================================================
# H4: validate TRƯỚC mọi ghi — request lỗi không được để lại dấu vết
# ==============================================================================
def test_apply_validates_everything_before_any_write(client, db_session, manager_headers):
    campaign = db_session.query(Campaign).filter(Campaign.id == CAMPAIGN_1_ID).first()
    assert campaign is not None
    channel = db_session.query(MarketingChannel).filter(MarketingChannel.code == "facebook").first()

    def _counts():
        return (
            db_session.query(CampaignBudgetAllocation)
            .filter(CampaignBudgetAllocation.campaign_id == CAMPAIGN_1_ID)
            .count(),
            db_session.query(CampaignKPITarget)
            .filter(CampaignKPITarget.campaign_id == CAMPAIGN_1_ID)
            .count(),
            db_session.query(Task).filter(Task.campaign_id == CAMPAIGN_1_ID).count(),
            db_session.query(CampaignPlanApplication)
            .filter(CampaignPlanApplication.campaign_id == CAMPAIGN_1_ID)
            .count(),
        )

    before = _counts()
    base_task = {"title": "X", "task_type": "ADS", "priority": "HIGH", "due_offset_days": 1}

    cases = [
        # a. Tổng phân bổ vượt ngân sách.
        (
            "planner-validate-budget",
            {
                "budget_split": [{"channel_code": "facebook", "planned_amount": 999999999.0}],
                "kpi_targets": [],
                "tasks": [base_task],
            },
        ),
        # b. Kênh không tồn tại / không hoạt động.
        (
            "planner-validate-channel",
            {
                "budget_split": [{"channel_code": "khong-ton-tai", "planned_amount": 1000.0}],
                "kpi_targets": [],
                "tasks": [base_task],
            },
        ),
        # c. Kênh bị phân bổ trùng.
        (
            "planner-validate-dupe-channel",
            {
                "budget_split": [
                    {"channel_code": "facebook", "planned_amount": 1000.0},
                    {"channel_code": "FACEBOOK", "planned_amount": 2000.0},
                ],
                "kpi_targets": [],
                "tasks": [base_task],
            },
        ),
        # d. KPI trùng metric_name.
        (
            "planner-validate-dupe-kpi",
            {
                "budget_split": [{"channel_code": "facebook", "planned_amount": 1000.0}],
                "kpi_targets": [
                    {"metric_name": "Leads", "target_value": 1, "unit": "count"},
                    {"metric_name": "leads", "target_value": 2, "unit": "count"},
                ],
                "tasks": [base_task],
            },
        ),
        # e. Task ngoài khoảng chiến dịch (01/09 -> 30/09 là tối đa offset 29).
        (
            "planner-validate-task-range",
            {
                "budget_split": [{"channel_code": "facebook", "planned_amount": 1000.0}],
                "kpi_targets": [],
                "tasks": [{**base_task, "title": "Qua han", "due_offset_days": 999}],
            },
        ),
    ]
    assert channel is not None

    for key, body in cases:
        resp = client.post(
            f"/api/v1/campaigns/{CAMPAIGN_1_ID}/plan/apply",
            json={**body, "idempotency_key": key},
            headers=manager_headers,
        )
        assert resp.status_code == 400, f"{key}: mong đợi 400, nhận {resp.status_code}: {resp.text}"

    # KHÔNG một byte nào được ghi: không dòng mới, không nhật ký khoá thất bại nào.
    assert _counts() == before, "request validation-fail phải không đụng vào CSDL"


def test_apply_rejects_unknown_campaign_and_wrong_roles(client, db_session, manager_headers, approver_headers, beta_marketer_headers):
    body = {
        "budget_split": [{"channel_code": "facebook", "planned_amount": 1000.0}],
        "kpi_targets": [],
        "tasks": [{"title": "X", "task_type": "ADS", "priority": "HIGH", "due_offset_days": 1}],
        "idempotency_key": "planner-apply-auth-001",
    }
    # 404 chiến dịch không tồn tại.
    resp = client.post("/api/v1/campaigns/999999/plan/apply", json=body, headers=manager_headers)
    assert resp.status_code == 404, resp.text

    # Client approver là ws member nhưng không có quyền phân bổ/áp kế hoạch.
    resp = client.post(
        f"/api/v1/campaigns/{CAMPAIGN_1_ID}/plan/apply", json=body, headers=approver_headers
    )
    assert resp.status_code == 403, resp.text

    # Beta workspace: cách ly tenant, không được đụng chiến dịch alpha.
    resp = client.post(
        f"/api/v1/campaigns/{CAMPAIGN_1_ID}/plan/apply", json=body, headers=beta_marketer_headers
    )
    assert resp.status_code == 403, resp.text


# ==============================================================================
# H5: idempotency — dedup khi lặp cùng kế hoạch, 409 khi lặp khoá sai
# ==============================================================================
def test_apply_is_idempotent_for_same_key_and_same_plan(client, db_session, manager_headers):
    plan = _plan_from_ai(client, manager_headers)
    payload = {
        "budget_split": plan["budget_split"],
        "kpi_targets": [],
        "tasks": plan["tasks"],
        "idempotency_key": "planner-apply-dedup-001",
    }
    url = f"/api/v1/campaigns/{CAMPAIGN_1_ID}/plan/apply"

    first = client.post(url, json=payload, headers=manager_headers)
    assert first.status_code == 200, first.text
    assert first.json()["deduplicated"] is False

    after_first = (
        db_session.query(CampaignPlanApplication)
        .filter(CampaignPlanApplication.idempotency_key == "planner-apply-dedup-001")
        .count()
    )
    assert after_first == 1
    alloc_count = (
        db_session.query(CampaignBudgetAllocation)
        .filter(CampaignBudgetAllocation.campaign_id == CAMPAIGN_1_ID)
        .count()
    )
    task_count = db_session.query(Task).filter(Task.campaign_id == CAMPAIGN_1_ID).count()

    # Gửi lại y hệt (double-click / retry mạng): 200 dedup, không ghi gì thêm.
    second = client.post(url, json=payload, headers=manager_headers)
    assert second.status_code == 200, second.text
    second_body = second.json()
    assert second_body["deduplicated"] is True
    assert second_body["tasks_created"] == 0
    assert second_body["budget_allocations"], "dedup vẫn trả trạng thái hiện tại"

    assert (
        db_session.query(CampaignPlanApplication)
        .filter(CampaignPlanApplication.idempotency_key == "planner-apply-dedup-001")
        .count()
    ) == 1
    assert (
        db_session.query(CampaignBudgetAllocation)
        .filter(CampaignBudgetAllocation.campaign_id == CAMPAIGN_1_ID)
        .count()
    ) == alloc_count
    assert db_session.query(Task).filter(Task.campaign_id == CAMPAIGN_1_ID).count() == task_count


def test_apply_same_key_with_different_plan_returns_409(client, manager_headers):
    plan = _plan_from_ai(client, manager_headers)
    url = f"/api/v1/campaigns/{CAMPAIGN_1_ID}/plan/apply"
    key = "planner-apply-conflict-001"

    first = client.post(
        url,
        json={
            "budget_split": plan["budget_split"],
            "kpi_targets": [],
            "tasks": plan["tasks"],
            "idempotency_key": key,
        },
        headers=manager_headers,
    )
    assert first.status_code == 200, first.text

    # Cùng khoá nhưng kế hoạch KHÁC: không được im lặng trả kết quả cũ -> 409.
    second = client.post(
        url,
        json={
            "budget_split": [{"channel_code": "facebook", "planned_amount": 1234567.0}],
            "kpi_targets": [],
            "tasks": [{"title": "Khac", "task_type": "ADS", "priority": "HIGH", "due_offset_days": 2}],
            "idempotency_key": key,
        },
        headers=manager_headers,
    )
    assert second.status_code == 409, second.text


# ==============================================================================
# H6: OpenAPI — /ai/plan là đường cũ (deprecated), apply là đường mới
# ==============================================================================
def test_plan_openapi_marks_sync_deprecated_and_apply_current():
    import app.main as main_module

    paths = main_module.app.openapi()["paths"]
    sync_op = paths["/api/v1/ai/plan"]["post"]
    assert "POST /ai/jobs" in (sync_op.get("description") or "")
    assert "kind=plan" in (sync_op.get("description") or "")

    apply_op = paths["/api/v1/campaigns/{campaign_id}/plan/apply"]["post"]
    assert apply_op.get("deprecated") is not True
