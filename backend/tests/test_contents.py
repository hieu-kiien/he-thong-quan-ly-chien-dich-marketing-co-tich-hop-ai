"""Test router /contents & quy trình duyệt (CONTRACT §2, §4, §10)."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import BannedKeyword, Campaign, Channel, Content, User


def test_create_content(
    client: TestClient, marketer1_headers: dict[str, str], sample_campaign: Campaign, test_channels: dict[str, Channel]
):
    resp = client.post(
        "/api/v1/contents",
        headers=marketer1_headers,
        json={
            "campaign_id": sample_campaign.id,
            "channel_code": "FACEBOOK",
            "content_type": "SOCIAL_POST",
            "title": "Nội dung bài viết mới",
            "body": "Nội dung thân bài chi tiết...",
            "cta": "Bấm vào link",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "DRAFT"
    assert data["origin"] == "MANUAL"
    assert data["campaign"]["id"] == sample_campaign.id
    assert data["created_by"]["full_name"] == "Trần Thị Lan Anh Test"


def test_create_content_channel_not_in_campaign(
    client: TestClient, marketer1_headers: dict[str, str], sample_campaign: Campaign, test_channels: dict[str, Channel]
):
    # WEBSITE is not in sample_campaign (which only has FACEBOOK & INSTAGRAM)
    resp = client.post(
        "/api/v1/contents",
        headers=marketer1_headers,
        json={
            "campaign_id": sample_campaign.id,
            "channel_code": "WEBSITE",
            "content_type": "SOCIAL_POST",
            "title": "Bài viết sai kênh",
            "body": "Nội dung...",
        },
    )
    assert resp.status_code == 422
    assert "channel_code" in resp.json()["detail"]["fields"]


def test_submit_content_with_banned_matches(
    client: TestClient,
    marketer1_headers: dict[str, str],
    sample_content: Content,
    db: Session,
):
    # Add a banned keyword
    db.add(BannedKeyword(keyword="cam kết 100%", note="Từ cấm"))
    sample_content.body = "Sản phẩm của chúng tôi cam kết 100% chất lượng cao!"
    db.commit()

    resp = client.post(f"/api/v1/contents/{sample_content.id}/submit", headers=marketer1_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "PENDING_REVIEW"
    assert len(data["banned_matches"]) == 1
    assert data["banned_matches"][0]["keyword"] == "cam kết 100%"
    assert data["banned_matches"][0]["count"] == 1


def test_marketer_cannot_approve(
    client: TestClient, marketer2_headers: dict[str, str], sample_content: Content, db: Session
):
    sample_content.status = "PENDING_REVIEW"
    db.commit()

    resp = client.post(f"/api/v1/contents/{sample_content.id}/approve", headers=marketer2_headers)
    assert resp.status_code == 403


def test_manager_cannot_approve_own_content(
    client: TestClient,
    manager_headers: dict[str, str],
    manager_user: User,
    sample_campaign: Campaign,
    test_channels: dict[str, Channel],
    db: Session,
):
    # Manager creates content
    content = Content(
        campaign_id=sample_campaign.id,
        channel_id=test_channels["FACEBOOK"].id,
        content_type="SOCIAL_POST",
        title="Bài viết của quản lý",
        body="Nội dung...",
        status="PENDING_REVIEW",
        created_by=manager_user.id,
    )
    db.add(content)
    db.commit()
    db.refresh(content)

    # Manager tries to approve own content -> 403 CANNOT_REVIEW_OWN
    resp = client.post(f"/api/v1/contents/{content.id}/approve", headers=manager_headers)
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "CANNOT_REVIEW_OWN"


def test_approve_and_reject_flow(
    client: TestClient, manager_headers: dict[str, str], sample_content: Content, db: Session
):
    sample_content.status = "PENDING_REVIEW"
    db.commit()

    # Reject without comment -> 422
    resp = client.post(f"/api/v1/contents/{sample_content.id}/reject", headers=manager_headers, json={"comment": ""})
    assert resp.status_code == 422

    # Reject with comment -> REJECTED
    resp = client.post(
        f"/api/v1/contents/{sample_content.id}/reject",
        headers=manager_headers,
        json={"comment": "Chưa đạt yêu cầu hình ảnh"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "REJECTED"

    # Now marketer re-submits
    sample_content.status = "PENDING_REVIEW"
    db.commit()

    # Manager approves
    resp = client.post(
        f"/api/v1/contents/{sample_content.id}/approve",
        headers=manager_headers,
        json={"comment": "Duyệt tốt"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "APPROVED"

    # Check reviews list
    reviews_resp = client.get(f"/api/v1/contents/{sample_content.id}/reviews", headers=manager_headers)
    assert reviews_resp.status_code == 200
    assert len(reviews_resp.json()) == 2


def test_mark_published(client: TestClient, marketer1_headers: dict[str, str], sample_content: Content, db: Session):
    sample_content.status = "APPROVED"
    db.commit()

    resp = client.post(
        f"/api/v1/contents/{sample_content.id}/mark-published",
        headers=marketer1_headers,
        json={"published_url": "https://facebook.com/annamexample/posts/555"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "PUBLISHED"
    assert data["published_url"] == "https://facebook.com/annamexample/posts/555"
    assert data["published_at"] is not None


def test_delete_locked_content(client: TestClient, marketer1_headers: dict[str, str], sample_content: Content, db: Session):
    sample_content.status = "APPROVED"
    db.commit()

    resp = client.delete(f"/api/v1/contents/{sample_content.id}", headers=marketer1_headers)
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "CONTENT_LOCKED"


def test_check_banned_endpoint(client: TestClient, marketer1_headers: dict[str, str], db: Session):
    db.add(BannedKeyword(keyword="chữa khỏi", note="y tế"))
    db.commit()

    resp = client.post(
        "/api/v1/contents/check-banned",
        headers=marketer1_headers,
        json={"text": "Uống cà phê chữa khỏi mệt mỏi, thật là chữa khỏi hoàn toàn."},
    )
    assert resp.status_code == 200
    matches = resp.json()["matches"]
    assert len(matches) == 1
    assert matches[0]["keyword"] == "chữa khỏi"
    assert matches[0]["count"] == 2
