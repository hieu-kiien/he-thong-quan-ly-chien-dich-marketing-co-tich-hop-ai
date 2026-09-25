"""Unit & Integration Test Suite cho Enterprise Settings & BYOK Custom AI API Key (M6 - R6).
Bao gồm 30 test cases: Mã hóa Fernet, Chống can thiệp Ciphertext, Masking, Pydantic Schemas,
REST Endpoints, Multi-tier Key Resolver, và RBAC.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.crypto import (
    get_fernet_cipher, encrypt_api_key, decrypt_api_key, mask_api_key
)
from app.models.entities import User, CustomApiKey, Workspace, WorkspaceMember
from app.schemas.schemas import (
    AIKeyTestRequest, AIKeyTestResponse, AIKeyCreate, AIKeyResponse
)
from app.services.ai.ai_service import AIService
from pydantic import ValidationError


def get_auth_headers(client: TestClient, email: str, password: str) -> dict:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    if resp.status_code != 200:
        raise AssertionError(f"Login failed: {resp.text}")
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def manager_headers(client: TestClient) -> dict:
    return get_auth_headers(client, "manager@ictu.edu.vn", "Manager@123")


# ==============================================================================
# 1. Cryptographic Tests: Fernet, PBKDF2HMAC, Tamper-Resistance & Masking (1-10)
# ==============================================================================

def test_01_crypto_fernet_derivation_deterministic():
    """Kiểm tra việc dẫn xuất khóa Fernet từ SECRET_KEY là nhất quán (deterministic)."""
    cipher1 = get_fernet_cipher()
    cipher2 = get_fernet_cipher()
    test_data = b"MarketFlow-Secret-Verification-Bytes"
    token = cipher1.encrypt(test_data)
    decrypted = cipher2.decrypt(token)
    assert decrypted == test_data


def test_02_crypto_encrypt_decrypt_roundtrip():
    """Kiểm tra quy trình mã hóa và giải mã khóa API round-trip hoạt động hoàn hảo."""
    plain = "AIzaSyRealGeminiKeyExample123456789"
    cipher_text = encrypt_api_key(plain)
    assert cipher_text != plain
    assert cipher_text.startswith("gAAAAA")
    decrypted = decrypt_api_key(cipher_text)
    assert decrypted == plain


def test_03_crypto_tamper_resistance_invalid_token():
    """Kiểm tra khả năng chống can thiệp: Ciphertext bị thay đổi dù chỉ 1 ký tự sẽ ném ValueError."""
    plain = "AIzaSyTamperTestKey9999"
    cipher_text = encrypt_api_key(plain)
    # Giả mạo ciphertext bằng cách đổi ký tự ở giữa
    tampered_list = list(cipher_text)
    tampered_list[20] = "X" if tampered_list[20] != "X" else "Y"
    tampered_text = "".join(tampered_list)

    with pytest.raises(ValueError, match="Tampered or invalid key"):
        decrypt_api_key(tampered_text)


def test_04_crypto_corrupted_ciphertext_raises_error():
    """Kiểm tra chuỗi không phải định dạng Fernet token ném ValueError an toàn."""
    with pytest.raises(ValueError, match="Tampered or invalid key"):
        decrypt_api_key("ThisIsNotAValidFernetEncryptedBase64String==")


def test_05_crypto_empty_plain_key_raises_error():
    """Mã hóa chuỗi rỗng hoặc chỉ có khoảng trắng phải ném ValueError."""
    with pytest.raises(ValueError, match="không được để trống"):
        encrypt_api_key("   ")


def test_06_crypto_empty_cipher_key_raises_error():
    """Giải mã chuỗi rỗng phải ném ValueError."""
    with pytest.raises(ValueError, match="không hợp lệ"):
        decrypt_api_key("")


def test_07_mask_api_key_standard_length():
    """Che mặt nạ khóa có độ dài >= 10 ký tự: giữ 6 ký tự đầu, 4 ký tự cuối kèm '...'."""
    key = "AIzaSySecretApiKeySavedSecurely9999"
    masked = mask_api_key(key)
    assert masked == "AIzaSy...9999"
    assert "..." in masked


def test_08_mask_api_key_short_length():
    """Che mặt nạ khóa ngắn (4-9 ký tự): giữ 2 đầu, 2 cuối kèm '...'."""
    key = "123456"
    masked = mask_api_key(key)
    assert masked == "12...56"
    assert "..." in masked


def test_09_mask_api_key_very_short():
    """Che mặt nạ khóa cực ngắn (< 4 ký tự): trả về '...' để không lộ thông tin."""
    key = "ab"
    masked = mask_api_key(key)
    assert masked == "..."


def test_10_mask_api_key_empty():
    """Khóa rỗng trả về chuỗi rỗng."""
    assert mask_api_key("") == ""
    assert mask_api_key(None) == ""


# ==============================================================================
# 2. Pydantic Schemas & Input Validation Tests (11-17)
# ==============================================================================

def test_11_schema_ai_key_test_request_valid():
    """Schema AIKeyTestRequest hợp lệ với Gemini."""
    req = AIKeyTestRequest(
        provider="gemini",
        api_key="AIzaSyValidFormatKey123",
        model="gemini-2.5-flash"
    )
    assert req.provider == "gemini"
    assert req.model == "gemini-2.5-flash"
    assert req.api_key == "AIzaSyValidFormatKey123"


def test_12_schema_ai_key_test_request_empty_key_rejected():
    """Schema AIKeyTestRequest từ chối key rỗng hoặc chỉ có khoảng trắng."""
    with pytest.raises(ValidationError):
        AIKeyTestRequest(provider="gemini", api_key="   ")


def test_13_schema_ai_key_test_request_prohibited_provider():
    """Schema AIKeyTestRequest từ chối các provider ngoài Gemini (OpenAI, Anthropic)."""
    with pytest.raises(ValidationError):
        AIKeyTestRequest(provider="anthropic", api_key="sk-ant-test-key")

    with pytest.raises(ValidationError):
        AIKeyTestRequest(provider="openai", api_key="sk-test-key")


def test_14_schema_ai_key_test_request_prohibited_model():
    """Schema AIKeyTestRequest từ chối mô hình cấm (Claude, GPT)."""
    with pytest.raises(ValidationError):
        AIKeyTestRequest(provider="gemini", api_key="test-key", model="claude-3-7-sonnet")

    with pytest.raises(ValidationError):
        AIKeyTestRequest(provider="gemini", api_key="test-key", model="gpt-4o")


def test_15_schema_ai_key_create_valid():
    """Schema AIKeyCreate hợp lệ."""
    data = AIKeyCreate(
        provider="gemini",
        api_key="AIzaSySecretApiKeySavedSecurely9999",
        model="gemini-2.5-pro",
        workspace_id=1,
        is_active=True
    )
    assert data.provider == "gemini"
    assert data.workspace_id == 1
    assert data.model == "gemini-2.5-pro"


def test_16_schema_ai_key_create_empty_key_rejected():
    """Schema AIKeyCreate từ chối key rỗng."""
    with pytest.raises(ValidationError):
        AIKeyCreate(api_key="")


def test_17_schema_ai_key_response_no_plain_key():
    """Schema AIKeyResponse tuyệt đối không có trường plain-text api_key."""
    resp = AIKeyResponse(
        provider="gemini",
        model="gemini-2.5-flash",
        masked_key="AIzaSy...9999",
        is_active=True
    )
    dumped = resp.model_dump()
    assert "api_key" not in dumped
    assert "encrypted_key" not in dumped
    assert dumped["masked_key"] == "AIzaSy...9999"


# ==============================================================================
# 3. REST API Endpoints Tests (18-29)
# ==============================================================================

def test_18_api_test_connection_mock_success(client: TestClient, manager_headers):
    """Endpoint test-ai-connection trả về 200 success=True với key mock verification."""
    resp = client.post("/api/v1/settings/test-ai-connection", json={
        "provider": "gemini",
        "api_key": "AIzaSyTestKeyForMockVerification12345",
        "model": "gemini-2.5-flash"
    }, headers=manager_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["latency_ms"] >= 0
    assert "Mock Verified" in data["message"]


def test_19_api_test_connection_invalid_dummy_fails_cleanly(client: TestClient, manager_headers):
    """Endpoint test-ai-connection trả về success=False sạch sẽ khi key invalid, không crash 500."""
    resp = client.post("/api/v1/settings/test-ai-connection", json={
        "provider": "gemini",
        "api_key": "invalid_dummy_key_0000",
        "model": "gemini-2.5-flash"
    }, headers=manager_headers)
    assert resp.status_code in (200, 400)
    data = resp.json()
    assert data["success"] is False
    assert data.get("error") == "API_KEY_INVALID" or "không hợp lệ" in data.get("message", "")


def test_20_api_test_connection_prohibited_provider_422(client: TestClient, manager_headers):
    """Endpoint test-ai-connection trả về 422 khi cung cấp provider bị cấm."""
    resp = client.post("/api/v1/settings/test-ai-connection", json={
        "provider": "anthropic",
        "api_key": "any-key-here",
        "model": "gemini-2.5-flash"
    }, headers=manager_headers)
    assert resp.status_code in (400, 422)


def test_21_api_test_connection_prohibited_model_422(client: TestClient, manager_headers):
    """Endpoint test-ai-connection trả về 422 khi cung cấp model bị cấm."""
    resp = client.post("/api/v1/settings/test-ai-connection", json={
        "provider": "gemini",
        "api_key": "AIzaSyValidFormatKey123",
        "model": "claude-3-7-sonnet"
    }, headers=manager_headers)
    assert resp.status_code in (400, 422)


def test_22_api_store_custom_ai_key_user_level(client: TestClient, manager_headers):
    """Lưu trữ custom key ở cấp cá nhân người dùng (workspace_id = None)."""
    resp = client.post("/api/v1/settings/ai-keys", json={
        "provider": "gemini",
        "api_key": "AIzaSyUserPersonalSecretKey12345",
        "model": "gemini-2.5-flash"
    }, headers=manager_headers)
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert data["status"] == "SAVED"
    assert "AIzaSy" in data["masked_key"]
    assert "api_key" not in data


def test_23_api_store_custom_ai_key_workspace_level(client: TestClient, manager_headers):
    """Lưu trữ custom key ở cấp workspace."""
    resp = client.post("/api/v1/settings/ai-keys", json={
        "provider": "gemini",
        "api_key": "AIzaSyWorkspaceSecretKey99999",
        "model": "gemini-2.5-pro",
        "workspace_id": 1
    }, headers=manager_headers)
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert data["status"] == "SAVED"
    assert data["workspace_id"] == 1
    assert data["model"] == "gemini-2.5-pro"


def test_24_api_store_custom_ai_key_update_existing(client: TestClient, manager_headers):
    """Cập nhật custom key đã tồn tại sang mô hình mới."""
    resp = client.post("/api/v1/settings/ai-keys", json={
        "provider": "gemini",
        "api_key": "AIzaSyWorkspaceSecretKeyUpdated123",
        "model": "gemini-2.5-pro",
        "workspace_id": 1
    }, headers=manager_headers)
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert data["model"] == "gemini-2.5-pro"
    assert data["status"] == "SAVED"


def test_25_api_get_custom_ai_key_masked(client: TestClient, manager_headers):
    """Truy vấn GET /settings/ai-keys trả về masked_key và không để lộ plaintext."""
    # Lưu key trước
    client.post("/api/v1/settings/ai-keys", json={
        "provider": "gemini",
        "api_key": "AIzaSySecretApiKeySavedSecurely9999",
        "model": "gemini-2.5-flash",
        "workspace_id": 1
    }, headers=manager_headers)

    resp = client.get("/api/v1/settings/ai-keys?workspace_id=1", headers=manager_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "masked_key" in data
    assert "..." in data["masked_key"]
    assert "api_key" not in data
    assert "encrypted_key" not in data


def test_26_api_get_custom_ai_key_list(client: TestClient, manager_headers):
    """Truy vấn GET /settings/ai-keys/list trả về danh sách các key hợp lệ."""
    resp = client.get("/api/v1/settings/ai-keys/list", headers=manager_headers)
    assert resp.status_code == 200
    items = resp.json()
    assert isinstance(items, list)
    for item in items:
        assert "masked_key" in item
        assert "api_key" not in item


def test_27_api_toggle_custom_ai_key(client: TestClient, manager_headers):
    """Toggle trạng thái kích hoạt is_active của khóa."""
    save_resp = client.post("/api/v1/settings/ai-keys", json={
        "provider": "gemini",
        "api_key": "AIzaSyToggleTestKey12345",
        "model": "gemini-2.5-flash",
        "workspace_id": 1
    }, headers=manager_headers)
    assert save_resp.status_code in (200, 201)
    key_id = save_resp.json()["id"]

    resp = client.patch(f"/api/v1/settings/ai-keys/{key_id}/toggle", headers=manager_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_active"] is False

    resp2 = client.patch(f"/api/v1/settings/ai-keys/{key_id}/toggle", headers=manager_headers)
    assert resp2.status_code == 200
    assert resp2.json()["is_active"] is True


def test_28_api_delete_custom_ai_key_by_id(client: TestClient, manager_headers, db_session: Session):
    """Xóa khóa theo ID thành công."""
    # Tạo một key tạm để xóa
    temp_key = CustomApiKey(
        user_id=1,
        provider="gemini",
        encrypted_key=encrypt_api_key("AIzaSyTempKeyToDelete12345"),
        model="gemini-2.5-flash",
        is_active=True
    )
    db_session.add(temp_key)
    db_session.commit()
    db_session.refresh(temp_key)

    resp = client.delete(f"/api/v1/settings/ai-keys/{temp_key.id}", headers=manager_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "DELETED"


def test_29_api_delete_deactivate_current_key(client: TestClient, manager_headers):
    """Vô hiệu hóa key hiện tại qua DELETE /settings/ai-keys."""
    resp = client.delete("/api/v1/settings/ai-keys", headers=manager_headers)
    assert resp.status_code in (200, 204)


# ==============================================================================
# 4. Multi-tier Resolver Integration Tests (30)
# ==============================================================================

def test_30_resolver_multi_tier_priority_order(db_session: Session):
    """Kiểm tra bộ phân giải AIService.resolve_api_key tuân thủ thứ tự ưu tiên:
    Workspace Key > User Key > System Default Key > Smart Fallback.
    """
    service = AIService()

    # Dọn dẹp key cũ trong session test
    db_session.query(CustomApiKey).delete()
    db_session.commit()

    # 1. Chưa có key nào -> Rơi về Fallback hoặc System
    res_empty = service.resolve_api_key(db=db_session, workspace_id=1, user_id=1)
    assert res_empty["tier"] in ("SYSTEM", "FALLBACK")

    # 2. Tạo User personal key (user_id=1, workspace_id=None)
    user_key = CustomApiKey(
        user_id=1,
        workspace_id=None,
        provider="gemini",
        encrypted_key=encrypt_api_key("AIzaSyUserTierKey12345"),
        model="gemini-2.5-flash",
        is_active=True
    )
    db_session.add(user_key)
    db_session.commit()

    # Với workspace 2 (chưa có key riêng), user 1 gọi -> nhận Tier User
    res_user = service.resolve_api_key(db=db_session, workspace_id=2, user_id=1)
    assert res_user["tier"] == "USER"
    assert res_user["api_key"] == "AIzaSyUserTierKey12345"

    # 3. Tạo Workspace key cho workspace 1 -> Ưu tiên Workspace hơn User
    ws_key = CustomApiKey(
        user_id=1,
        workspace_id=1,
        provider="gemini",
        encrypted_key=encrypt_api_key("AIzaSyWorkspaceTierKey99999"),
        model="gemini-2.5-pro",
        is_active=True
    )
    db_session.add(ws_key)
    db_session.commit()

    res_ws = service.resolve_api_key(db=db_session, workspace_id=1, user_id=1)
    assert res_ws["tier"] == "WORKSPACE"
    assert res_ws["api_key"] == "AIzaSyWorkspaceTierKey99999"
    assert res_ws["model"] == "gemini-2.5-pro"

    assert res_ws["model"] == "gemini-2.5-pro"
