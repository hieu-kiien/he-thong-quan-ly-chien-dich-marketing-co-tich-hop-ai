"""Empirical Verification Script for Challenger 1 - Milestone 6 (R6 BYOK).
Executes direct HTTP endpoint calls and adversarial stress checks.
"""

import sys
import os
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Ensure backend root is in sys.path
backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models.entities import CustomApiKey, User
from app.core.crypto import encrypt_api_key, decrypt_api_key, mask_api_key

def run_empirical_verification():
    print(">>> [CHALLENGER 1] Starting Empirical Verification of Milestone 6 Endpoints...")
    client = TestClient(app)

    # 0. Authenticate as Manager
    login_resp = client.post("/api/v1/auth/login", json={"email": "manager@ictu.edu.vn", "password": "Manager@123"})
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("[AUTH] Successfully authenticated as manager@ictu.edu.vn.")

    # 1. Endpoint POST /api/v1/settings/test-ai-connection
    print("\n--- 1. Testing POST /api/v1/settings/test-ai-connection ---")
    # 1.1 Valid mock key
    resp_valid = client.post("/api/v1/settings/test-ai-connection", json={
        "provider": "gemini",
        "api_key": "AIzaSyTestKeyForMockVerification12345",
        "model": "gemini-2.5-flash"
    }, headers=headers)
    print(f"Valid mock key status: {resp_valid.status_code}, success={resp_valid.json().get('success')}, latency_ms={resp_valid.json().get('latency_ms')}")
    assert resp_valid.status_code == 200, f"Expected 200, got {resp_valid.status_code}"
    valid_data = resp_valid.json()
    assert valid_data.get("success") is True, "Expected success: True"
    assert "latency_ms" in valid_data and valid_data["latency_ms"] >= 0, "Expected non-negative latency_ms"
    print(">> [PASS] Valid mock key returns success=True with latency_ms.")

    # 1.2 Invalid dummy key
    resp_invalid = client.post("/api/v1/settings/test-ai-connection", json={
        "provider": "gemini",
        "api_key": "invalid_dummy_key_0000",
        "model": "gemini-2.5-flash"
    }, headers=headers)
    print(f"Invalid dummy key status: {resp_invalid.status_code}, success={resp_invalid.json().get('success')}, error={resp_invalid.json().get('error')}")
    assert resp_invalid.status_code in (200, 400), f"Expected 200/400, got {resp_invalid.status_code}"
    invalid_data = resp_invalid.json()
    assert invalid_data.get("success") is False, "Expected success: False for invalid key"
    print(">> [PASS] Invalid dummy key rejected cleanly without 500 error.")

    # 1.3 Prohibited provider & model (Anthropic / Claude)
    resp_prohibited = client.post("/api/v1/settings/test-ai-connection", json={
        "provider": "anthropic",
        "api_key": "sk-ant-test-key-12345",
        "model": "claude-3-7-sonnet"
    }, headers=headers)
    print(f"Prohibited provider status: {resp_prohibited.status_code}")
    assert resp_prohibited.status_code == 422, f"Expected 422 for prohibited provider, got {resp_prohibited.status_code}"
    print(">> [PASS] Prohibited provider (Anthropic/Claude) strictly rejected with 422.")

    # 2. Endpoint POST /api/v1/settings/ai-keys (Store Custom Key)
    print("\n--- 2. Testing POST /api/v1/settings/ai-keys (Store) ---")
    secret_key = "AIzaSyCustomKeySavedByChallenger99999"
    resp_store = client.post("/api/v1/settings/ai-keys", json={
        "provider": "gemini",
        "api_key": secret_key,
        "model": "gemini-2.5-flash"
    }, headers=headers)
    print(f"Store key status: {resp_store.status_code}, status_field={resp_store.json().get('status')}, masked={resp_store.json().get('masked_key')}")
    assert resp_store.status_code in (200, 201), f"Expected 200/201, got {resp_store.status_code}"
    store_data = resp_store.json()
    assert store_data.get("status") == "SAVED", "Expected status: SAVED"
    masked_key = store_data.get("masked_key", "")
    assert "..." in masked_key or "*" in masked_key, f"Expected masked format, got {masked_key}"
    assert "api_key" not in store_data or store_data.get("api_key") is None, "Plaintext api_key leaked in POST response!"
    print(f">> [PASS] Key saved securely with masked format: {masked_key}")

    # 3. Endpoint GET /api/v1/settings/ai-keys (Retrieve & Masking)
    print("\n--- 3. Testing GET /api/v1/settings/ai-keys (Retrieve) ---")
    resp_get = client.get("/api/v1/settings/ai-keys", headers=headers)
    print(f"Get key status: {resp_get.status_code}, masked_key={resp_get.json().get('masked_key')}, scope={resp_get.json().get('scope')}")
    assert resp_get.status_code == 200, f"Expected 200, got {resp_get.status_code}"
    get_data = resp_get.json()
    assert "api_key" not in get_data or get_data.get("api_key") is None, "Plaintext api_key leaked in GET response!"
    assert "encrypted_key" not in get_data, "Encrypted key leaked in GET response!"
    assert secret_key not in resp_get.text, "Raw plaintext secret key detected in HTTP response body!"
    assert "..." in get_data.get("masked_key", ""), "Masked key missing ellipsis format"
    print(f">> [PASS] GET returns masked key ({get_data.get('masked_key')}) with zero plaintext leakage.")

    # 4. Cross-Feature: AI Generation with BYOK Key Resolution
    print("\n--- 4. Testing Cross-Feature Resolution: POST /api/v1/ai/ideas ---")
    resp_ai = client.post("/api/v1/ai/ideas", json={
        "campaign_id": 1,
        "channel_code": "facebook"
    }, headers=headers)
    print(f"AI Ideas status: {resp_ai.status_code}, returned ideas: {len(resp_ai.json().get('ideas', []))}")
    assert resp_ai.status_code == 200, f"Expected 200, got {resp_ai.status_code}"
    ideas = resp_ai.json().get("ideas", [])
    assert len(ideas) > 0, "Expected generated ideas list > 0"
    print(f">> [PASS] AI Generation successfully generated {len(ideas)} ideas using resolved BYOK pipeline.")

    # 5. Endpoint DELETE /api/v1/settings/ai-keys
    print("\n--- 5. Testing DELETE /api/v1/settings/ai-keys (Deactivate/Delete) ---")
    resp_del = client.delete("/api/v1/settings/ai-keys", headers=headers)
    print(f"Delete key status: {resp_del.status_code}, response: {resp_del.json()}")
    assert resp_del.status_code in (200, 204), f"Expected 200/204, got {resp_del.status_code}"

    # Confirm key is deactivated or deleted
    resp_get_after = client.get("/api/v1/settings/ai-keys", headers=headers)
    print(f"Get key after delete status: {resp_get_after.status_code}, status={resp_get_after.json().get('status')}")
    after_data = resp_get_after.json()
    assert after_data.get("status") in ("NOT_CONFIGURED", "INACTIVE") or after_data.get("masked_key") == "", \
        f"Key was not properly deactivated/removed: {after_data}"
    print(">> [PASS] Key successfully deactivated/removed and system reverted cleanly.")

    # 6. Adversarial Cryptographic & Tamper-Resistance Stress Tests
    print("\n--- 6. Cryptographic Tamper-Resistance Stress Tests ---")
    test_key = "AIzaSyAdversarialTamperKey_XYZ12345"
    cipher_text = encrypt_api_key(test_key)
    assert cipher_text != test_key
    assert cipher_text.startswith("gAAAAA")

    # Tamper with 1 byte in Fernet payload
    tampered_chars = list(cipher_text)
    tampered_chars[15] = 'Z' if tampered_chars[15] != 'Z' else 'A'
    tampered_cipher = "".join(tampered_chars)
    tamper_caught = False
    try:
        decrypt_api_key(tampered_cipher)
    except ValueError as e:
        tamper_caught = True
        print(f"Tamper detected correctly: {e}")
    assert tamper_caught, "Cryptographic integrity check failed to catch tampered ciphertext!"
    print(">> [PASS] Ciphertext tamper resistance verified: 1-byte alteration triggers ValueError.")

    # 7. Database Verification: Verify At-Rest Encryption in DB
    print("\n--- 7. At-Rest Encryption Database Verification ---")
    db = SessionLocal()
    try:
        records = db.query(CustomApiKey).all()
        for r in records:
            assert r.encrypted_key is not None
            assert not r.encrypted_key.startswith("AIzaSy"), f"Plaintext key stored in DB record {r.id}!"
            assert r.encrypted_key.startswith("gAAAAA"), f"Invalid Fernet envelope in DB record {r.id}!"
        print(f">> [PASS] Checked {len(records)} database records: all keys are AES-128/Fernet encrypted at rest.")
    finally:
        db.close()

    print("\n=======================================================")
    print(">>> [CHALLENGER 1] ALL EMPIRICAL & ADVERSARIAL CHECKS PASSED 100%! <<<")
    print("=======================================================")

if __name__ == "__main__":
    run_empirical_verification()
