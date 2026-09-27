"""
Adversarial Empirical Stress-Testing Suite for Milestone M3:
Workflow Logic, State Machine & Database Notifications.

Target Verifications:
1. Rejection reason validation:
   - Length 0 ("", None, missing, whitespace) -> HTTP 422 or 400 rejection
   - Length 1 ("a", "!", " x ") -> HTTP 422 or 400 rejection
   - Length 2 ("ab", "NO", " xy ") -> HTTP 422 or 400 rejection
   - Length 3 ("abc", "Sai", "Bad") -> HTTP 200 acceptance, status -> REJECTED
2. State machine anti-tampering:
   - APPROVED content:
     * title edit -> status resets to AI_DRAFT, version_no increments
     * body edit -> status resets to AI_DRAFT, version_no increments
     * cta edit -> status resets to AI_DRAFT, version_no increments
     * image_url edit -> status resets to AI_DRAFT, version_no increments
   - PUBLISHED content:
     * title edit -> status resets to AI_DRAFT, version_no increments
     * body edit -> status resets to AI_DRAFT, version_no increments
     * cta edit -> status resets to AI_DRAFT, version_no increments
     * image_url edit -> status resets to AI_DRAFT, version_no increments
   - Direct status jumps to APPROVED or PUBLISHED via PUT -> HTTP 400
   - Direct creation as APPROVED or PUBLISHED via POST -> HTTP 400
   - Non-modifying update preserves APPROVED status
"""

import pytest
from pydantic import ValidationError
from app.models.entities import MarketingContent, Campaign, User, ContentReview
from app.schemas.schemas import ReviewCreate


# ==============================================================================
# SECTION 1: REJECTION REASON VALIDATION STRESS-TESTS
# ==============================================================================

class TestRejectionReasonValidation:
    """Stress-test rejection reason length boundary conditions across Schema and API."""

    def test_schema_reject_reason_length_0_rejected(self):
        """Length 0: Empty string and whitespace-only must raise ValidationError."""
        with pytest.raises(ValidationError):
            ReviewCreate(decision="REJECTED", reason="")

        with pytest.raises(ValidationError):
            ReviewCreate(decision="REJECTED", reason="   ")

    def test_schema_reject_reason_length_1_rejected(self):
        """Length 1: 1 character or 1 character padded with whitespace must raise ValidationError."""
        with pytest.raises(ValidationError):
            ReviewCreate(decision="REJECTED", reason="x")

        with pytest.raises(ValidationError):
            ReviewCreate(decision="REJECTED", reason="!")

        with pytest.raises(ValidationError):
            ReviewCreate(decision="REJECTED", reason="  a  ")

    def test_schema_reject_reason_length_2_rejected(self):
        """Length 2: 2 characters or 2 characters padded with whitespace must raise ValidationError."""
        with pytest.raises(ValidationError):
            ReviewCreate(decision="REJECTED", reason="ab")

        with pytest.raises(ValidationError):
            ReviewCreate(decision="REJECTED", reason="NO")

        with pytest.raises(ValidationError):
            ReviewCreate(decision="REJECTED", reason="  12  ")

    def test_schema_reject_reason_length_3_accepted(self):
        """Length 3: Exactly 3 characters or more must succeed."""
        r_abc = ReviewCreate(decision="REJECTED", reason="abc")
        assert r_abc.reason == "abc"

        r_sai = ReviewCreate(decision="REJECTED", reason="Sai")
        assert r_sai.reason == "Sai"

        r_padded = ReviewCreate(decision="REJECTED", reason="  xyz  ")
        assert r_padded.reason == "xyz"

        r_long = ReviewCreate(decision="REJECTED", reason="Nội dung cần điều chỉnh lại CTA và thông điệp thương hiệu")
        assert len(r_long.reason) > 3

    def test_api_reject_reason_length_0_boundary(self, client, db_session, manager_headers, workspace_alpha):
        """API: Submit reject requests with length 0 (empty string, None, missing, whitespace) -> HTTP 400/422."""
        mkt = db_session.query(User).filter(User.email.in_(["marketer@gmail.com"])).first()
        campaign = db_session.query(Campaign).filter(Campaign.workspace_id == workspace_alpha.id).first()

        content = MarketingContent(
            workspace_id=workspace_alpha.id,
            campaign_id=campaign.id,
            channel_id=1,
            created_by=mkt.id,
            title="Bài Test Độ Dài Lý Do 0",
            body="Thân bài kiểm tra reject reason length 0.",
            status="IN_REVIEW",
            version_no=1
        )
        db_session.add(content)
        db_session.commit()
        db_session.refresh(content)

        # 0a. Empty string ""
        res_empty = client.post(
            f"/api/v1/contents/{content.id}/reject",
            json={"decision": "REJECTED", "reason": ""},
            headers=manager_headers
        )
        assert res_empty.status_code in [400, 422], f"Expected 400 or 422 for empty string, got {res_empty.status_code}"

        # 0b. Whitespace only "   "
        res_ws = client.post(
            f"/api/v1/contents/{content.id}/reject",
            json={"decision": "REJECTED", "reason": "   "},
            headers=manager_headers
        )
        assert res_ws.status_code in [400, 422], f"Expected 400 or 422 for whitespace only, got {res_ws.status_code}"

        # 0c. Reason is None
        res_none = client.post(
            f"/api/v1/contents/{content.id}/reject",
            json={"decision": "REJECTED", "reason": None},
            headers=manager_headers
        )
        assert res_none.status_code in [400, 422], f"Expected 400 or 422 for None reason, got {res_none.status_code}"

        # 0d. Missing reason field entirely
        res_missing = client.post(
            f"/api/v1/contents/{content.id}/reject",
            json={"decision": "REJECTED"},
            headers=manager_headers
        )
        assert res_missing.status_code in [400, 422], f"Expected 400 or 422 for missing reason, got {res_missing.status_code}"

        # Verify content remained IN_REVIEW
        db_session.refresh(content)
        assert content.status == "IN_REVIEW"

    def test_api_reject_reason_length_1_boundary(self, client, db_session, manager_headers, workspace_alpha):
        """API: Submit reject requests with length 1 ("a", "!", " x ") -> HTTP 400/422."""
        mkt = db_session.query(User).filter(User.email.in_(["marketer@gmail.com"])).first()
        campaign = db_session.query(Campaign).filter(Campaign.workspace_id == workspace_alpha.id).first()

        content = MarketingContent(
            workspace_id=workspace_alpha.id,
            campaign_id=campaign.id,
            channel_id=1,
            created_by=mkt.id,
            title="Bài Test Độ Dài Lý Do 1",
            body="Thân bài kiểm tra reject reason length 1.",
            status="IN_REVIEW",
            version_no=1
        )
        db_session.add(content)
        db_session.commit()
        db_session.refresh(content)

        # 1a. Single char "a"
        res_a = client.post(
            f"/api/v1/contents/{content.id}/reject",
            json={"decision": "REJECTED", "reason": "a"},
            headers=manager_headers
        )
        assert res_a.status_code in [400, 422], f"Expected 400 or 422 for length 1, got {res_a.status_code}"

        # 1b. Single char "!"
        res_sym = client.post(
            f"/api/v1/contents/{content.id}/reject",
            json={"decision": "REJECTED", "reason": "!"},
            headers=manager_headers
        )
        assert res_sym.status_code in [400, 422], f"Expected 400 or 422 for length 1 symbol, got {res_sym.status_code}"

        # 1c. Single char with surrounding whitespace "  x  "
        res_ws = client.post(
            f"/api/v1/contents/{content.id}/reject",
            json={"decision": "REJECTED", "reason": "  x  "},
            headers=manager_headers
        )
        assert res_ws.status_code in [400, 422], f"Expected 400 or 422 for padded length 1, got {res_ws.status_code}"

        # Content must remain IN_REVIEW
        db_session.refresh(content)
        assert content.status == "IN_REVIEW"

    def test_api_reject_reason_length_2_boundary(self, client, db_session, manager_headers, workspace_alpha):
        """API: Submit reject requests with length 2 ("ab", "NO", "  xy  ") -> HTTP 400/422."""
        mkt = db_session.query(User).filter(User.email.in_(["marketer@gmail.com"])).first()
        campaign = db_session.query(Campaign).filter(Campaign.workspace_id == workspace_alpha.id).first()

        content = MarketingContent(
            workspace_id=workspace_alpha.id,
            campaign_id=campaign.id,
            channel_id=1,
            created_by=mkt.id,
            title="Bài Test Độ Dài Lý Do 2",
            body="Thân bài kiểm tra reject reason length 2.",
            status="IN_REVIEW",
            version_no=1
        )
        db_session.add(content)
        db_session.commit()
        db_session.refresh(content)

        # 2a. Two chars "ab"
        res_ab = client.post(
            f"/api/v1/contents/{content.id}/reject",
            json={"decision": "REJECTED", "reason": "ab"},
            headers=manager_headers
        )
        assert res_ab.status_code in [400, 422], f"Expected 400 or 422 for length 2, got {res_ab.status_code}"

        # 2b. Two chars "NO"
        res_no = client.post(
            f"/api/v1/contents/{content.id}/reject",
            json={"decision": "REJECTED", "reason": "NO"},
            headers=manager_headers
        )
        assert res_no.status_code in [400, 422], f"Expected 400 or 422 for 'NO', got {res_no.status_code}"

        # 2c. Two chars with padding "  12  "
        res_pad = client.post(
            f"/api/v1/contents/{content.id}/reject",
            json={"decision": "REJECTED", "reason": "  12  "},
            headers=manager_headers
        )
        assert res_pad.status_code in [400, 422], f"Expected 400 or 422 for padded length 2, got {res_pad.status_code}"

        # Content must remain IN_REVIEW
        db_session.refresh(content)
        assert content.status == "IN_REVIEW"

    def test_api_reject_reason_length_3_accepted(self, client, db_session, manager_headers, workspace_alpha):
        """API: Submit reject request with length 3 ("abc") -> Accepted HTTP 200, status -> REJECTED."""
        mkt = db_session.query(User).filter(User.email.in_(["marketer@gmail.com"])).first()
        campaign = db_session.query(Campaign).filter(Campaign.workspace_id == workspace_alpha.id).first()

        content = MarketingContent(
            workspace_id=workspace_alpha.id,
            campaign_id=campaign.id,
            channel_id=1,
            created_by=mkt.id,
            title="Bài Test Độ Dài Lý Do 3 (abc)",
            body="Thân bài kiểm tra reject reason length 3.",
            status="IN_REVIEW",
            version_no=1
        )
        db_session.add(content)
        db_session.commit()
        db_session.refresh(content)

        # Exactly 3 characters: "abc"
        res_abc = client.post(
            f"/api/v1/contents/{content.id}/reject",
            json={"decision": "REJECTED", "reason": "abc"},
            headers=manager_headers
        )
        assert res_abc.status_code == 200, f"Expected 200 for 'abc', got {res_abc.status_code}: {res_abc.text}"
        data = res_abc.json()
        assert data["status"] == "REJECTED"

        # Check database persistence and review record
        db_session.refresh(content)
        assert content.status == "REJECTED"

        review_rec = db_session.query(ContentReview).filter(ContentReview.content_id == content.id).first()
        assert review_rec is not None
        assert review_rec.decision == "REJECTED"
        assert review_rec.reason == "abc"


# ==============================================================================
# SECTION 2: STATE MACHINE ANTI-TAMPERING & VERSION INCREMENT STRESS-TESTS
# ==============================================================================

class TestStateMachineAntiTamperingApproved:
    """Stress-test anti-tampering on APPROVED content across title, body, cta, image_url."""

    def _create_approved_content(self, db_session, workspace_alpha):
        mkt = db_session.query(User).filter(User.email.in_(["marketer@gmail.com"])).first()
        campaign = db_session.query(Campaign).filter(Campaign.workspace_id == workspace_alpha.id).first()

        content = MarketingContent(
            workspace_id=workspace_alpha.id,
            campaign_id=campaign.id,
            channel_id=1,
            created_by=mkt.id,
            title="Tiêu Đề Đã Được Duyệt Ban Đầu",
            body="Nội dung thân bài đã được duyệt ban đầu.",
            cta="Mua Ngay",
            image_url="https://example.com/original-banner.png",
            status="APPROVED",
            version_no=1
        )
        db_session.add(content)
        db_session.commit()
        db_session.refresh(content)
        return content

    def test_approved_edit_title_resets_to_ai_draft_and_increments_version(self, client, db_session, marketer_headers, workspace_alpha):
        """APPROVED content: editing title resets status to AI_DRAFT and version_no becomes 2."""
        content = self._create_approved_content(db_session, workspace_alpha)
        assert content.status == "APPROVED"
        assert content.version_no == 1

        res = client.put(
            f"/api/v1/contents/{content.id}",
            json={"title": "Tiêu Đề Đã Bị Thay Đổi Trái Phép"},
            headers=marketer_headers
        )
        assert res.status_code == 200, f"Update failed: {res.text}"
        data = res.json()
        assert data["status"] == "AI_DRAFT", f"Expected AI_DRAFT, got {data['status']}"
        assert data["version_no"] == 2, f"Expected version_no 2, got {data['version_no']}"

        db_session.refresh(content)
        assert content.status == "AI_DRAFT"
        assert content.version_no == 2
        assert content.title == "Tiêu Đề Đã Bị Thay Đổi Trái Phép"

    def test_approved_edit_body_resets_to_ai_draft_and_increments_version(self, client, db_session, marketer_headers, workspace_alpha):
        """APPROVED content: editing body resets status to AI_DRAFT and version_no becomes 2."""
        content = self._create_approved_content(db_session, workspace_alpha)

        res = client.put(
            f"/api/v1/contents/{content.id}",
            json={"body": "Thân bài hoàn toàn mới sau khi đã được sếp duyệt!"},
            headers=marketer_headers
        )
        assert res.status_code == 200, f"Update failed: {res.text}"
        data = res.json()
        assert data["status"] == "AI_DRAFT"
        assert data["version_no"] == 2

        db_session.refresh(content)
        assert content.status == "AI_DRAFT"
        assert content.version_no == 2
        assert content.body == "Thân bài hoàn toàn mới sau khi đã được sếp duyệt!"

    def test_approved_edit_cta_resets_to_ai_draft_and_increments_version(self, client, db_session, marketer_headers, workspace_alpha):
        """APPROVED content: editing cta resets status to AI_DRAFT and version_no becomes 2."""
        content = self._create_approved_content(db_session, workspace_alpha)

        res = client.put(
            f"/api/v1/contents/{content.id}",
            json={"cta": "Đăng Ký Ngay Nhận Quà Khủng"},
            headers=marketer_headers
        )
        assert res.status_code == 200, f"Update failed: {res.text}"
        data = res.json()
        assert data["status"] == "AI_DRAFT"
        assert data["version_no"] == 2

        db_session.refresh(content)
        assert content.status == "AI_DRAFT"
        assert content.version_no == 2
        assert content.cta == "Đăng Ký Ngay Nhận Quà Khủng"

    def test_approved_edit_image_url_resets_to_ai_draft_and_increments_version(self, client, db_session, marketer_headers, workspace_alpha):
        """APPROVED content: editing image_url resets status to AI_DRAFT and version_no becomes 2."""
        content = self._create_approved_content(db_session, workspace_alpha)

        # 1. Update to new image URL
        res = client.put(
            f"/api/v1/contents/{content.id}",
            json={"image_url": "https://example.com/unapproved-new-banner.jpg"},
            headers=marketer_headers
        )
        assert res.status_code == 200, f"Update failed: {res.text}"
        data = res.json()
        assert data["status"] == "AI_DRAFT"
        assert data["version_no"] == 2

        db_session.refresh(content)
        assert content.status == "AI_DRAFT"
        assert content.version_no == 2
        assert content.image_url == "https://example.com/unapproved-new-banner.jpg"

    def test_approved_no_content_change_preserves_approved_status(self, client, db_session, marketer_headers, workspace_alpha):
        """APPROVED content: update without changing title, body, cta, image_url preserves APPROVED status."""
        content = self._create_approved_content(db_session, workspace_alpha)

        # Send same title and body
        res = client.put(
            f"/api/v1/contents/{content.id}",
            json={
                "title": content.title,
                "body": content.body,
                "cta": content.cta,
                "image_url": content.image_url
            },
            headers=marketer_headers
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "APPROVED"
        assert data["version_no"] == 2  # version increments on any PUT


class TestStateMachineAntiTamperingPublished:
    """Stress-test anti-tampering on PUBLISHED content across title, body, cta, image_url."""

    def _create_published_content(self, db_session, workspace_alpha):
        mkt = db_session.query(User).filter(User.email.in_(["marketer@gmail.com"])).first()
        campaign = db_session.query(Campaign).filter(Campaign.workspace_id == workspace_alpha.id).first()

        content = MarketingContent(
            workspace_id=workspace_alpha.id,
            campaign_id=campaign.id,
            channel_id=1,
            created_by=mkt.id,
            title="Bài Viết Đang Lên Sóng Mạng Xã Hội",
            body="Nội dung truyền thông đã được xuất bản chính thức.",
            cta="Xem Chi Tiết",
            image_url="https://example.com/published-banner.png",
            status="PUBLISHED",
            version_no=1
        )
        db_session.add(content)
        db_session.commit()
        db_session.refresh(content)
        return content

    def test_published_edit_title_resets_to_ai_draft_and_increments_version(self, client, db_session, marketer_headers, workspace_alpha):
        """PUBLISHED content: editing title resets status to AI_DRAFT and version_no becomes 2."""
        content = self._create_published_content(db_session, workspace_alpha)

        res = client.put(
            f"/api/v1/contents/{content.id}",
            json={"title": "Sửa Tiêu Đề Bài Đang Publish"},
            headers=marketer_headers
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "AI_DRAFT"
        assert data["version_no"] == 2

        db_session.refresh(content)
        assert content.status == "AI_DRAFT"
        assert content.version_no == 2
        assert content.title == "Sửa Tiêu Đề Bài Đang Publish"

    def test_published_edit_body_resets_to_ai_draft_and_increments_version(self, client, db_session, marketer_headers, workspace_alpha):
        """PUBLISHED content: editing body resets status to AI_DRAFT and version_no becomes 2."""
        content = self._create_published_content(db_session, workspace_alpha)

        res = client.put(
            f"/api/v1/contents/{content.id}",
            json={"body": "Sửa thân bài của bài viết đã xuất bản!"},
            headers=marketer_headers
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "AI_DRAFT"
        assert data["version_no"] == 2

        db_session.refresh(content)
        assert content.status == "AI_DRAFT"
        assert content.version_no == 2

    def test_published_edit_cta_resets_to_ai_draft_and_increments_version(self, client, db_session, marketer_headers, workspace_alpha):
        """PUBLISHED content: editing cta resets status to AI_DRAFT and version_no becomes 2."""
        content = self._create_published_content(db_session, workspace_alpha)

        res = client.put(
            f"/api/v1/contents/{content.id}",
            json={"cta": "Gọi Hotline 1900xxxx"},
            headers=marketer_headers
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "AI_DRAFT"
        assert data["version_no"] == 2

        db_session.refresh(content)
        assert content.status == "AI_DRAFT"
        assert content.version_no == 2

    def test_published_edit_image_url_resets_to_ai_draft_and_increments_version(self, client, db_session, marketer_headers, workspace_alpha):
        """PUBLISHED content: editing image_url resets status to AI_DRAFT and version_no becomes 2."""
        content = self._create_published_content(db_session, workspace_alpha)

        res = client.put(
            f"/api/v1/contents/{content.id}",
            json={"image_url": "https://example.com/new-published-banner.png"},
            headers=marketer_headers
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "AI_DRAFT"
        assert data["version_no"] == 2

        db_session.refresh(content)
        assert content.status == "AI_DRAFT"
        assert content.version_no == 2

    def test_multi_cycle_tampering_version_progression(self, client, db_session, manager_headers, marketer_headers, workspace_alpha):
        """Lifecycle multi-cycle test:
        DRAFT (v1) -> Submit -> Approve (v1, APPROVED) ->
        Tamper Title -> AI_DRAFT (v2) -> Submit -> Approve (v2, APPROVED) ->
        Tamper Body -> AI_DRAFT (v3) -> Submit -> Approve (v3, APPROVED) ->
        Publish (v3, PUBLISHED) ->
        Tamper CTA -> AI_DRAFT (v4)
        """
        campaign = db_session.query(Campaign).filter(Campaign.workspace_id == workspace_alpha.id).first()

        # 1. Create clean DRAFT
        res_create = client.post(
            "/api/v1/contents",
            json={
                "campaign_id": campaign.id,
                "channel_id": 1,
                "title": "Vòng đời đa phiên bản",
                "body": "Nội dung chuẩn kiểm thử chu trình chống gian lận.",
                "cta": "Bấm vào đây",
                "status": "DRAFT"
            },
            headers=marketer_headers
        )
        assert res_create.status_code == 201
        content_id = res_create.json()["id"]
        assert res_create.json()["version_no"] == 1

        # Submit -> IN_REVIEW
        r_sub1 = client.post(f"/api/v1/contents/{content_id}/submit", headers=marketer_headers)
        assert r_sub1.status_code == 200
        assert r_sub1.json()["status"] == "IN_REVIEW"

        # Approve -> APPROVED
        r_appr1 = client.post(f"/api/v1/contents/{content_id}/approve", headers=manager_headers)
        assert r_appr1.status_code == 200
        assert r_appr1.json()["status"] == "APPROVED"
        assert r_appr1.json()["version_no"] == 1

        # Cycle 1 Tamper: Edit Title -> resets to AI_DRAFT, v2
        r_tamper1 = client.put(
            f"/api/v1/contents/{content_id}",
            json={"title": "Vòng đời phiên bản 2"},
            headers=marketer_headers
        )
        assert r_tamper1.status_code == 200
        assert r_tamper1.json()["status"] == "AI_DRAFT"
        assert r_tamper1.json()["version_no"] == 2

        # Re-submit -> IN_REVIEW
        r_sub2 = client.post(f"/api/v1/contents/{content_id}/submit", headers=marketer_headers)
        assert r_sub2.status_code == 200
        assert r_sub2.json()["status"] == "IN_REVIEW"

        # Re-approve -> APPROVED
        r_appr2 = client.post(f"/api/v1/contents/{content_id}/approve", headers=manager_headers)
        assert r_appr2.status_code == 200
        assert r_appr2.json()["status"] == "APPROVED"
        assert r_appr2.json()["version_no"] == 2

        # Cycle 2 Tamper: Edit Body -> resets to AI_DRAFT, v3
        r_tamper2 = client.put(
            f"/api/v1/contents/{content_id}",
            json={"body": "Nội dung thân bài đã đổi sang phiên bản 3."},
            headers=marketer_headers
        )
        assert r_tamper2.status_code == 200
        assert r_tamper2.json()["status"] == "AI_DRAFT"
        assert r_tamper2.json()["version_no"] == 3

        # Re-submit -> IN_REVIEW
        r_sub3 = client.post(f"/api/v1/contents/{content_id}/submit", headers=marketer_headers)
        assert r_sub3.status_code == 200

        # Re-approve -> APPROVED
        r_appr3 = client.post(f"/api/v1/contents/{content_id}/approve", headers=manager_headers)
        assert r_appr3.status_code == 200
        assert r_appr3.json()["status"] == "APPROVED"
        assert r_appr3.json()["version_no"] == 3

        # Publish -> PUBLISHED
        r_pub = client.post(f"/api/v1/contents/{content_id}/publish", headers=manager_headers)
        assert r_pub.status_code == 200
        assert r_pub.json()["status"] == "PUBLISHED"
        assert r_pub.json()["version_no"] == 3

        # Cycle 3 Tamper: Edit CTA on PUBLISHED -> resets to AI_DRAFT, v4
        r_tamper3 = client.put(
            f"/api/v1/contents/{content_id}",
            json={"cta": "CTA Mới Phiên Bản 4"},
            headers=marketer_headers
        )
        assert r_tamper3.status_code == 200
        assert r_tamper3.json()["status"] == "AI_DRAFT"
        assert r_tamper3.json()["version_no"] == 4
