"""Hạn mức gói miễn phí theo workspace (`app/services/quota.py`).

TRỌNG TÂM CỦA BỘ TEST NÀY — ba điều dễ làm sai nhất:

1. **Hạn mứng phải thực thi ở SERVER.** Mỗi điểm chặn có ít nhất một test gọi
   HTTP thật và khẳng định 429. Nhóm `test_*_endpoint_*` kiểm đúng điều đó; một
   hạn mứng chỉ ẩn nút ở UI thì không phải hạn mứng.

2. **AI job phải tính lúc ENQUEUE, và retry idempotent không được tính hai lần.**
   Nhóm `test_ai_job_quota_*` kiểm điều này bằng cách so số hàng `ai_jobs` thực
   sự tồn tại, không tin vào bất kỳ bộ đếm nào trong bộ nhớ.

3. **Hạn mứng không được lộ chéo tenant.** Một workspace đã chạm trần phải không
   ảnh hưởng tới workspace khác — nếu không thì hạn mứng biến thành công cụ đoán
   xem tenant bên cạnh đang dùng bao nhiêu.

Ngoài ra: thông báo lỗi phải máy-đọc-được, và đường ghi đè cho admin phải tồn tại
(và được ghi log).
"""

import json
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.entities import (
    AIJob,
    Campaign,
    MarketingContent,
    MarketingSchedule,
    User,
    Workspace,
    WorkspaceMember,
)
from app.services import quota


@pytest.fixture
def tight_quota(monkeypatch):
    """Hạn mức siết về số nhỏ để test không phải tạo hàng trăm bản ghi."""
    monkeypatch.setattr(settings, "QUOTA_AI_JOBS_PER_DAY", 3)
    monkeypatch.setattr(settings, "QUOTA_MAX_CAMPAIGNS", 2)
    monkeypatch.setattr(settings, "QUOTA_MAX_CONTENTS", 2)
    monkeypatch.setattr(settings, "QUOTA_MAX_WORKSPACE_MEMBERS", 2)
    monkeypatch.setattr(settings, "QUOTA_MAX_SCHEDULES", 1)
    monkeypatch.setattr(settings, "QUOTA_MAX_WORKSPACES_PER_USER", 2)
    monkeypatch.setattr(settings, "QUOTA_OVERRIDE_WORKSPACE_IDS", "")
    return True


def _enqueue_body(**overrides):
    body = {
        "kind": "ideas",
        "idempotency_key": None,
        "campaign_id": 1,
        "channel_code": "facebook",
        "custom_topic": "Kiem thu han muc AI job",
    }
    body.update(overrides)
    return body


def _count_jobs(db: Session, workspace_id: int) -> int:
    return int(db.query(AIJob).filter(AIJob.workspace_id == workspace_id).count())


# ==============================================================================
# 1. THỰC THI Ở SERVER CHO TỪNG ĐIỂM CHẶN
# ==============================================================================
def test_ai_job_quota_endpoint_blocks_after_limit(
    client: TestClient, db_session: Session, manager_headers, workspace_alpha, tight_quota
):
    """Vượt hạn mứng AI job phải trả 429 chứ không tạo job nữa."""
    before = _count_jobs(db_session, workspace_alpha.id)

    for i in range(3):
        resp = client.post(
            "/api/v1/ai/jobs",
            json=_enqueue_body(custom_topic=f"Chủ đề {i}", idempotency_key=f"quota-{i}"),
            headers=manager_headers,
        )
        assert resp.status_code == 202, f"lượt {i}: {resp.text}"

    resp = client.post(
        "/api/v1/ai/jobs",
        json=_enqueue_body(custom_topic="vượt hạn mứng", idempotency_key="quota-over"),
        headers=manager_headers,
    )
    assert resp.status_code == 429, f"Phải là 429, nhận {resp.status_code}: {resp.text}"

    # Quan trọng: bị chặn thì KHÔNG được tạo job. Đây là chỗ nhiều bản hiện thực
    # trừ trước rồi mới từ chối, làm lệch bộ đếm.
    assert _count_jobs(db_session, workspace_alpha.id) == before + 3


def test_campaign_quota_endpoint_blocks_after_limit(
    client: TestClient, db_session: Session, manager_headers, workspace_alpha, tight_quota
):
    existing = int(db_session.query(Campaign).filter(Campaign.workspace_id == workspace_alpha.id).count())
    allowed = max(2 - existing, 0)

    for i in range(allowed):
        resp = client.post(
            "/api/v1/campaigns",
            json={
                "product_id": 1, "name": f"Quota campaign {i}",
                "objective": "o", "audience": "a",
                "start_date": "2026-01-01", "end_date": "2026-12-31", "budget": 1000,
            },
            headers=manager_headers,
        )
        assert resp.status_code == 201, f"lượt {i}: {resp.text}"

    blocked = client.post(
        "/api/v1/campaigns",
        json={
            "product_id": 1, "name": "Campaign vượt hạn mứng",
            "objective": "o", "audience": "a",
            "start_date": "2026-01-01", "end_date": "2026-12-31", "budget": 1000,
        },
        headers=manager_headers,
    )
    assert blocked.status_code == 429, f"Phải là 429, nhận {blocked.status_code}"
    assert quota.LIMIT_CAMPAIGNS in json.dumps(blocked.json(), ensure_ascii=False)


def test_content_quota_endpoint_blocks_after_limit(
    client: TestClient, db_session: Session, manager_headers, workspace_alpha, tight_quota
):
    """Hạn mứng nội dung chặn ở `POST /contents` với thân lỗi máy-đọc-được."""
    existing = int(
        db_session.query(MarketingContent).filter(MarketingContent.workspace_id == workspace_alpha.id).count()
    )
    campaign = db_session.query(Campaign).filter(Campaign.workspace_id == workspace_alpha.id).first()
    if campaign is None:
        pytest.skip("Cần ít nhất một campaign trong workspace alpha")

    def _post(title):
        return client.post(
            "/api/v1/contents",
            json={"campaign_id": campaign.id, "channel_id": 1, "title": title, "body": "nội dung"},
            headers=manager_headers,
        )

    for i in range(max(2 - existing, 0)):
        assert _post(f"Nội dung quota {i}").status_code == 201

    blocked = _post("Nội dung vượt hạn mứng")
    assert blocked.status_code == 429, f"Phải là 429, nhận {blocked.status_code}"
    detail = blocked.json()["detail"]
    assert detail["error"] == "quota_exceeded"
    assert detail["limit_code"] == quota.LIMIT_CONTENTS


def test_workspace_member_quota_endpoint_blocks_after_limit(
    client: TestClient, db_session: Session, rbac_headers, workspace_beta, tight_quota
):
    """Hạn mứng thành viên chặn ở `POST /workspaces/{id}/members`."""
    headers = rbac_headers["beta_agency_manager"]
    candidates = [
        u for u in db_session.query(User).filter(User.email.like("%@gmail.com")).all()
        if u.email not in ("manager@gmail.com", "marketer@gmail.com", "agency_mgr_beta@gmail.com")
    ]
    assert len(candidates) >= 3, "Cần đủ user để vượt trần thành viên"

    statuses = []
    for user in candidates[:4]:
        statuses.append(
            client.post(
                f"/api/v1/workspaces/{workspace_beta.id}/members",
                json={"email": user.email, "role": "MARKETER"},
                headers=headers,
            ).status_code
        )
    assert 429 in statuses, f"Phải có lần bị 429, nhận {statuses}"


def test_schedule_quota_endpoint_blocks_after_limit(
    client: TestClient, db_session: Session, manager_headers, workspace_alpha, tight_quota
):
    """Hạn mứng lịch đăng chặn ở `POST /contents/{id}/schedule`."""
    campaign = db_session.query(Campaign).filter(Campaign.workspace_id == workspace_alpha.id).first()
    if campaign is None:
        pytest.skip("Cần campaign")

    # Tự dựng một bài APPROVED: endpoint lập lịch bắt buộc nội dung phải được duyệt,
    # nên test không được phụ thuộc vào việc seed có sẵn bài APPROVED hay không.
    approved = MarketingContent(
        workspace_id=workspace_alpha.id,
        campaign_id=campaign.id,
        channel_id=1,
        created_by=campaign.owner_id,
        title="Bài APPROVED để đo hạn mứng lịch",
        body="nội dung",
        status="APPROVED",
    )
    db_session.add(approved)
    db_session.commit()
    db_session.refresh(approved)

    def _schedule():
        return client.post(
            f"/api/v1/contents/{approved.id}/schedule",
            json={"scheduled_at": "2026-11-01T09:00:00", "timezone": "Asia/Ho_Chi_Minh"},
            headers=manager_headers,
        )

    first = _schedule()
    assert first.status_code == 201, f"Lịch đầu tiên phải tạo được: {first.text}"

    blocked = _schedule()
    assert blocked.status_code == 429, f"Lịch thứ hai phải bị chặn, nhận {blocked.status_code}"
    detail = blocked.json()["detail"]
    assert detail["limit_code"] == quota.LIMIT_SCHEDULES
    # Lịch bị chặn thì không được ghi thêm hàng.
    assert int(
        db_session.query(MarketingSchedule).filter(MarketingSchedule.content_id == approved.id).count()
    ) == 1


def test_workspaces_per_user_quota_blocks_after_limit(
    client: TestClient, db_session: Session, manager_headers, tight_quota
):
    """Hạn mứng workspace tính THEO NGƯỜI DÙNG, không theo workspace."""
    owned = int(db_session.query(Workspace).filter(Workspace.owner_id.in_(
        db_session.query(User.id).filter(User.email == "manager@gmail.com")
    )).count())

    statuses = []
    for i in range(max(2 - owned, 0) + 2):
        statuses.append(
            client.post("/api/v1/workspaces", json={"name": f"Quota ws {i}"}, headers=manager_headers).status_code
        )
    assert 429 in statuses, f"Phải có lần bị 429, nhận {statuses}"


# ==============================================================================
# 2. AI JOB: TÍNH LÚC ENQUEUE, RETRY KHÔNG TÍNH HAI LẦN
# ==============================================================================
def test_ai_job_quota_is_charged_at_enqueue_not_at_completion(
    client: TestClient, db_session: Session, manager_headers, workspace_alpha, monkeypatch
):
    """Lượt tiêu phải bị trừ khi job ĐƯỢC NHẬN, không chờ job chạy xong.

    Test này đặt trần = 1, nhận một job, rồi kiểm tra hàng `ai_jobs` đã có ngay
    mà KHÔNG cần worker chạy. Nếu ai đó dời việc tính hạn mứng xuống lúc hoàn
    thành, phép đo này bắt được ngay.
    """
    monkeypatch.setattr(settings, "QUOTA_AI_JOBS_PER_DAY", 1)
    before = _count_jobs(db_session, workspace_alpha.id)

    resp = client.post(
        "/api/v1/ai/jobs",
        json=_enqueue_body(custom_topic="tính lúc enqueue", idempotency_key="charge-at-enqueue"),
        headers=manager_headers,
    )
    assert resp.status_code == 202, resp.text

    # Không có worker nào chạy; job vẫn ở trạng thái `queued`.
    job = db_session.query(AIJob).filter(AIJob.idempotency_key == "charge-at-enqueue").first()
    assert job is not None, "Job phải được tạo ngay lúc enqueue"
    assert job.status == "queued", "Job chưa được worker chạy — đúng, đang ở `queued`"

    # Đã tốn 1 lượt dù job chưa hoàn thành.
    assert _count_jobs(db_session, workspace_alpha.id) == before + 1
    snapshot = quota.measure(db_session, quota.LIMIT_AI_JOBS_PER_DAY, workspace_id=workspace_alpha.id)
    assert snapshot.used == before + 1


def test_ai_job_quota_is_not_double_charged_on_idempotent_retry(
    client: TestClient, db_session: Session, manager_headers, workspace_alpha, tight_quota
):
    """Gửi lại CÙNG idempotency_key nhiều lần chỉ tiêu đúng một lượt."""
    before = _count_jobs(db_session, workspace_alpha.id)
    body = _enqueue_body(custom_topic="retry một lần logic", idempotency_key="no-double-charge")

    responses = [client.post("/api/v1/ai/jobs", json=body, headers=manager_headers) for _ in range(4)]
    assert [r.status_code for r in responses] == [202, 202, 202, 202]
    # Chỉ lần đầu `deduplicated=False`, các lần sau trả lại job cũ.
    assert [r.json()["deduplicated"] for r in responses] == [False, True, True, True]
    assert len({r.json()["job_id"] for r in responses}) == 1

    assert _count_jobs(db_session, workspace_alpha.id) == before + 1, (
        "Retry idempotent phải chỉ tạo MỘT hàng ai_jobs — mỗi hàng là một lượt tiêu"
    )

    # Quan trọng hơn: trần 3 vẫn còn 2 lượt trống, tức retry không đốt hạn mứng.
    snapshot = quota.measure(db_session, quota.LIMIT_AI_JOBS_PER_DAY, workspace_id=workspace_alpha.id)
    assert snapshot.used == before + 1


def test_ai_job_quota_retry_survives_to_the_limit_boundary(
    client: TestClient, db_session: Session, manager_headers, workspace_alpha, monkeypatch
):
    """Ngay sát trần, retry vẫn không bị tính lần hai.

    Trước đây phép thử "không tính hai lần" dễ pass khi còn nhiều lượt trống. Ở đây
    ta điền kín hạn mức rồi retry: nếu retry bị tính lần hai thì lượt tiếp theo
    bị chặn oan.
    """
    monkeypatch.setattr(settings, "QUOTA_AI_JOBS_PER_DAY", 2)
    body = _enqueue_body(custom_topic="retry sát trần", idempotency_key="boundary-retry")

    first = client.post("/api/v1/ai/jobs", json=body, headers=manager_headers)
    assert first.status_code == 202
    job_id = first.json()["job_id"]

    # Điền nốt lượt còn lại bằng một yêu cầu KHÁC.
    second = client.post(
        "/api/v1/ai/jobs",
        json=_enqueue_body(custom_topic="lượt thứ hai", idempotency_key="boundary-second"),
        headers=manager_headers,
    )
    assert second.status_code == 202

    # Retry yêu cầu cũ: vẫn 202, vẫn job cũ, không đốt lượt nào.
    for _ in range(3):
        retry = client.post("/api/v1/ai/jobs", json=body, headers=manager_headers)
        assert retry.status_code == 202
        assert retry.json()["job_id"] == job_id
        assert retry.json()["deduplicated"] is True


def test_ai_job_quota_resets_only_after_window_passes(
    db_session: Session, workspace_alpha, monkeypatch
):
    """Job ngoài cửa sổ 24 giờ không còn bị tính."""
    monkeypatch.setattr(settings, "QUOTA_AI_JOBS_PER_DAY", 2)
    now = datetime(2026, 10, 8, 12, 0, tzinfo=timezone.utc)

    for i in range(2):
        db_session.add(
            AIJob(
                workspace_id=workspace_alpha.id, user_id=1, kind="ideas", status="queued",
                payload_json="{}", idempotency_key=f"old-{i}",
                payload_hash=f"h{i}", queued_at=now - timedelta(hours=30),
                available_at=now - timedelta(hours=30), created_at=now - timedelta(hours=30),
            )
        )
    db_session.commit()

    snapshot = quota.measure(
        db_session, quota.LIMIT_AI_JOBS_PER_DAY, workspace_id=workspace_alpha.id, now=now
    )
    assert snapshot.used == 0, "Job 30 giờ trước phải nằm ngoài cửa sổ 24 giờ"
    assert snapshot.resets_at is None, "Không có job trong cửa sổ thì không có mốc reset"

    # Thêm một job trong cửa sổ -> used=1 và có mốc reset.
    db_session.add(
        AIJob(
            workspace_id=workspace_alpha.id, user_id=1, kind="ideas", status="queued",
            payload_json="{}", idempotency_key="fresh-1", payload_hash="hf",
            queued_at=now - timedelta(hours=2), available_at=now - timedelta(hours=2),
            created_at=now - timedelta(hours=2),
        )
    )
    db_session.commit()
    snapshot = quota.measure(
        db_session, quota.LIMIT_AI_JOBS_PER_DAY, workspace_id=workspace_alpha.id, now=now
    )
    assert snapshot.used == 1
    # Reset = job cũ nhất trong cửa sổ + 24h.
    assert snapshot.resets_at == now - timedelta(hours=2) + quota.AI_JOBS_WINDOW


def test_failed_and_cancelled_jobs_still_count_as_charged(
    db_session: Session, workspace_alpha, monkeypatch
):
    """Job hỏng/huỷ VẪN bị tính — nó đã chiếm slot và đã cố gọi LLM.

    Nếu chỉ đếm job `succeeded`, kẻ lạm dụng sẽ tạo hàng trăm job toàn lỗi để
    tiêu hạn mức của người khác mà không tốn lượt nào của chính mình.
    """
    monkeypatch.setattr(settings, "QUOTA_AI_JOBS_PER_DAY", 5)
    now = datetime(2026, 10, 8, 12, 0, tzinfo=timezone.utc)
    for status in ("failed", "cancelled", "succeeded", "running"):
        db_session.add(
            AIJob(
                workspace_id=workspace_alpha.id, user_id=1, kind="ideas", status=status,
                payload_json="{}", idempotency_key=f"st-{status}", payload_hash=f"h-{status}",
                queued_at=now - timedelta(hours=1), available_at=now - timedelta(hours=1),
                created_at=now - timedelta(hours=1),
            )
        )
    db_session.commit()

    snapshot = quota.measure(
        db_session, quota.LIMIT_AI_JOBS_PER_DAY, workspace_id=workspace_alpha.id, now=now
    )
    assert snapshot.used == 4, "Mọi trạng thái job đều phải bị tính"


# ==============================================================================
# 3. THÔNG BÁO LỖI MÁY-ĐỌC-ĐƯỢC
# ==============================================================================
def test_quota_error_names_limit_value_and_reset(
    client: TestClient, manager_headers, workspace_alpha, monkeypatch
):
    """429 phải nói rõ: vượt hạn mức nào, bao nhiêu, bao giờ hết."""
    monkeypatch.setattr(settings, "QUOTA_AI_JOBS_PER_DAY", 1)
    body = _enqueue_body(custom_topic="đo lỗi", idempotency_key="err-detail")

    assert client.post("/api/v1/ai/jobs", json=body, headers=manager_headers).status_code == 202
    blocked = client.post("/api/v1/ai/jobs", json=body, headers=manager_headers)
    # Retry idempotent KHÔNG phải 429 — nó trả job cũ. Dùng payload khác để vượt.
    assert blocked.status_code == 202
    assert blocked.json()["deduplicated"] is True

    over = client.post(
        "/api/v1/ai/jobs",
        json=_enqueue_body(custom_topic="lượt vượt", idempotency_key="err-detail-2"),
        headers=manager_headers,
    )
    assert over.status_code == 429, over.text

    detail = over.json()["detail"]
    assert detail["error"] == "quota_exceeded"
    assert detail["limit_code"] == quota.LIMIT_AI_JOBS_PER_DAY
    assert detail["limit"] == 1
    assert detail["used"] == 1
    assert detail["remaining"] == 0
    assert detail["requested"] == 1
    assert detail["scope"] == "workspace"
    # Cửa sổ trượt nên PHẢI có mốc reset + Retry-After.
    assert detail["resets_at"], "Hạn mứng theo cửa sổ phải có mốc reset"
    assert detail["retry_after_seconds"] > 0
    assert int(over.headers["Retry-After"]) >= 1
    # Thông báo cho người dùng phải nêu con số, không chỉ là "429".
    assert "1/1" in detail["message"]


def test_gauge_limit_error_says_it_does_not_auto_reset(
    client: TestClient, manager_headers, workspace_alpha, tight_quota
):
    """Đồng hồ tích luỹ không tự xoá — thông báo phải nói rõ để user biết phải xoá gì."""
    # Tạo cho tới khi bị chặn.
    for i in range(3):
        resp = client.post(
            "/api/v1/campaigns",
            json={
                "product_id": 1, "name": f"C {i}", "objective": "o", "audience": "a",
                "start_date": "2026-01-01", "end_date": "2026-12-31", "budget": 1,
            },
            headers=manager_headers,
        )
        assert resp.status_code in (201, 429), f"lượt {i}: {resp.status_code} {resp.text}"

    blocked = client.post(
        "/api/v1/campaigns",
        json={
            "product_id": 1, "name": "C chặn", "objective": "o", "audience": "a",
            "start_date": "2026-01-01", "end_date": "2026-12-31", "budget": 1,
        },
        headers=manager_headers,
    )
    assert blocked.status_code == 429
    detail = blocked.json()["detail"]
    assert detail["resets_at"] is None
    assert "KHÔNG tự đặt lại" in detail["message"]


# ==============================================================================
# 4. CÁCH LY TENANT + ĐƯỜNG GHI ĐỀ ADMIN
# ==============================================================================
def test_quota_is_scoped_per_workspace(
    client: TestClient, db_session: Session, rbac_headers, workspace_alpha, workspace_beta, monkeypatch
):
    """Workspace Beta chạm trần KHÔNG được chặn Workspace Alpha."""
    # Trần 3: seed có ~2 chiến dịch ở Alpha, nên Alpha còn chỗ còn Beta thì không.
    monkeypatch.setattr(settings, "QUOTA_MAX_CAMPAIGNS", 3)
    headers = rbac_headers["beta_agency_manager"]

    beta_before = quota.measure(db_session, quota.LIMIT_CAMPAIGNS, workspace_id=workspace_beta.id).used
    alpha_before = quota.measure(db_session, quota.LIMIT_CAMPAIGNS, workspace_id=workspace_alpha.id).used

    statuses = []
    for i in range(6):
        statuses.append(
            client.post(
                "/api/v1/campaigns",
                json={
                    "product_id": 1, "name": f"Beta {i}", "objective": "o", "audience": "a",
                    "start_date": "2026-01-01", "end_date": "2026-12-31", "budget": 1,
                },
                headers=headers,
            ).status_code
        )
    assert 429 in statuses, f"Beta phải bị chặn khi đạt trần của chính nó, nhận {statuses}"

    beta_after = quota.measure(db_session, quota.LIMIT_CAMPAIGNS, workspace_id=workspace_beta.id).used
    assert beta_after <= 3, "Beta không được vượt trần"
    assert beta_after > beta_before, "Beta phải tạo được tới trần"

    # Alpha không bị hạn mứng của Beta chặn: số của Alpha vẫn nguyên và còn chỗ.
    alpha_now = quota.measure(db_session, quota.LIMIT_CAMPAIGNS, workspace_id=workspace_alpha.id)
    assert alpha_now.used == alpha_before, (
        "Việc Beta tạo chiến dịch không được làm đổi bộ đếm của Alpha"
    )
    assert alpha_now.used < 3, "Alpha phải còn chỗ để phép thử có ý nghĩa"

    alpha = client.post(
        "/api/v1/campaigns",
        json={
            "product_id": 1, "name": "Alpha vẫn OK", "objective": "o", "audience": "a",
            "start_date": "2026-01-01", "end_date": "2026-12-31", "budget": 1,
        },
        headers=rbac_headers["manager"],
    )
    assert alpha.status_code == 201, f"Alpha phải không bị hạn mứng của Beta chặn: {alpha.text}"


def test_admin_role_is_exempt_and_logged(
    db_session: Session, workspace_alpha, monkeypatch, caplog
):
    """ADMIN được miễn, và việc miễn phải được GHI LOG.

    Một lớp phòng thủ bị bỏ qua trong im lặng thì không còn là lớp phòng thủ.
    """
    monkeypatch.setattr(settings, "QUOTA_MAX_CAMPAIGNS", 0)
    admin = db_session.query(User).filter(User.role == "ADMIN").first()
    if admin is None:
        admin = User(
            email="quota_admin_probe@gmail.com", full_name="Quota Admin Probe",
            password_hash="khong-dung-de-dang-nhap", role="ADMIN", status="ACTIVE",
        )
        db_session.add(admin)
        db_session.commit()

    with caplog.at_level("WARNING", logger="marketflow.quota"):
        snapshot = quota.enforce(
            db_session, quota.LIMIT_CAMPAIGNS, user=admin, workspace_id=workspace_alpha.id
        )
    assert snapshot.limit == 0, "Vẫn trả snapshot đúng để UI hiển thị"
    assert any("MIEN" in r.message for r in caplog.records), (
        "Dùng đường miễn trần mà không ghi log thì không kiểm soát được"
    )


def test_env_override_workspace_ids_is_honoured_and_logged(
    db_session: Session, workspace_alpha, monkeypatch, caplog
):
    """`QUOTA_OVERRIDE_WORKSPACE_IDS` là đường ghi đè theo env, có ghi log."""
    monkeypatch.setattr(settings, "QUOTA_MAX_CAMPAIGNS", 0)
    monkeypatch.setattr(settings, "QUOTA_OVERRIDE_WORKSPACE_IDS", f"9999, {workspace_alpha.id}, abc")

    manager = db_session.query(User).filter(User.email == "manager@gmail.com").first()
    with caplog.at_level("WARNING", logger="marketflow.quota"):
        quota.enforce(db_session, quota.LIMIT_CAMPAIGNS, user=manager, workspace_id=workspace_alpha.id)

    assert any("QUOTA_OVERRIDE_WORKSPACE_IDS" in r.message for r in caplog.records)
    # Mục không phải số phải bị bỏ qua có log, không làm sập khởi động.
    assert any("khong phai so nguyen" in r.message or "không phải số nguyên" in r.message
               for r in caplog.records), "Giá trị rác trong env phải được bỏ qua kèm cảnh báo"


def test_override_does_not_leak_to_other_workspaces(
    db_session: Session, workspace_alpha, workspace_beta, monkeypatch
):
    """Workspace trong danh sách miễn không kéo theo workspace khác."""
    monkeypatch.setattr(settings, "QUOTA_MAX_CAMPAIGNS", 0)
    monkeypatch.setattr(settings, "QUOTA_OVERRIDE_WORKSPACE_IDS", str(workspace_alpha.id))
    manager = db_session.query(User).filter(User.email == "manager@gmail.com").first()

    from fastapi import HTTPException

    quota.enforce(db_session, quota.LIMIT_CAMPAIGNS, user=manager, workspace_id=workspace_alpha.id)
    with pytest.raises(HTTPException) as exc:
        quota.enforce(db_session, quota.LIMIT_CAMPAIGNS, user=manager, workspace_id=workspace_beta.id)
    assert exc.value.status_code == 429


# ==============================================================================
# 5. ENDPOINT BÁO CÁO HẠN MỨC (cho UI đếm ngược)
# ==============================================================================
def test_quota_snapshot_endpoint_shape(client: TestClient, manager_headers, workspace_alpha):
    """`GET /workspaces/{id}/quota` trả đủ mọi hạn mức kèm mốc reset."""
    resp = client.get(f"/api/v1/workspaces/{workspace_alpha.id}/quota", headers=manager_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["workspace_id"] == workspace_alpha.id
    codes = {item["limit_code"] for item in body["limits"]}
    for expected in (
        quota.LIMIT_AI_JOBS_PER_DAY, quota.LIMIT_CAMPAIGNS, quota.LIMIT_CONTENTS,
        quota.LIMIT_WORKSPACE_MEMBERS, quota.LIMIT_SCHEDULES, quota.LIMIT_WORKSPACES_PER_USER,
    ):
        assert expected in codes, f"Thiếu hạn mức {expected}"
    for item in body["limits"]:
        assert {"limit_code", "label", "used", "limit", "remaining", "exceeded", "scope", "resets_at"} <= set(item)
        assert item["remaining"] == max(item["limit"] - item["used"], 0)


def test_quota_snapshot_respects_tenant_isolation(
    client: TestClient, rbac_headers, workspace_alpha, workspace_beta
):
    """Đọc hạn mứng của workspace mình không thuộc về phải bị chặn như mọi endpoint khác."""
    resp = client.get(
        f"/api/v1/workspaces/{workspace_beta.id}/quota", headers=rbac_headers["marketer"]
    )
    assert resp.status_code == 403, f"Phải là 403, nhận {resp.status_code}"


def test_quota_snapshot_requires_auth(client: TestClient, workspace_alpha):
    assert client.get(f"/api/v1/workspaces/{workspace_alpha.id}/quota").status_code == 401


# ==============================================================================
# 6. ĐO LƯỜNG ĐÚNG SỐ BẢN GHI THẬT
# ==============================================================================
def test_gauge_limits_count_actual_rows(db_session: Session, workspace_alpha, monkeypatch):
    """Đồng hồ đếm bản ghi thật, không dùng bộ đếm phụ (nên không thể lệch)."""
    monkeypatch.setattr(settings, "QUOTA_MAX_CAMPAIGNS", 100)
    monkeypatch.setattr(settings, "QUOTA_MAX_CONTENTS", 100)
    monkeypatch.setattr(settings, "QUOTA_MAX_WORKSPACE_MEMBERS", 100)
    monkeypatch.setattr(settings, "QUOTA_MAX_SCHEDULES", 100)
    monkeypatch.setattr(settings, "QUOTA_MAX_WORKSPACES_PER_USER", 100)

    campaigns = quota.measure(db_session, quota.LIMIT_CAMPAIGNS, workspace_id=workspace_alpha.id)
    assert campaigns.used == db_session.query(Campaign).filter(
        Campaign.workspace_id == workspace_alpha.id
    ).count()

    contents = quota.measure(db_session, quota.LIMIT_CONTENTS, workspace_id=workspace_alpha.id)
    assert contents.used == db_session.query(MarketingContent).filter(
        MarketingContent.workspace_id == workspace_alpha.id
    ).count()

    members = quota.measure(db_session, quota.LIMIT_WORKSPACE_MEMBERS, workspace_id=workspace_alpha.id)
    assert members.used == db_session.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_alpha.id
    ).count()

    schedules = quota.measure(db_session, quota.LIMIT_SCHEDULES, workspace_id=workspace_alpha.id)
    expected = db_session.query(MarketingSchedule).join(
        MarketingContent, MarketingSchedule.content_id == MarketingContent.id
    ).filter(MarketingContent.workspace_id == workspace_alpha.id).count()
    assert schedules.used == expected


def test_schedule_quota_follows_content_workspace(
    db_session: Session, workspace_alpha, workspace_beta, monkeypatch
):
    """Lịch đăng không có `workspace_id` nên phải suy qua nội dung cha."""
    monkeypatch.setattr(settings, "QUOTA_MAX_SCHEDULES", 100)
    campaign = db_session.query(Campaign).filter(Campaign.workspace_id == workspace_beta.id).first()
    if campaign is None:
        pytest.skip("Cần campaign ở workspace beta")

    content = MarketingContent(
        workspace_id=workspace_beta.id, campaign_id=campaign.id, channel_id=1,
        created_by=campaign.owner_id, title="Lịch của beta", body="b", status="APPROVED",
    )
    db_session.add(content)
    db_session.commit()
    db_session.refresh(content)
    db_session.add(MarketingSchedule(
        content_id=content.id, scheduled_at="2026-11-01T09:00:00",
        timezone="Asia/Ho_Chi_Minh", status="PLANNED", created_by=campaign.owner_id,
    ))
    db_session.commit()

    beta = quota.measure(db_session, quota.LIMIT_SCHEDULES, workspace_id=workspace_beta.id)
    alpha = quota.measure(db_session, quota.LIMIT_SCHEDULES, workspace_id=workspace_alpha.id)
    assert beta.used >= 1, "Lịch của beta phải được tính vào beta"
    assert alpha.used == 0, "Lịch của beta KHÔNG được tính vào alpha"


def test_unknown_limit_code_raises(db_session: Session):
    with pytest.raises(ValueError):
        quota.measure(db_session, "khong_ton_tai", workspace_id=1)