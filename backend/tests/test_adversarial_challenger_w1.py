"""
Adversarial Probe & Empirical Verification Suite - Challenger W1_1
==================================================================
Author: Challenger W1_1 (Empirical Challenger Agent)
Purpose: Stress-test assumptions and probe potential bypasses in Wave 1 P0:
  1. Privilege Escalation Bypasses (case variations, whitespace, null byte, array payloads, mass assignment)
  2. Multi-Tenant Cross-Workspace ID Tampering & BOLA/IDOR (Beta -> Alpha reverse isolation, foreign campaign attachment)
  3. HTTP Parameter Pollution (duplicate query parameters, conflicting IDs)
  4. Review Queue State Machine Bypasses (case variations, whitespace, illegal state jumps)
  5. BYOK Vault Cryptographic Stress & Tamper Resistance
"""

import os
import json
import pytest
from typing import Dict, Any
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password, create_access_token
from app.core.crypto import (
    encrypt_api_key, decrypt_api_key, mask_api_key,
    get_jwt_secret_key, get_byok_encryption_key
)
from app.models.entities import (
    User, Workspace, WorkspaceMember, BrandKit,
    Campaign, CampaignMember, MarketingContent, ContentReview,
    CampaignMetric, CustomApiKey
)


# ==============================================================================
# SUITE 1: ADVERSARIAL PRIVILEGE ESCALATION PROBES
# ==============================================================================
class TestAdversarialPrivilegeEscalation:
    """Stress-test role validation, injection, and privilege escalation during registration."""

    @pytest.mark.parametrize("payload_role, expected_status", [
        # Case variations of privileged roles
        ("agency_manager", [400, 403, 422]),
        ("Agency_Manager", [400, 403, 422]),
        ("AGENCY_manager", [400, 403, 422]),
        ("admin", [400, 403, 422]),
        ("Admin", [400, 403, 422]),
        ("manager", [400, 403, 422]),
        ("Manager", [400, 403, 422]),
        ("client_approver", [400, 403, 422]),
        ("Client_Approver", [400, 403, 422]),
        # Whitespace / newline variations
        (" AGENCY_MANAGER", [400, 403, 422]),
        ("AGENCY_MANAGER ", [400, 403, 422]),
        (" AGENCY_MANAGER ", [400, 403, 422]),
        ("ADMIN\n", [400, 403, 422]),
        ("ADMIN\t", [400, 403, 422]),
        ("ADMIN\r\n", [400, 403, 422]),
        # Null byte injection
        ("ADMIN\x00", [400, 403, 422]),
        ("AGENCY_MANAGER\x00extra", [400, 403, 422]),
        # Empty string
        ("", [400, 403, 422]),
        ("   ", [400, 403, 422]),
        # SQL Injection
        ("MARKETER' OR '1'='1", [400, 403, 422]),
        ("'; DROP TABLE users; --", [400, 403, 422]),
        # Unknown roles
        ("SUPERADMIN", [400, 403, 422]),
        ("ROOT", [400, 403, 422]),
    ])
    def test_adv_01_role_injection_variants_rejected(
        self, client: TestClient, payload_role: str, expected_status: list
    ):
        """Verify that case variations, whitespaces, null bytes, and malicious roles fail."""
        resp = client.post("/api/v1/auth/register", json={
            "email": f"probe_role_{hash(payload_role)}@attacker.vn",
            "password": "SecurePassword@123",
            "full_name": "Role Probe",
            "role": payload_role
        })
        assert resp.status_code in expected_status, (
            f"Adversarial role payload '{repr(payload_role)}' bypassed validation! Got {resp.status_code}: {resp.text}"
        )

    @pytest.mark.parametrize("non_string_role", [
        ["AGENCY_MANAGER"],
        {"role": "ADMIN"},
        True,
        1,
        0,
        ["ADMIN", "MARKETER"],
    ])
    def test_adv_02_non_string_role_payloads_rejected(
        self, client: TestClient, non_string_role: Any
    ):
        """Verify that non-string role payloads (arrays, dicts, booleans, ints) are rejected by schema."""
        resp = client.post("/api/v1/auth/register", json={
            "email": f"probe_nonstr_{hash(str(non_string_role))}@attacker.vn",
            "password": "SecurePassword@123",
            "full_name": "NonStr Probe",
            "role": non_string_role
        })
        assert resp.status_code in (400, 422), (
            f"Non-string role payload {repr(non_string_role)} did not trigger 422/400! Got {resp.status_code}"
        )

    def test_adv_03_mass_assignment_extra_fields_ignored_or_rejected(
        self, client: TestClient, db_session: Session
    ):
        """Verify that mass-assignment attempts (injecting is_admin, status=ADMIN, id=1) do not grant privilege."""
        target_email = "probe_mass_assign@attacker.vn"
        resp = client.post("/api/v1/auth/register", json={
            "email": target_email,
            "password": "SecurePassword@123",
            "full_name": "Mass Assignment Probe",
            "role": "MARKETER",
            # Malicious injected parameters
            "is_admin": True,
            "is_superuser": True,
            "status": "SUPERUSER",
            "id": 1,
            "workspace_id": 1
        })
        assert resp.status_code == 201, f"Registration failed unexpectedly: {resp.text}"
        
        user = db_session.query(User).filter(User.email == target_email).first()
        assert user is not None
        assert user.role == "MARKETER", f"User role was elevated via mass assignment: {user.role}"
        assert user.status == "ACTIVE"
        assert user.id != 1, "User overwrote primary key id=1!"


# ==============================================================================
# SUITE 2: BIDIRECTIONAL & DEEP CROSS-WORKSPACE ID TAMPERING PROBES
# ==============================================================================
class TestAdversarialCrossWorkspaceTampering:
    """Probes cross-workspace isolation bidirectionally: Beta -> Alpha and Alpha -> Beta."""

    def test_adv_04_beta_agency_manager_cannot_read_or_edit_alpha_campaign(
        self, client: TestClient, beta_agency_manager_headers, workspace_alpha, db_session: Session
    ):
        """EMPIRICAL PROBE: Can Agency Manager of Workspace Beta view, edit, or delete Alpha's campaign?"""
        alpha_campaign = db_session.query(Campaign).filter(Campaign.workspace_id == workspace_alpha.id).first()
        assert alpha_campaign is not None, "Workspace Alpha must have at least one campaign"

        # 1. Probe GET /campaigns/{alpha_campaign.id} from Beta Agency Manager
        resp_get = client.get(f"/api/v1/campaigns/{alpha_campaign.id}", headers=beta_agency_manager_headers)
        # Note: If this returns 200 instead of 403, it reveals that Alpha campaigns (ws_id=1) lack reverse isolation!
        is_get_forbidden = (resp_get.status_code == 403)

        # 2. Probe PUT /campaigns/{alpha_campaign.id} from Beta Agency Manager
        resp_put = client.put(
            f"/api/v1/campaigns/{alpha_campaign.id}",
            json={"name": "Compromised by Beta Agency Manager"},
            headers=beta_agency_manager_headers
        )
        is_put_forbidden = (resp_put.status_code == 403)

        # 3. Probe DELETE /campaigns/{alpha_campaign.id} from Beta Agency Manager
        resp_del = client.delete(
            f"/api/v1/campaigns/{alpha_campaign.id}",
            headers=beta_agency_manager_headers
        )
        is_del_forbidden = (resp_del.status_code == 403)

        print(f"\n[EMPIRICAL RESULT] Beta Agency Mgr -> Alpha Campaign: GET={resp_get.status_code}, PUT={resp_put.status_code}, DELETE={resp_del.status_code}")
        
        # We assert that cross-workspace access must be strictly forbidden
        assert is_get_forbidden, (
            f"VULNERABILITY DETECTED: Beta Agency Manager accessed Alpha Campaign {alpha_campaign.id}! Status: {resp_get.status_code}"
        )
        assert is_put_forbidden, (
            f"VULNERABILITY DETECTED: Beta Agency Manager updated Alpha Campaign {alpha_campaign.id}! Status: {resp_put.status_code}"
        )
        assert is_del_forbidden, (
            f"VULNERABILITY DETECTED: Beta Agency Manager deleted Alpha Campaign {alpha_campaign.id}! Status: {resp_del.status_code}"
        )

    def test_adv_05_beta_agency_manager_cannot_read_or_edit_alpha_content(
        self, client: TestClient, beta_agency_manager_headers, workspace_alpha, db_session: Session
    ):
        """EMPIRICAL PROBE: Can Agency Manager of Workspace Beta view or edit Alpha's content?"""
        alpha_content = db_session.query(MarketingContent).filter(MarketingContent.workspace_id == workspace_alpha.id).first()
        assert alpha_content is not None, "Workspace Alpha must have at least one content"

        # 1. Probe GET /contents/{alpha_content.id}
        resp_get = client.get(f"/api/v1/contents/{alpha_content.id}", headers=beta_agency_manager_headers)
        is_get_forbidden = (resp_get.status_code == 403)

        # 2. Probe PUT /contents/{alpha_content.id}
        resp_put = client.put(
            f"/api/v1/contents/{alpha_content.id}",
            json={"title": "Hacked Title by Beta Mgr"},
            headers=beta_agency_manager_headers
        )
        is_put_forbidden = (resp_put.status_code == 403)

        print(f"\n[EMPIRICAL RESULT] Beta Agency Mgr -> Alpha Content: GET={resp_get.status_code}, PUT={resp_put.status_code}")

        assert is_get_forbidden, (
            f"VULNERABILITY DETECTED: Beta Agency Manager accessed Alpha Content {alpha_content.id}! Status: {resp_get.status_code}"
        )
        assert is_put_forbidden, (
            f"VULNERABILITY DETECTED: Beta Agency Manager updated Alpha Content {alpha_content.id}! Status: {resp_put.status_code}"
        )

    def test_adv_06_beta_marketer_cannot_read_alpha_campaign_or_content(
        self, client: TestClient, beta_marketer_headers, workspace_alpha, db_session: Session
    ):
        """Verify that Marketer of Workspace Beta cannot access Alpha's campaign or content."""
        alpha_campaign = db_session.query(Campaign).filter(Campaign.workspace_id == workspace_alpha.id).first()
        alpha_content = db_session.query(MarketingContent).filter(MarketingContent.workspace_id == workspace_alpha.id).first()

        resp_cmp = client.get(f"/api/v1/campaigns/{alpha_campaign.id}", headers=beta_marketer_headers)
        assert resp_cmp.status_code == 403, f"Beta Marketer accessed Alpha Campaign: {resp_cmp.status_code}"

        resp_cnt = client.get(f"/api/v1/contents/{alpha_content.id}", headers=beta_marketer_headers)
        assert resp_cnt.status_code == 403, f"Beta Marketer accessed Alpha Content: {resp_cnt.status_code}"

    def test_adv_07_cross_workspace_content_injection_into_foreign_campaign(
        self, client: TestClient, beta_marketer_headers, marketer_headers, workspace_alpha, workspace_beta, db_session: Session
    ):
        """EMPIRICAL PROBE: Can a Marketer create content attached to another workspace's campaign?"""
        alpha_campaign = db_session.query(Campaign).filter(Campaign.workspace_id == workspace_alpha.id).first()
        beta_campaign = db_session.query(Campaign).filter(Campaign.workspace_id == workspace_beta.id).first()
        assert alpha_campaign is not None and beta_campaign is not None

        # Attack 1: Beta Marketer tries to create content inside Alpha's campaign
        resp_attack1 = client.post("/api/v1/contents", json={
            "campaign_id": alpha_campaign.id,
            "channel_id": 1,
            "title": "Cross-Workspace Injection 1",
            "body": "Body",
            "cta": "CTA"
        }, headers=beta_marketer_headers)
        assert resp_attack1.status_code == 403, (
            f"VULNERABILITY: Beta Marketer created content inside Alpha Campaign! Status: {resp_attack1.status_code}"
        )

        # Attack 2: Alpha Marketer tries to create content inside Beta's campaign
        resp_attack2 = client.post("/api/v1/contents", json={
            "campaign_id": beta_campaign.id,
            "channel_id": 1,
            "title": "Cross-Workspace Injection 2",
            "body": "Body",
            "cta": "CTA"
        }, headers=marketer_headers)
        assert resp_attack2.status_code == 403, (
            f"VULNERABILITY: Alpha Marketer created content inside Beta Campaign! Status: {resp_attack2.status_code}"
        )

    def test_adv_08_beta_agency_manager_cannot_tamper_alpha_byok_key(
        self, client: TestClient, beta_agency_manager_headers, workspace_alpha
    ):
        """EMPIRICAL PROBE: Can Beta Agency Manager read or set Workspace Alpha's BYOK key?"""
        # 1. GET /settings/ai-keys?workspace_id=1
        resp_get = client.get(f"/api/v1/settings/ai-keys?workspace_id={workspace_alpha.id}", headers=beta_agency_manager_headers)
        # 2. POST /settings/ai-keys with workspace_id=1
        resp_post = client.post("/api/v1/settings/ai-keys", json={
            "api_key": "AIzaSyBetaAttackerKey1234567890123456",
            "provider": "gemini",
            "workspace_id": workspace_alpha.id
        }, headers=beta_agency_manager_headers)

        print(f"\n[EMPIRICAL RESULT] Beta Agency Mgr -> Alpha BYOK: GET={resp_get.status_code}, POST={resp_post.status_code}")

        assert resp_get.status_code == 403, (
            f"VULNERABILITY DETECTED: Beta Agency Manager read Alpha BYOK key! Status: {resp_get.status_code}"
        )
        assert resp_post.status_code == 403, (
            f"VULNERABILITY DETECTED: Beta Agency Manager configured Alpha BYOK key! Status: {resp_post.status_code}"
        )

    def test_adv_19_beta_agency_manager_cannot_list_alpha_campaigns_or_contents(
        self, client: TestClient, beta_agency_manager_headers, workspace_alpha
    ):
        """EMPIRICAL PROBE: Can Beta Agency Manager query campaigns and contents of Workspace Alpha via query param?"""
        resp_cmp = client.get(f"/api/v1/campaigns?workspace_id={workspace_alpha.id}", headers=beta_agency_manager_headers)
        resp_cnt = client.get(f"/api/v1/contents?workspace_id={workspace_alpha.id}", headers=beta_agency_manager_headers)

        print(f"\n[EMPIRICAL RESULT] Beta Agency Mgr List Alpha: Campaigns={resp_cmp.status_code} ({len(resp_cmp.json())} items), Contents={resp_cnt.status_code} ({len(resp_cnt.json())} items)")

        assert resp_cmp.status_code == 403, (
            f"VULNERABILITY DETECTED: Beta Agency Manager listed Alpha Campaigns! Status: {resp_cmp.status_code}"
        )
        assert resp_cnt.status_code == 403, (
            f"VULNERABILITY DETECTED: Beta Agency Manager listed Alpha Contents! Status: {resp_cnt.status_code}"
        )



# ==============================================================================
# SUITE 3: HTTP PARAMETER POLLUTION (HPP) & QUERY INJECTION
# ==============================================================================
class TestAdversarialParameterPollution:
    """Stress-test query parameter handling against HTTP Parameter Pollution (HPP)."""

    def test_adv_09_duplicate_workspace_id_in_campaigns_query(
        self, client: TestClient, manager_headers, workspace_alpha, workspace_beta
    ):
        """Verify behavior when multiple workspace_id parameters are provided: ?workspace_id=1&workspace_id=2"""
        resp = client.get(
            f"/api/v1/campaigns?workspace_id={workspace_alpha.id}&workspace_id={workspace_beta.id}",
            headers=manager_headers
        )
        # Should not produce HTTP 500 Unhandled Exception
        assert resp.status_code in (200, 400, 422, 403), f"Server crashed with {resp.status_code}: {resp.text}"
        if resp.status_code == 200:
            campaigns = resp.json()
            # If manager of Alpha called it, it must NOT return campaigns belonging to Workspace Beta
            for c in campaigns:
                assert c["workspace_id"] != workspace_beta.id, (
                    f"HPP LEAK: Parameter pollution allowed Alpha Manager to receive Beta Campaign: {c}"
                )

    def test_adv_10_duplicate_workspace_id_in_brand_kit_query(
        self, client: TestClient, manager_headers, workspace_alpha, workspace_beta
    ):
        """Verify that duplicate workspace_id in /brand-kit does not leak Beta BrandKit to Alpha Manager."""
        resp = client.get(
            f"/api/v1/brand-kit?workspace_id={workspace_alpha.id}&workspace_id={workspace_beta.id}",
            headers=manager_headers
        )
        assert resp.status_code in (200, 400, 422, 403)
        if resp.status_code == 200:
            data = resp.json()
            assert data["workspace_id"] != workspace_beta.id, "HPP LEAK: Received Workspace Beta BrandKit!"

    def test_adv_11_negative_and_out_of_bounds_workspace_ids(
        self, client: TestClient, manager_headers
    ):
        """Verify negative, zero, and huge IDs do not crash the application."""
        for test_id in [-1, 0, 999999999]:
            resp = client.get(f"/api/v1/campaigns?workspace_id={test_id}", headers=manager_headers)
            assert resp.status_code in (200, 403, 404, 422), f"Failed for workspace_id={test_id}: {resp.status_code}"


# ==============================================================================
# SUITE 4: REVIEW STATE MACHINE ADVERSARIAL INTEGRITY
# ==============================================================================
class TestAdversarialStateMachine:
    """Stress-test state transitions and edge cases in the review queue."""

    @pytest.mark.parametrize("disallowed_status", [
        "approved",
        "Approved",
        " APPROVED ",
        "published",
        "Published",
        " PUBLISHED ",
        "IN_REVIEW",
    ])
    def test_adv_12_disallowed_creation_statuses(
        self, client: TestClient, marketer_headers, disallowed_status: str
    ):
        """Creation with status variants of approved/published or uppercase/lowercase should be rejected or normalized."""
        resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Adversarial Status Content",
            "body": "Body text",
            "cta": "Click here",
            "status": disallowed_status
        }, headers=marketer_headers)
        # If it succeeds, it must NOT be saved as APPROVED or PUBLISHED
        if resp.status_code == 201:
            saved_status = resp.json().get("status")
            assert saved_status not in ("APPROVED", "PUBLISHED"), (
                f"Content was created with status {saved_status} using '{disallowed_status}'!"
            )
        else:
            assert resp.status_code in (400, 422)

    def test_adv_13_cannot_approve_draft_directly_without_submission(
        self, client: TestClient, manager_headers, db_session: Session
    ):
        """Content in DRAFT cannot be directly approved via /approve without being IN_REVIEW."""
        draft = MarketingContent(
            workspace_id=1,
            campaign_id=1,
            channel_id=1,
            created_by=2,
            title="Adversarial Direct Approve Test",
            body="Body text",
            cta="CTA",
            status="DRAFT",
            version_no=1
        )
        db_session.add(draft)
        db_session.commit()
        db_session.refresh(draft)

        resp = client.post(f"/api/v1/contents/{draft.id}/approve", headers=manager_headers)
        assert resp.status_code == 400, f"Expected 400 Bad Request, got {resp.status_code}: {resp.text}"

    def test_adv_14_cannot_approve_rejected_content_without_resubmission(
        self, client: TestClient, manager_headers, db_session: Session
    ):
        """Content in REJECTED cannot be approved via /approve without first being re-submitted to IN_REVIEW."""
        rejected = MarketingContent(
            workspace_id=1,
            campaign_id=1,
            channel_id=1,
            created_by=2,
            title="Adversarial Rejected Content",
            body="Body text",
            cta="CTA",
            status="REJECTED",
            version_no=1
        )
        db_session.add(rejected)
        db_session.commit()
        db_session.refresh(rejected)

        resp = client.post(f"/api/v1/contents/{rejected.id}/approve", headers=manager_headers)
        assert resp.status_code == 400, f"Expected 400 Bad Request, got {resp.status_code}: {resp.text}"

    @pytest.mark.parametrize("invalid_reason", [
        "",
        "   ",
        "a",
        "ab",
        "\t\n",
    ])
    def test_adv_15_rejection_reason_whitespace_and_length_validation(
        self, client: TestClient, manager_headers, db_session: Session, invalid_reason: str
    ):
        """Rejection reasons must be at least 3 non-whitespace characters."""
        content = MarketingContent(
            workspace_id=1,
            campaign_id=1,
            channel_id=1,
            created_by=2,
            title="Content for Reject Validation",
            body="Body",
            cta="CTA",
            status="IN_REVIEW",
            version_no=1
        )
        db_session.add(content)
        db_session.commit()
        db_session.refresh(content)

        resp = client.post(
            f"/api/v1/contents/{content.id}/reject",
            json={"decision": "REJECTED", "reason": invalid_reason},
            headers=manager_headers
        )
        assert resp.status_code in (400, 422), (
            f"Invalid rejection reason {repr(invalid_reason)} was accepted! Got {resp.status_code}"
        )


# ==============================================================================
# SUITE 5: BYOK CRYPTOGRAPHIC VAULT STRESS TESTS
# ==============================================================================
class TestAdversarialCryptoVault:
    """Stress-test encryption/decryption error handling and tamper resistance."""

    def test_adv_16_corrupted_ciphertext_raises_value_error(self):
        """A valid Fernet token with a corrupted MAC or modified byte raises ValueError, not unhandled crash."""
        plaintext = "AIzaSyValidGeminiKeyForTamperTest123456"
        ciphertext = encrypt_api_key(plaintext)
        
        # Corrupt one character in the middle
        corrupted = ciphertext[:20] + ("A" if ciphertext[20] != "A" else "B") + ciphertext[21:]
        
        with pytest.raises(ValueError, match="Tampered or invalid key|Decryption failed|corrupted"):
            decrypt_api_key(corrupted)

    def test_adv_17_truncated_ciphertext_raises_value_error(self):
        """Truncated token (<50 chars) raises ValueError."""
        with pytest.raises(ValueError):
            decrypt_api_key("gAAAAAB")

    def test_adv_18_non_base64_ciphertext_raises_value_error(self):
        """Non-base64 characters raise ValueError."""
        with pytest.raises(ValueError):
            decrypt_api_key("!@#$%^&*()_+=NOT_BASE64_CIPHERTEXT!!!")
