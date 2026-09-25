"""Adversarial Boundary, Tamper Resistance, and Whitelist Stress Test Suite for Milestone 6 (R6).
Authored by Challenger 2 (Boundary Stress, Tamper Resistance & Prohibited Provider Challenger).

Empirical Verification Matrix:
1. Strict Gemini Whitelist Enforcement:
   - Prohibited providers ("anthropic", "openai") rejected with HTTP 422.
   - Prohibited models ("claude-3-7-sonnet", "gpt-4o", "claude-3-5-sonnet", non-Gemini models) rejected with HTTP 422.
   - Case variations, whitespace padding, and both endpoints (/test-ai-connection, /ai-keys) tested.
2. Empty and Whitespace Key Handling:
   - Empty string "", single/multiple spaces "   ", tabs/newlines "\t\n  \r", and missing keys rejected with HTTP 422.
   - Crypto layer raises ValueError on empty or whitespace keys.
3. Invalid Dummy Key Safe Handling:
   - "invalid_dummy_key_0000" and related invalid prefixes return status 200/400 with success: false cleanly.
   - Zero HTTP 500 crashes on invalid or malformed keys.
4. Cryptographic Tamper Resistance (Fernet HMAC & Bit-Flip Stress):
   - 1-character string mutation at different positions raises ValueError("Tampered or invalid key").
   - Raw Fernet byte mutations (Version, Timestamp, IV, Ciphertext, HMAC signature) all detected by HMAC and raise ValueError.
   - Single-bit flip (XOR 0x01) detected and rejected.
   - Direct SQLite database tampering handled gracefully by GET endpoints and AIService resolver without HTTP 500.
5. Zero Plaintext Exposure:
   - GET /api/v1/settings/ai-keys and /list never expose "api_key" or "encrypted_key".
   - Plaintext secret substring is never present in response text.
   - Masked key contains at least 3 masking characters ('...' or '*').
"""

import base64
import os
import pytest
from typing import Dict, Any
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from pydantic import ValidationError

from app.core.config import settings
from app.core.crypto import (
    get_fernet_cipher, encrypt_api_key, decrypt_api_key, mask_api_key
)
from app.models.entities import User, CustomApiKey, Workspace, WorkspaceMember
from app.schemas.schemas import (
    AIKeyTestRequest, AIKeyTestResponse, AIKeyCreate, AIKeyResponse
)
from app.services.ai.ai_service import AIService


# ==============================================================================
# FIXTURES
# ==============================================================================

@pytest.fixture
def manager_headers(client: TestClient) -> Dict[str, str]:
    resp = client.post("/api/v1/auth/login", json={"email": "manager@ictu.edu.vn", "password": "Manager@123"})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
def marketer_headers(client: TestClient) -> Dict[str, str]:
    resp = client.post("/api/v1/auth/login", json={"email": "marketer@ictu.edu.vn", "password": "Marketer@123"})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


# ==============================================================================
# CHALLENGE 1: Strict Gemini Whitelist Enforcement
# ==============================================================================

class TestChallenge1StrictGeminiWhitelist:
    """Challenge 1: Verify strict enforcement of Gemini-only whitelist and rejection of prohibited providers/models."""

    @pytest.mark.parametrize("payload", [
        {"provider": "anthropic", "api_key": "sk-ant-test-key", "model": "claude-3-7-sonnet"},
        {"provider": "openai", "api_key": "sk-test-openai-key", "model": "gpt-4o"},
        {"provider": "gemini", "api_key": "AIzaSyValidFormatKey", "model": "claude-3-5-sonnet"},
        {"provider": "anthropic", "api_key": "sk-ant-test-key", "model": "gemini-2.5-flash"},
        {"provider": "openai", "api_key": "sk-test-openai-key", "model": "gemini-2.5-flash"},
        {"provider": "gemini", "api_key": "AIzaSyValidFormatKey", "model": "claude-3-7-sonnet"},
        {"provider": "gemini", "api_key": "AIzaSyValidFormatKey", "model": "gpt-4o"},
        {"provider": "gemini", "api_key": "AIzaSyValidFormatKey", "model": "claude"},
        {"provider": "gemini", "api_key": "AIzaSyValidFormatKey", "model": "gpt"},
        {"provider": "gemini", "api_key": "AIzaSyValidFormatKey", "model": "sonnet"},
        {"provider": "gemini", "api_key": "AIzaSyValidFormatKey", "model": "mistral-large"},
        {"provider": "gemini", "api_key": "AIzaSyValidFormatKey", "model": "llama-3-70b"},
        {"provider": "gemini", "api_key": "AIzaSyValidFormatKey", "model": "deepseek-coder"},
    ])
    def test_c1_01_prohibited_models_and_providers_rejected_test_connection(self, client: TestClient, manager_headers, payload):
        """Verify POST /api/v1/settings/test-ai-connection rejects prohibited providers and models with HTTP 422 or 400."""
        resp = client.post("/api/v1/settings/test-ai-connection", json=payload, headers=manager_headers)
        assert resp.status_code in (400, 422), f"Expected 400 or 422 for payload {payload}, got {resp.status_code}: {resp.text}"

    @pytest.mark.parametrize("payload", [
        {"provider": "anthropic", "api_key": "AIzaSyValidFormatKey", "model": "gemini-2.5-flash"},
        {"provider": "openai", "api_key": "AIzaSyValidFormatKey", "model": "gemini-2.5-flash"},
        {"provider": "gemini", "api_key": "AIzaSyValidFormatKey", "model": "claude-3-7-sonnet"},
        {"provider": "gemini", "api_key": "AIzaSyValidFormatKey", "model": "gpt-4o"},
        {"provider": "gemini", "api_key": "AIzaSyValidFormatKey", "model": "claude-3-5-sonnet"},
        {"provider": "openrouter", "api_key": "AIzaSyValidFormatKey", "model": "gemini-2.5-flash"},
    ])
    def test_c1_02_prohibited_models_and_providers_rejected_save_ai_keys(self, client: TestClient, manager_headers, payload):
        """Verify POST /api/v1/settings/ai-keys rejects prohibited providers and models with HTTP 422 or 400."""
        resp = client.post("/api/v1/settings/ai-keys", json=payload, headers=manager_headers)
        assert resp.status_code in (400, 422), f"Expected 400 or 422 for payload {payload}, got {resp.status_code}: {resp.text}"

    @pytest.mark.parametrize("provider_variant,model_variant", [
        ("  ANTHROPIC  ", "gemini-2.5-flash"),
        ("OpenAI", "gemini-2.5-flash"),
        ("gemini", "  CLAUDE-3-7-SONNET  "),
        ("gemini", "GPT-4O"),
        ("gemini", "Claude-3-5-Sonnet"),
        ("gemini", "SONNET"),
    ])
    def test_c1_03_case_insensitive_and_padded_prohibited_rejected(self, client: TestClient, manager_headers, provider_variant, model_variant):
        """Verify case insensitivity and whitespace-padded variants of prohibited names are strictly rejected."""
        payload = {
            "provider": provider_variant,
            "api_key": "AIzaSyValidFormatKey123",
            "model": model_variant
        }
        resp = client.post("/api/v1/settings/test-ai-connection", json=payload, headers=manager_headers)
        assert resp.status_code in (400, 422)

    def test_c1_04_schema_level_validation_prohibited_names(self):
        """Verify Pydantic schema validation directly rejects prohibited names with ValidationError."""
        with pytest.raises(ValidationError):
            AIKeyTestRequest(provider="anthropic", api_key="valid-key", model="gemini-2.5-flash")

        with pytest.raises(ValidationError):
            AIKeyTestRequest(provider="openai", api_key="valid-key", model="gemini-2.5-flash")

        with pytest.raises(ValidationError):
            AIKeyTestRequest(provider="gemini", api_key="valid-key", model="claude-3-7-sonnet")

        with pytest.raises(ValidationError):
            AIKeyTestRequest(provider="gemini", api_key="valid-key", model="gpt-4o")

        with pytest.raises(ValidationError):
            AIKeyTestRequest(provider="gemini", api_key="valid-key", model="claude-3-5-sonnet")

        with pytest.raises(ValidationError):
            AIKeyCreate(provider="anthropic", api_key="valid-key")

        with pytest.raises(ValidationError):
            AIKeyCreate(provider="openai", api_key="valid-key")

        with pytest.raises(ValidationError):
            AIKeyCreate(provider="gemini", api_key="valid-key", model="claude-3-7-sonnet")


# ==============================================================================
# CHALLENGE 2: Empty and Whitespace Key Handling
# ==============================================================================

class TestChallenge2EmptyAndWhitespaceKeys:
    """Challenge 2: Verify empty and whitespace-only API keys are strictly rejected with HTTP 422."""

    @pytest.mark.parametrize("empty_key", [
        "",
        " ",
        "   ",
        "\t",
        "\n",
        "\r\n",
        " \t \n \r ",
    ])
    def test_c2_01_empty_whitespace_rejected_on_test_connection(self, client: TestClient, manager_headers, empty_key):
        """Verify /test-ai-connection rejects empty and whitespace keys with HTTP 422."""
        resp = client.post("/api/v1/settings/test-ai-connection", json={
            "provider": "gemini",
            "api_key": empty_key,
            "model": "gemini-2.5-flash"
        }, headers=manager_headers)
        assert resp.status_code == 422, f"Expected 422 for empty key {repr(empty_key)}, got {resp.status_code}: {resp.text}"

    @pytest.mark.parametrize("empty_key", [
        "",
        " ",
        "   ",
        "\t\t",
        "\n\n",
        "  \t\n  ",
    ])
    def test_c2_02_empty_whitespace_rejected_on_store_keys(self, client: TestClient, manager_headers, empty_key):
        """Verify /ai-keys rejects empty and whitespace keys with HTTP 422."""
        resp = client.post("/api/v1/settings/ai-keys", json={
            "provider": "gemini",
            "api_key": empty_key,
            "model": "gemini-2.5-flash"
        }, headers=manager_headers)
        assert resp.status_code == 422, f"Expected 422 for empty key {repr(empty_key)}, got {resp.status_code}: {resp.text}"

    def test_c2_03_missing_or_null_key_rejected(self, client: TestClient, manager_headers):
        """Verify omitting the api_key field or sending null returns HTTP 422."""
        resp1 = client.post("/api/v1/settings/test-ai-connection", json={
            "provider": "gemini",
            "model": "gemini-2.5-flash"
        }, headers=manager_headers)
        assert resp1.status_code == 422

        resp2 = client.post("/api/v1/settings/test-ai-connection", json={
            "provider": "gemini",
            "api_key": None,
            "model": "gemini-2.5-flash"
        }, headers=manager_headers)
        assert resp2.status_code == 422

        resp3 = client.post("/api/v1/settings/ai-keys", json={
            "provider": "gemini",
            "model": "gemini-2.5-flash"
        }, headers=manager_headers)
        assert resp3.status_code == 422

    def test_c2_04_crypto_layer_rejects_empty_and_whitespace(self):
        """Verify encrypt_api_key and decrypt_api_key raise ValueError on empty or whitespace keys."""
        for invalid in ["", " ", "   ", "\t", "\n", None]:
            with pytest.raises(ValueError):
                encrypt_api_key(invalid)
            with pytest.raises(ValueError):
                decrypt_api_key(invalid)


# ==============================================================================
# CHALLENGE 3: Invalid Dummy Key Safe Handling
# ==============================================================================

class TestChallenge3InvalidDummyKeySafety:
    """Challenge 3: Verify testing invalid dummy keys returns success: false cleanly without HTTP 500 crash."""

    @pytest.mark.parametrize("dummy_key", [
        "invalid_dummy_key_0000",
        "invalid_dummy_key_99999",
        "invalid_expired_token_12345",
        "invalid_key_random_xyz",
    ])
    def test_c3_01_invalid_dummy_keys_fail_cleanly(self, client: TestClient, manager_headers, dummy_key):
        """Verify invalid dummy keys return HTTP 200 or 400 with success: False and NEVER crash 500."""
        resp = client.post("/api/v1/settings/test-ai-connection", json={
            "provider": "gemini",
            "api_key": dummy_key,
            "model": "gemini-2.5-flash"
        }, headers=manager_headers)

        assert resp.status_code in (200, 400), f"Expected 200 or 400, got {resp.status_code}: {resp.text}"
        assert resp.status_code != 500, "System must NEVER crash with HTTP 500 on invalid keys"

        data = resp.json()
        assert data.get("success") is False
        assert "latency_ms" in data
        assert data["latency_ms"] >= 0
        assert data.get("error") is not None or "message" in data

    def test_c3_02_arbitrary_unrecognized_key_fails_cleanly(self, client: TestClient, manager_headers):
        """Verify sending an arbitrary unrecognized key does not raise unhandled exceptions or crash 500."""
        resp = client.post("/api/v1/settings/test-ai-connection", json={
            "provider": "gemini",
            "api_key": "AIzaSyNonExistentMalformedKeyXYZ9876543210",
            "model": "gemini-2.5-flash"
        }, headers=manager_headers)

        assert resp.status_code in (200, 400)
        assert resp.status_code != 500
        data = resp.json()
        assert data.get("success") is False


# ==============================================================================
# CHALLENGE 4: Cryptographic Tamper Resistance (Fernet HMAC & Bit-Flip Stress)
# ==============================================================================

class TestChallenge4TamperResistance:
    """Challenge 4: Verify HMAC integrity and tamper resistance against bit-flips, byte modifications, and DB tampering."""

    def test_c4_01_string_level_tamper_raises_value_error(self):
        """Verify modifying 1 character in base64 ciphertext at different positions raises ValueError."""
        plain = "AIzaSyRealGeminiKeyExample123456789"
        valid_cipher = encrypt_api_key(plain)

        # Tamper at index 10, 20, 40, and last character
        for pos in [10, 20, 40, len(valid_cipher) - 2]:
            tampered = list(valid_cipher)
            tampered[pos] = "A" if tampered[pos] != "A" else "B"
            tampered_str = "".join(tampered)

            with pytest.raises(ValueError, match="Tampered or invalid key"):
                decrypt_api_key(tampered_str)

    def test_c4_02_raw_fernet_structure_byte_tampering(self):
        """Verify tampering each structural component of Fernet token is caught by HMAC verification:
        - Version (byte 0)
        - Timestamp (bytes 1-8)
        - IV (bytes 9-24)
        - Ciphertext payload (bytes 25..N-32)
        - HMAC signature (last 32 bytes)
        """
        plain = "AIzaSySensitiveSecurityKeyToProtect12345"
        valid_cipher = encrypt_api_key(plain)
        raw_bytes = base64.urlsafe_b64decode(valid_cipher.encode("utf-8"))

        # Fernet structure: 1 (version) + 8 (timestamp) + 16 (IV) + payload + 32 (HMAC)
        assert len(raw_bytes) > 57

        critical_offsets = [
            0,                     # Version byte
            4,                     # Timestamp byte
            15,                    # IV byte
            28,                    # Payload ciphertext byte
            len(raw_bytes) - 1,    # Last byte of HMAC
            len(raw_bytes) - 16,   # Middle byte of HMAC
        ]

        for offset in critical_offsets:
            tampered_bytes = bytearray(raw_bytes)
            # Invert 1 byte
            tampered_bytes[offset] = (tampered_bytes[offset] ^ 0xFF)
            tampered_token = base64.urlsafe_b64encode(tampered_bytes).decode("utf-8")

            with pytest.raises(ValueError, match="Tampered or invalid key"):
                decrypt_api_key(tampered_token)

    def test_c4_03_single_bit_flip_detected_by_hmac(self):
        """Verify a single-bit flip (XOR 0x01) anywhere in the Fernet token is detected and rejected."""
        plain = "AIzaSySingleBitFlipVerificationKey"
        valid_cipher = encrypt_api_key(plain)
        raw_bytes = base64.urlsafe_b64decode(valid_cipher.encode("utf-8"))

        # Flip the least significant bit of byte 12 (IV)
        tampered_bytes = bytearray(raw_bytes)
        tampered_bytes[12] ^= 0x01
        tampered_token = base64.urlsafe_b64encode(tampered_bytes).decode("utf-8")

        with pytest.raises(ValueError, match="Tampered or invalid key"):
            decrypt_api_key(tampered_token)

    def test_c4_04_truncated_and_appended_ciphertext_rejected(self):
        """Verify truncated tokens and tokens with appended garbage are rejected."""
        valid_cipher = encrypt_api_key("AIzaSyTruncationTestKey123")

        # Truncated
        truncated = valid_cipher[:-8]
        with pytest.raises(ValueError, match="Tampered or invalid key"):
            decrypt_api_key(truncated)

        # Appended garbage
        appended = valid_cipher + "XYZ123=="
        with pytest.raises(ValueError, match="Tampered or invalid key"):
            decrypt_api_key(appended)

    def test_c4_05_direct_sqlite_db_tampering_immunity(self, client: TestClient, manager_headers, db_session: Session):
        """Adversarial Test: Directly tamper 1 byte in the SQLite custom_api_keys table:
        1. Calling decrypt_api_key on the tampered record raises ValueError.
        2. Calling GET /api/v1/settings/ai-keys handles the corruption gracefully without HTTP 500.
        3. Calling AIService.resolve_api_key detects corruption, logs error, and safely falls back without crash.
        """
        # 1. Lưu key hợp lệ
        save_resp = client.post("/api/v1/settings/ai-keys", json={
            "provider": "gemini",
            "api_key": "AIzaSyOriginalVaultKeyBeforeTampering9999",
            "model": "gemini-2.5-flash",
            "workspace_id": 1
        }, headers=manager_headers)
        assert save_resp.status_code in (200, 201)

        # 2. Truy vấn trực tiếp từ SQLite DB
        key_record = db_session.query(CustomApiKey).filter(
            CustomApiKey.workspace_id == 1,
            CustomApiKey.provider == "gemini"
        ).first()
        assert key_record is not None
        original_encrypted = key_record.encrypted_key

        # 3. Can thiệp trực tiếp 1 byte vào SQLite column (tampering)
        tampered_chars = list(original_encrypted)
        tampered_chars[15] = "Z" if tampered_chars[15] != "Z" else "Y"
        key_record.encrypted_key = "".join(tampered_chars)
        db_session.commit()
        db_session.refresh(key_record)

        # 4. Xác nhận decrypt_api_key ném ValueError
        with pytest.raises(ValueError, match="Tampered or invalid key"):
            decrypt_api_key(key_record.encrypted_key)

        # 5. Gọi GET /settings/ai-keys -> Không được crash 500, phải trả 200 với fallback an toàn
        get_resp = client.get("/api/v1/settings/ai-keys?workspace_id=1", headers=manager_headers)
        assert get_resp.status_code == 200, f"Expected 200 fallback, got {get_resp.status_code}: {get_resp.text}"
        data = get_resp.json()
        assert "masked_key" in data
        assert "AIzaSy" in data["masked_key"] or "..." in data["masked_key"]
        assert "api_key" not in data

        # 6. Gọi AIService.resolve_api_key -> Phải bắt lỗi và fallback an toàn sang SYSTEM/FALLBACK
        service = AIService()
        res = service.resolve_api_key(db=db_session, workspace_id=1, user_id=1)
        assert res is not None
        assert res["tier"] in ("SYSTEM", "FALLBACK")


# ==============================================================================
# CHALLENGE 5: Zero Plaintext Exposure
# ==============================================================================

class TestChallenge5ZeroPlaintextExposure:
    """Challenge 5: Verify plaintext API keys are never exposed in GET responses, logs, or listings."""

    def test_c5_01_get_ai_keys_zero_plaintext_leak(self, client: TestClient, manager_headers):
        """Verify GET /api/v1/settings/ai-keys never exposes plaintext api_key or encrypted_key."""
        secret_key = "AIzaSySuperSecretEnterpriseKey9876543210ABCDEF"
        middle_sensitive_chars = "9876543210"

        # Save key
        save_resp = client.post("/api/v1/settings/ai-keys", json={
            "provider": "gemini",
            "api_key": secret_key,
            "model": "gemini-2.5-flash",
            "workspace_id": 1
        }, headers=manager_headers)
        assert save_resp.status_code in (200, 201)

        # Query key
        resp = client.get("/api/v1/settings/ai-keys?workspace_id=1", headers=manager_headers)
        assert resp.status_code == 200
        data = resp.json()

        # Check zero plaintext exposure in JSON structure
        assert "api_key" not in data, "CRITICAL: 'api_key' must NEVER be present in GET response!"
        assert "encrypted_key" not in data, "CRITICAL: 'encrypted_key' must NOT be exposed in GET response!"

        # Check masked_key format
        masked = data.get("masked_key", "")
        assert masked, "masked_key must not be empty"
        assert "..." in masked or "*" in masked, "masked_key must contain masking symbols"

        # Check raw HTTP response body text does NOT contain sensitive middle characters
        assert middle_sensitive_chars not in resp.text, (
            f"CRITICAL LEAK: Sensitive plaintext characters '{middle_sensitive_chars}' found in raw response text!"
        )

    def test_c5_02_get_ai_keys_list_zero_plaintext_leak(self, client: TestClient, manager_headers):
        """Verify GET /api/v1/settings/ai-keys/list never exposes plaintext keys across multiple records."""
        resp = client.get("/api/v1/settings/ai-keys/list", headers=manager_headers)
        assert resp.status_code == 200
        items = resp.json()
        assert isinstance(items, list)

        for item in items:
            assert "api_key" not in item
            assert "encrypted_key" not in item
            masked = item.get("masked_key", "")
            assert "..." in masked or "*" in masked
            # Verify masking length has at least 3 masking chars
            mask_char_count = masked.count(".") + masked.count("*")
            assert mask_char_count >= 3, f"Masking in {masked} has fewer than 3 mask characters"

    @pytest.mark.parametrize("plain,expected_contain", [
        ("AIzaSy1234567890abcdef", "..."),
        ("123456", "..."),
        ("abc", "..."),
        ("ab", "..."),
    ])
    def test_c5_03_mask_api_key_formats_guarantee_three_mask_chars(self, plain, expected_contain):
        """Verify mask_api_key always produces at least 3 masking characters ('...') for all key lengths."""
        masked = mask_api_key(plain)
        assert expected_contain in masked
        assert masked.count(".") >= 3 or masked.count("*") >= 3
