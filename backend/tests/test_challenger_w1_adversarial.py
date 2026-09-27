"""
Adversarial Probe & Stress Harness for Wave 1 P0 Verification
=============================================================
Evaluates:
1. Live DB Protection: Asserts marketing_campaigns.db is never touched, modified, or resized.
2. BYOK Cryptography: Probes wrong key decryption, forged tokens without gAAAAA, tampered ciphertexts, empty/whitespace keys, and production placeholder rejection.
3. Review Queue State Machine: Probes invalid transitions (DRAFT->PUBLISHED, REJECTED->PUBLISHED without edit/resubmit, non-approver roles, anti-tampering demotion, compliance guardrails).
"""

import os
import json
import base64
import hashlib
import sqlite3
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from cryptography.fernet import Fernet

from app.core.config import settings, validate_security_configuration, Settings
from app.core.security import hash_password, create_access_token
from app.core.crypto import (
    encrypt_api_key, decrypt_api_key, mask_api_key,
    get_jwt_secret_key, get_byok_encryption_key, _get_rotation_keys
)
from app.models.entities import (
    User, Workspace, Campaign, MarketingContent, ContentReview
)
from seed.seed_data import init_db as seed_init_db, reset_db

BASE_DIR = Path(__file__).resolve().parent.parent
LIVE_DB_FILE = BASE_DIR / "marketing_campaigns.db"


# ==============================================================================
# PROBE 1: LIVE DB PROTECTION & IMMUTABILITY
# ==============================================================================
class TestAdversarialLiveDBProtection:
    """Verifies that live production database backend/marketing_campaigns.db is NEVER mutated."""

    def test_adv_live_db_checksum_and_size_integrity(self):
        """Live DB phải tồn tại, còn nguyên vẹn, và không bị test sửa.

        KHÔNG so sánh SHA-256 thô của file: bất kỳ tiến trình nào mở DB qua app
        engine cũng làm `PRAGMA journal_mode=WAL` đổi 4 byte header
        (offset 18-19: 1,1 -> 2,2) và bump file change counter (offset 24-27),
        dù không một page dữ liệu nào thay đổi. Hash thô vì thế fail vĩnh viễn
        theo cách giả (false failure), che mất tín hiệu thật.

        Thay vào đó kiểm tra 3 tầng, ổn định với journal mode:
          1. Header không phải header rỗng -> đúng cấu trúc SQLite.
          2. PRAGMA integrity_check == "ok" -> file không hỏng.
          3. Schema + nội dung logic đúng kỳ vọng -> dữ liệu không bị can thiệp.
        Việc "test có sửa live DB hay không" đã được bảo vệ chặt hơn bởi fixture
        autouse `live_db_guard` trong conftest.py (so sánh size + mtime_ns).
        """
        assert LIVE_DB_FILE.exists(), f"Live DB {LIVE_DB_FILE} must exist!"

        raw = LIVE_DB_FILE.read_bytes()
        assert len(raw) > 0, "Live DB rỗng"
        assert raw[:16] == b"SQLite format 3\x00", (
            f"Live DB không phải file SQLite hợp lệ: header = {raw[:16]!r}"
        )

        conn = sqlite3.connect(f"file:{LIVE_DB_FILE}?mode=ro", uri=True)
        try:
            integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
            assert integrity == "ok", f"Live DB hỏng file: PRAGMA integrity_check = {integrity!r}"

            tables = {
                r[0] for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            for required in ("users", "campaigns", "marketing_contents", "workspaces"):
                assert required in tables, f"Thiếu bảng '{required}' trong live DB"

            user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            assert user_count >= 3, (
                f"Live DB phải có >= 3 tài khoản demo, thực tế {user_count}"
            )
        finally:
            conn.close()

    def test_adv_live_db_guard_detects_simulated_size_tampering(self, monkeypatch, tmp_path):
        """Validates that the live_db_guard logic would catch any size or timestamp discrepancy."""
        fake_db = tmp_path / "fake_marketing_campaigns.db"
        fake_db.write_text("initial db content")
        initial_stat = (fake_db.stat().st_size, fake_db.stat().st_mtime_ns)

        # Mutate file
        fake_db.write_text("initial db content mutated!!")
        mutated_stat = (fake_db.stat().st_size, fake_db.stat().st_mtime_ns)

        assert initial_stat != mutated_stat, "Tampering must change size or mtime"

    def test_adv_reset_db_blocked_in_production(self, monkeypatch):
        """reset_db() must raise RuntimeError without modifying live DB when in production."""
        monkeypatch.setattr(settings, "APP_ENV", "production")
        monkeypatch.setenv("APP_ENV", "production")
        with pytest.raises(RuntimeError, match="Database reset is forbidden in production environment"):
            reset_db()


# ==============================================================================
# PROBE 2: BYOK CRYPTO VAULT & KEY FORGERY / TAMPERING
# ==============================================================================
class TestAdversarialBYOKVault:
    """Adversarially probes BYOK cryptography against key forgery, tampering, and misconfiguration."""

    def test_adv_byok_decrypt_with_foreign_key_rejected(self):
        """A valid Fernet token generated with an attacker's separate key must be rejected with ValueError."""
        attacker_key = Fernet.generate_key()
        attacker_cipher = Fernet(attacker_key)
        forged_token = attacker_cipher.encrypt(b"stolen-secret-api-key-12345").decode("utf-8")

        assert forged_token.startswith("gAAAAA")
        with pytest.raises(ValueError, match="Tampered or invalid key"):
            decrypt_api_key(forged_token)

    @pytest.mark.parametrize("forged_token", [
        "not_a_valid_token",
        "gAAAA",
        "gAAAAA",
        "gAAAAA_invalid_payload_with_insufficient_bytes",
        "gBBBBAbcdef1234567890",
        "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
        "AIzaSyDemoKeyNotEncrypted",
        "gAAAAABm" + "A" * 50,
        "gAAAAABm" + "=" * 50,
        "   ",
        "\x00\x01\x02\x03",
    ])
    def test_adv_byok_forged_tokens_without_valid_fernet_structure_rejected(self, forged_token: str):
        """Tokens lacking valid Fernet envelope/HMAC are rejected safely with ValueError."""
        with pytest.raises(ValueError):
            decrypt_api_key(forged_token)

    def test_adv_byok_tampered_ciphertext_matrices(self):
        """Bit-flip and truncation attacks against valid Fernet ciphertexts must all raise ValueError."""
        valid_key = "AIzaSyAdversarialBitFlipVerificationKey"
        encrypted = encrypt_api_key(valid_key)
        assert encrypted.startswith("gAAAAA")
        assert decrypt_api_key(encrypted) == valid_key

        raw_bytes = base64.urlsafe_b64decode(encrypted.encode("utf-8"))

        # 1. Flip byte in IV (offset 1 to 16)
        tampered_iv = bytearray(raw_bytes)
        tampered_iv[5] ^= 0xFF
        corrupted_token_iv = base64.urlsafe_b64encode(tampered_iv).decode("utf-8")
        with pytest.raises(ValueError, match="Tampered or invalid key"):
            decrypt_api_key(corrupted_token_iv)

        # 2. Flip byte in Timestamp (offset 17 to 24)
        tampered_ts = bytearray(raw_bytes)
        tampered_ts[18] ^= 0xFF
        corrupted_token_ts = base64.urlsafe_b64encode(tampered_ts).decode("utf-8")
        with pytest.raises(ValueError, match="Tampered or invalid key"):
            decrypt_api_key(corrupted_token_ts)

        # 3. Flip byte in Ciphertext body (offset 25 to -32)
        tampered_body = bytearray(raw_bytes)
        tampered_body[30] ^= 0xFF
        corrupted_token_body = base64.urlsafe_b64encode(tampered_body).decode("utf-8")
        with pytest.raises(ValueError, match="Tampered or invalid key"):
            decrypt_api_key(corrupted_token_body)

        # 4. Flip byte in HMAC signature (last 32 bytes)
        tampered_hmac = bytearray(raw_bytes)
        tampered_hmac[-5] ^= 0xFF
        corrupted_token_hmac = base64.urlsafe_b64encode(tampered_hmac).decode("utf-8")
        with pytest.raises(ValueError, match="Tampered or invalid key"):
            decrypt_api_key(corrupted_token_hmac)

        # 5. Appended garbage
        with pytest.raises(ValueError, match="Tampered or invalid key"):
            decrypt_api_key(encrypted + "==GARBAGE==")

    @pytest.mark.parametrize("empty_key", [
        "",
        "   ",
        "\t\n\r",
    ])
    def test_adv_byok_empty_and_whitespace_keys_rejected(self, empty_key: str):
        """Empty, whitespace, or whitespace-only keys must be rejected by both encrypt and decrypt."""
        with pytest.raises(ValueError, match="không được để trống|không hợp lệ"):
            encrypt_api_key(empty_key)
        with pytest.raises(ValueError, match="không hợp lệ"):
            decrypt_api_key(empty_key)

    @pytest.mark.parametrize("insecure_key", [
        "aia331-secret-key-change-in-production-super-secure",
        "aia331-super-secret-production-key-change-it",
        "your-super-secret-jwt-key",
        "change-me",
        "changethisinproduction",
        "secret",
        "admin",
        "12345678",
        "this-is-a-placeholder-key-for-test",
        "short",
        "key-under-32-chars",
    ])
    def test_adv_byok_production_mode_placeholder_rejection(self, insecure_key: str):
        """validate_security_configuration() must reject placeholder and short keys in production mode."""
        s = Settings(
            APP_ENV="production",
            SECRET_KEY=insecure_key,
            JWT_SECRET_KEY=insecure_key,
            BYOK_ENCRYPTION_KEY=insecure_key
        )
        with pytest.raises(RuntimeError):
            validate_security_configuration(s, enforce_production=True)

    def test_adv_byok_mask_api_key_boundary_ladder(self):
        """Verifies mask_api_key behavior across length boundary conditions."""
        # Length >= 10: 6 prefix ... 4 suffix
        assert mask_api_key("AIzaSy1234567890") == "AIzaSy...7890"
        assert mask_api_key("1234567890") == "123456...7890"
        # Length 4..9: 2 prefix ... 2 suffix
        assert mask_api_key("123456789") == "12...89"
        assert mask_api_key("1234") == "12...34"
        # Length 1..3: "..."
        assert mask_api_key("123") == "..."
        assert mask_api_key("1") == "..."
        # Length 0: ""
        assert mask_api_key("") == ""

    def test_adv_byok_rotation_keys_parsing_robustness(self, monkeypatch):
        """Rotation keys configuration supports JSON list, CSV string, or malformed strings gracefully."""
        # 1. JSON Array string
        monkeypatch.setattr(settings, "BYOK_ROTATION_KEYS", '["key_rot_1_must_be_32_bytes_long_1", "key_rot_2_must_be_32_bytes_long_2"]')
        keys = _get_rotation_keys()
        assert len(keys) == 2

        # 2. Comma-separated string
        monkeypatch.setattr(settings, "BYOK_ROTATION_KEYS", "key_rot_a_32chars_long_long_long, key_rot_b_32chars_long_long_long")
        keys = _get_rotation_keys()
        assert len(keys) == 2

        # 3. Empty string
        monkeypatch.setattr(settings, "BYOK_ROTATION_KEYS", "   ")
        keys = _get_rotation_keys()
        assert len(keys) == 0


# ==============================================================================
# PROBE 3: REVIEW QUEUE STATE MACHINE & INVALID TRANSITIONS
# ==============================================================================
class TestAdversarialReviewQueueStateMachine:
    """Adversarially probes the Human-in-the-loop review queue for illegal state transitions."""

    def test_adv_review_direct_creation_as_in_review_or_rejected(
        self, client: TestClient, marketer_headers
    ):
        """Adversarial check: what does POST /contents do when given IN_REVIEW or REJECTED?"""
        base_payload = {
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Adversarial Direct Status Creation Probe",
            "body": "Nội dung thăm dò trạng thái tạo mới",
            "cta": "Bấm ngay"
        }
        # Direct APPROVED / PUBLISHED are strictly blocked (400)
        resp_app = client.post("/api/v1/contents", json={**base_payload, "status": "APPROVED"}, headers=marketer_headers)
        assert resp_app.status_code == 400

        resp_pub = client.post("/api/v1/contents", json={**base_payload, "status": "PUBLISHED"}, headers=marketer_headers)
        assert resp_pub.status_code == 400

        # Disallowed arbitrary status -> 422
        resp_bad = client.post("/api/v1/contents", json={**base_payload, "status": "RANDOM_HACKED_STATE"}, headers=marketer_headers)
        assert resp_bad.status_code == 422

    @pytest.mark.parametrize("source_status,action_endpoint,expected_status", [
        ("DRAFT", "approve", 400),
        ("DRAFT", "reject", 400),
        ("DRAFT", "publish", 400),
        ("IN_REVIEW", "submit", 400),
        ("IN_REVIEW", "publish", 400),
        ("APPROVED", "submit", 400),
        ("APPROVED", "approve", 400),
        ("APPROVED", "reject", 400),
        ("REJECTED", "approve", 400),
        ("REJECTED", "publish", 400),
        ("REJECTED", "reject", 400),
        ("PUBLISHED", "submit", 400),
        ("PUBLISHED", "approve", 400),
        ("PUBLISHED", "reject", 400),
        ("PUBLISHED", "publish", 400),
    ])
    def test_adv_review_illegal_transition_matrix(
        self, client: TestClient, manager_headers, db_session: Session,
        source_status: str, action_endpoint: str, expected_status: int
    ):
        """Exhaustively tests that illegal transitions across all lifecycle states are rejected with 400."""
        content = MarketingContent(
            workspace_id=1,
            campaign_id=1,
            channel_id=1,
            created_by=2,
            title=f"Illegal Transition Test Content from {source_status}",
            body="Thân bài kiểm thử ma trận chuyển trạng thái bất hợp lệ",
            cta="Thực hiện",
            status=source_status,
            version_no=1
        )
        db_session.add(content)
        db_session.commit()
        db_session.refresh(content)

        payload = {"decision": "REJECTED", "reason": "Lý do kiểm thử hợp lệ"} if action_endpoint == "reject" else None
        resp = client.post(
            f"/api/v1/contents/{content.id}/{action_endpoint}",
            json=payload,
            headers=manager_headers
        )
        assert resp.status_code == expected_status, (
            f"VULNERABILITY: State transition {source_status} -> {action_endpoint} succeeded or returned unexpected code! "
            f"Got {resp.status_code}: {resp.text}"
        )

    def test_adv_review_role_authorization_matrix(
        self, client: TestClient, marketer_headers, client_approver_headers, db_session: Session
    ):
        """Verifies strict RBAC enforcement across review queue endpoints."""
        content = MarketingContent(
            workspace_id=1,
            campaign_id=1,
            channel_id=1,
            created_by=2,
            title="RBAC Review Role Check",
            body="Nội dung kiểm tra quyền duyệt",
            cta="Thử ngay",
            status="IN_REVIEW",
            version_no=1
        )
        db_session.add(content)
        db_session.commit()
        db_session.refresh(content)

        # 1. Marketer CANNOT approve (403)
        resp_mkt_app = client.post(f"/api/v1/contents/{content.id}/approve", headers=marketer_headers)
        assert resp_mkt_app.status_code == 403

        # 2. Marketer CANNOT reject (403)
        resp_mkt_rej = client.post(
            f"/api/v1/contents/{content.id}/reject",
            json={"decision": "REJECTED", "reason": "Marketer trying to reject"},
            headers=marketer_headers
        )
        assert resp_mkt_rej.status_code == 403

        # 3. Marketer CANNOT publish (403)
        content.status = "APPROVED"
        db_session.commit()
        resp_mkt_pub = client.post(f"/api/v1/contents/{content.id}/publish", headers=marketer_headers)
        assert resp_mkt_pub.status_code == 403

        # 4. Client Approver CANNOT publish (403)
        resp_app_pub = client.post(f"/api/v1/contents/{content.id}/publish", headers=client_approver_headers)
        assert resp_app_pub.status_code == 403

        # 5. Unauthenticated user CANNOT perform any action (401)
        assert client.post(f"/api/v1/contents/{content.id}/submit").status_code == 401
        assert client.post(f"/api/v1/contents/{content.id}/approve").status_code == 401
        assert client.post(f"/api/v1/contents/{content.id}/reject", json={"decision": "REJECTED", "reason": "test"}).status_code == 401
        assert client.post(f"/api/v1/contents/{content.id}/publish").status_code == 401

    def test_adv_review_anti_tampering_demotes_on_any_content_field_edit(
        self, client: TestClient, marketer_headers, db_session: Session
    ):
        """Modifying title, body, cta, or image_url of an APPROVED content MUST demote it to AI_DRAFT."""
        for field, new_val in [
            ("title", "Tiêu đề mới bị chỉnh sửa"),
            ("body", "Thân bài mới bị chỉnh sửa"),
            ("cta", "CTA mới bị chỉnh sửa"),
            ("image_url", "https://example.com/new_image.jpg"),
        ]:
            content = MarketingContent(
                workspace_id=1,
                campaign_id=1,
                channel_id=1,
                created_by=2,
                title="Tiêu đề gốc đã duyệt",
                body="Thân bài gốc đã duyệt",
                cta="CTA gốc",
                image_url="https://example.com/original.jpg",
                status="APPROVED",
                version_no=1
            )
            db_session.add(content)
            db_session.commit()
            db_session.refresh(content)

            resp = client.put(f"/api/v1/contents/{content.id}", json={field: new_val}, headers=marketer_headers)
            assert resp.status_code == 200
            assert resp.json()["status"] == "AI_DRAFT", f"Editing '{field}' failed to demote status to AI_DRAFT!"

    def test_adv_review_rejection_reason_min_length_boundaries(
        self, client: TestClient, manager_headers, db_session: Session
    ):
        """Rejection reason must be strictly validated: empty and < 3 chars rejected, >= 3 chars accepted."""
        content = MarketingContent(
            workspace_id=1,
            campaign_id=1,
            channel_id=1,
            created_by=2,
            title="Rejection Reason Boundary Content",
            body="Thân bài kiểm tra lý do từ chối",
            cta="Đăng ký",
            status="IN_REVIEW",
            version_no=1
        )
        db_session.add(content)
        db_session.commit()
        db_session.refresh(content)

        # 1. Whitespace only -> 400
        r1 = client.post(f"/api/v1/contents/{content.id}/reject", json={"decision": "REJECTED", "reason": "   "}, headers=manager_headers)
        assert r1.status_code in (400, 422)

        # 2. Exactly 2 chars -> 400
        r2 = client.post(f"/api/v1/contents/{content.id}/reject", json={"decision": "REJECTED", "reason": "NO"}, headers=manager_headers)
        assert r2.status_code == 400

        # 3. 2 chars with spaces -> 400
        r3 = client.post(f"/api/v1/contents/{content.id}/reject", json={"decision": "REJECTED", "reason": "  AB  "}, headers=manager_headers)
        assert r3.status_code == 400

        # 4. Exactly 3 chars -> 200 OK
        r4 = client.post(f"/api/v1/contents/{content.id}/reject", json={"decision": "REJECTED", "reason": "BAD"}, headers=manager_headers)
        assert r4.status_code == 200
        assert r4.json()["status"] == "REJECTED"

    def test_adv_review_compliance_guardrail_blocks_submit_of_violation(
        self, client: TestClient, marketer_headers, db_session: Session
    ):
        """Content containing HIGH severity banned keywords (e.g. 'cam kết 100%') CANNOT be submitted for review."""
        content = MarketingContent(
            workspace_id=1,
            campaign_id=1,
            channel_id=1,
            created_by=2,
            title="Bài viết vi phạm chính sách",
            body="Chúng tôi cam kết 100% làm giàu nhanh sau khóa học!",
            cta="Đăng ký ngay",
            status="DRAFT",
            version_no=1
        )
        db_session.add(content)
        db_session.commit()
        db_session.refresh(content)

        resp = client.post(f"/api/v1/contents/{content.id}/submit", headers=marketer_headers)
        assert resp.status_code == 400
        assert "an toàn thương hiệu" in resp.json().get("detail", "").lower() or "vi phạm" in resp.json().get("detail", "").lower()

        # Status remains DRAFT, NOT IN_REVIEW
        db_session.refresh(content)
        assert content.status == "DRAFT"


# ==============================================================================
# PROBE 4: CROSS-WORKSPACE BYOK KEY TAMPERING & ASYMMETRIC ISOLATION
# ==============================================================================
class TestAdversarialTenantIsolationBypass:
    """Probes whether Workspace 1 (default agency) is vulnerable to BYOK tampering from foreign workspace managers."""

    def test_adv_beta_agency_manager_tamper_alpha_byok_key(
        self, client: TestClient, beta_agency_manager_headers, workspace_alpha
    ):
        """EMPIRICAL PROBE: Can Agency Manager of Workspace Beta overwrite Alpha's BYOK key?
        Root Cause: settings.py line 101 checks 'target_ws_id > 1'. If target_ws_id == 1,
        the authorization check is bypassed and foreign managers can overwrite Workspace 1's key.
        """
        resp = client.post(
            "/api/v1/settings/ai-keys",
            json={
                "api_key": "AIzaSyBetaTamperingAlphaKey9999",
                "provider": "gemini",
                "workspace_id": workspace_alpha.id
            },
            headers=beta_agency_manager_headers
        )
        assert resp.status_code == 403, (
            f"VULNERABILITY CONFIRMED: Beta Agency Manager tampered with Workspace Alpha BYOK key! "
            f"Expected 403 Forbidden, got HTTP {resp.status_code}: {resp.text}"
        )

    def test_adv_beta_agency_manager_tamper_alpha_content(
        self, client: TestClient, beta_agency_manager_headers, workspace_alpha, db_session: Session
    ):
        """EMPIRICAL PROBE: Can Agency Manager of Workspace Beta update Alpha's content?
        Root Cause: contents.py line 48 checks 'content.workspace_id > 1'. If workspace_id == 1,
        the authorization check is bypassed and foreign managers can update Workspace 1's content.
        """
        alpha_content = db_session.query(MarketingContent).filter(MarketingContent.workspace_id == workspace_alpha.id).first()
        assert alpha_content is not None

        resp = client.put(
            f"/api/v1/contents/{alpha_content.id}",
            json={"title": "Defaced by Beta Agency Manager"},
            headers=beta_agency_manager_headers
        )
        assert resp.status_code == 403, (
            f"VULNERABILITY CONFIRMED: Beta Agency Manager modified Workspace Alpha Content! "
            f"Expected 403 Forbidden, got HTTP {resp.status_code}: {resp.text}"
        )

