import pytest
from pydantic import ValidationError
from app.models.entities import MarketingContent, Campaign, User, ContentReview
from app.schemas.schemas import ReviewCreate


# ==============================================================================
# 1. REJECTION REASON VALIDATION CONSISTENCY (MINIMUM 3 CHARACTERS)
# ==============================================================================
def test_review_create_schema_validation_length():
    """Test ReviewCreate schema enforces minimum 3 characters for reason."""
    # Under 3 characters should raise ValidationError
    with pytest.raises(ValidationError):
        ReviewCreate(decision="REJECTED", reason="ab")

    with pytest.raises(ValidationError):
        ReviewCreate(decision="REJECTED", reason="a")

    with pytest.raises(ValidationError):
        ReviewCreate(decision="REJECTED", reason="  a  ")

    with pytest.raises(ValidationError):
        ReviewCreate(decision="REJECTED", reason="   ")

    # 3 characters or more should pass
    r3 = ReviewCreate(decision="REJECTED", reason="abc")
    assert r3.reason == "abc"

    r_long = ReviewCreate(decision="REJECTED", reason="Nội dung cần chỉnh sửa theo nhận diện thương hiệu")
    assert r_long.reason == "Nội dung cần chỉnh sửa theo nhận diện thương hiệu"

    # APPROVED without reason is permitted
    r_appr = ReviewCreate(decision="APPROVED")
    assert r_appr.reason is None


def test_reject_endpoint_rejects_under_3_chars(client, db_session, manager_headers, marketer_headers, workspace_alpha):
    """Test POST /contents/{id}/reject rejects reasons with fewer than 3 characters."""
    mkt = db_session.query(User).filter(User.email.in_(["marketer@gmail.com", "marketer@gmail.com"])).first()
    campaign = db_session.query(Campaign).filter(Campaign.workspace_id == workspace_alpha.id).first()

    content = MarketingContent(
        workspace_id=workspace_alpha.id,
        campaign_id=campaign.id,
        channel_id=1,
        created_by=mkt.id,
        title="Bài Viết Thử Nghiệm Lý Do Từ Chối",
        body="Nội dung kiểm tra ràng buộc độ dài tối thiểu 3 ký tự.",
        status="IN_REVIEW",
        version_no=1
    )
    db_session.add(content)
    db_session.commit()
    db_session.refresh(content)

    # 1 char -> 400
    res1 = client.post(f"/api/v1/contents/{content.id}/reject", json={"decision": "REJECTED", "reason": "a"}, headers=manager_headers)
    assert res1.status_code == 400

    # 2 chars -> 400
    res2 = client.post(f"/api/v1/contents/{content.id}/reject", json={"decision": "REJECTED", "reason": "ab"}, headers=manager_headers)
    assert res2.status_code == 400

    # whitespace -> 400
    res3 = client.post(f"/api/v1/contents/{content.id}/reject", json={"decision": "REJECTED", "reason": "   "}, headers=manager_headers)
    assert res3.status_code == 400

    # 3 chars -> 200 OK
    res4 = client.post(f"/api/v1/contents/{content.id}/reject", json={"decision": "REJECTED", "reason": "Bad"}, headers=manager_headers)
    assert res4.status_code == 200
    assert res4.json()["status"] == "REJECTED"


# ==============================================================================
# 2. STATE MACHINE TRANSITION INTEGRITY (HUMAN-IN-THE-LOOP)
# ==============================================================================
def test_valid_lifecycle_transitions(client, db_session, manager_headers, marketer_headers, workspace_alpha):
    """Test full valid lifecycle: DRAFT -> submit -> IN_REVIEW -> approve -> APPROVED -> publish -> PUBLISHED."""
    mkt = db_session.query(User).filter(User.email.in_(["marketer@gmail.com", "marketer@gmail.com"])).first()
    campaign = db_session.query(Campaign).filter(Campaign.workspace_id == workspace_alpha.id).first()

    content = MarketingContent(
        workspace_id=workspace_alpha.id,
        campaign_id=campaign.id,
        channel_id=1,
        created_by=mkt.id,
        title="Chiến Dịch Khai Trương Mới",
        body="Nội dung truyền thông bài bản cho ngày khai trương cửa hàng.",
        cta="Đặt mua ngay",
        status="DRAFT",
        version_no=1
    )
    db_session.add(content)
    db_session.commit()
    db_session.refresh(content)

    # 1. Submit for review
    r_sub = client.post(f"/api/v1/contents/{content.id}/submit", headers=marketer_headers)
    assert r_sub.status_code == 200
    assert r_sub.json()["status"] == "IN_REVIEW"

    # 2. Approve
    r_appr = client.post(f"/api/v1/contents/{content.id}/approve", headers=manager_headers)
    assert r_appr.status_code == 200
    assert r_appr.json()["status"] == "APPROVED"

    # 3. Publish
    r_pub = client.post(f"/api/v1/contents/{content.id}/publish", headers=manager_headers)
    assert r_pub.status_code == 200
    assert r_pub.json()["status"] == "PUBLISHED"


def test_invalid_lifecycle_transitions_blocked(client, db_session, manager_headers, marketer_headers, workspace_alpha):
    """Test invalid state machine jumps are strictly blocked with 400 Bad Request."""
    mkt = db_session.query(User).filter(User.email.in_(["marketer@gmail.com", "marketer@gmail.com"])).first()
    campaign = db_session.query(Campaign).filter(Campaign.workspace_id == workspace_alpha.id).first()

    # DRAFT content cannot be approved directly
    draft = MarketingContent(
        workspace_id=workspace_alpha.id,
        campaign_id=campaign.id,
        channel_id=1,
        created_by=mkt.id,
        title="Bản Nháp Chưa Gửi",
        body="Bản thảo chưa hoàn thiện",
        status="DRAFT",
        version_no=1
    )
    db_session.add(draft)
    db_session.commit()
    db_session.refresh(draft)

    # Cannot approve DRAFT directly
    r_appr_draft = client.post(f"/api/v1/contents/{draft.id}/approve", headers=manager_headers)
    assert r_appr_draft.status_code == 400
    assert "IN_REVIEW" in r_appr_draft.json()["detail"]

    # Cannot publish DRAFT directly
    r_pub_draft = client.post(f"/api/v1/contents/{draft.id}/publish", headers=manager_headers)
    assert r_pub_draft.status_code == 400
    assert "APPROVED" in r_pub_draft.json()["detail"]

    # Cannot reject DRAFT directly
    r_rej_draft = client.post(
        f"/api/v1/contents/{draft.id}/reject",
        json={"decision": "REJECTED", "reason": "Lý do từ chối mẫu"},
        headers=manager_headers
    )
    assert r_rej_draft.status_code == 400


# ==============================================================================
# 3. DIRECT TAMPERING PREVENTION (ANTI-BYPASS)
# ==============================================================================
def test_direct_create_with_approved_or_published_forbidden(client, db_session, marketer_headers, workspace_alpha):
    """POST /contents must reject attempts to create content directly as APPROVED or PUBLISHED."""
    campaign = db_session.query(Campaign).filter(Campaign.workspace_id == workspace_alpha.id).first()

    res_appr = client.post(
        "/api/v1/contents",
        json={
            "campaign_id": campaign.id,
            "channel_id": 1,
            "title": "Hack Approve",
            "body": "Nội dung vượt mặt hàng đợi",
            "status": "APPROVED"
        },
        headers=marketer_headers
    )
    assert res_appr.status_code == 400

    res_pub = client.post(
        "/api/v1/contents",
        json={
            "campaign_id": campaign.id,
            "channel_id": 1,
            "title": "Hack Publish",
            "body": "Nội dung tự xuất bản",
            "status": "PUBLISHED"
        },
        headers=marketer_headers
    )
    assert res_pub.status_code == 400


def test_direct_update_to_approved_or_published_forbidden(client, db_session, marketer_headers, workspace_alpha):
    """PUT /contents/{id} must reject attempts to set status directly to APPROVED or PUBLISHED."""
    mkt = db_session.query(User).filter(User.email.in_(["marketer@gmail.com", "marketer@gmail.com"])).first()
    campaign = db_session.query(Campaign).filter(Campaign.workspace_id == workspace_alpha.id).first()

    content = MarketingContent(
        workspace_id=workspace_alpha.id,
        campaign_id=campaign.id,
        channel_id=1,
        created_by=mkt.id,
        title="Bản Nháp Bình Thường",
        body="Nội dung chưa duyệt",
        status="DRAFT",
        version_no=1
    )
    db_session.add(content)
    db_session.commit()
    db_session.refresh(content)

    res_up_appr = client.put(
        f"/api/v1/contents/{content.id}",
        json={"status": "APPROVED"},
        headers=marketer_headers
    )
    assert res_up_appr.status_code == 400

    res_up_pub = client.put(
        f"/api/v1/contents/{content.id}",
        json={"status": "PUBLISHED"},
        headers=marketer_headers
    )
    assert res_up_pub.status_code == 400


# ==============================================================================
# 4. ANTI-TAMPERING HUMAN-IN-THE-LOOP RESET (EDITING APPROVED -> AI_DRAFT)
# ==============================================================================
def test_editing_approved_content_resets_to_ai_draft(client, db_session, manager_headers, marketer_headers, workspace_alpha):
    """When an APPROVED article is modified (title, body, cta, or image_url),
    it must automatically reset to AI_DRAFT and increment version_no.
    """
    mkt = db_session.query(User).filter(User.email.in_(["marketer@gmail.com", "marketer@gmail.com"])).first()
    campaign = db_session.query(Campaign).filter(Campaign.workspace_id == workspace_alpha.id).first()

    approved_content = MarketingContent(
        workspace_id=workspace_alpha.id,
        campaign_id=campaign.id,
        channel_id=1,
        created_by=mkt.id,
        title="Bài Viết Đã Duyệt",
        body="Nội dung chính xác đã qua thẩm định.",
        cta="Mua ngay",
        image_url="https://example.com/banner-v1.jpg",
        status="APPROVED",
        version_no=1
    )
    db_session.add(approved_content)
    db_session.commit()
    db_session.refresh(approved_content)

    # 1. Modify body -> status automatically resets to AI_DRAFT
    res1 = client.put(
        f"/api/v1/contents/{approved_content.id}",
        json={"body": "Nội dung đã bị thay đổi trái phép!"},
        headers=marketer_headers
    )
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["status"] == "AI_DRAFT"
    assert data1["version_no"] == 2

    # Approve it again
    db_session.refresh(approved_content)
    approved_content.status = "APPROVED"
    db_session.commit()

    # 2. Modify image_url -> status automatically resets to AI_DRAFT
    res2 = client.put(
        f"/api/v1/contents/{approved_content.id}",
        json={"image_url": "https://example.com/new-unapproved-banner.jpg"},
        headers=marketer_headers
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["status"] == "AI_DRAFT"
    assert data2["version_no"] == 3


def test_editing_published_content_resets_to_ai_draft(client, db_session, marketer_headers, workspace_alpha):
    """When a PUBLISHED article is modified, it must automatically reset to AI_DRAFT."""
    mkt = db_session.query(User).filter(User.email.in_(["marketer@gmail.com", "marketer@gmail.com"])).first()
    campaign = db_session.query(Campaign).filter(Campaign.workspace_id == workspace_alpha.id).first()

    pub_content = MarketingContent(
        workspace_id=workspace_alpha.id,
        campaign_id=campaign.id,
        channel_id=1,
        created_by=mkt.id,
        title="Bài Viết Đã Xuất Bản",
        body="Nội dung đã lên sóng mạng xã hội.",
        status="PUBLISHED",
        version_no=1
    )
    db_session.add(pub_content)
    db_session.commit()
    db_session.refresh(pub_content)

    res = client.put(
        f"/api/v1/contents/{pub_content.id}",
        json={"title": "Tiêu Đề Bị Thay Đổi"},
        headers=marketer_headers
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "AI_DRAFT"
    assert data["version_no"] == 2
