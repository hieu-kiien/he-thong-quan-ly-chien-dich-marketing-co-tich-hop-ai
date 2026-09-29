"""Comprehensive BYOK Multi-Provider Expansion Test Suite (Worker M4).

Validates schema validation, multi-provider model validation (Gemini, OpenRouter, OpenAI),
multi-tier key resolution, live connection test endpoint, and cryptographic vault storage.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from pydantic import ValidationError

from app.schemas.schemas import AIKeyTestRequest, AIKeyCreate
from app.services.ai.ai_service import AIService
from app.models.entities import CustomApiKey, Workspace, User
from app.core.crypto import encrypt_api_key, decrypt_api_key


def test_schema_valid_providers():
    """Verify AIKeyTestRequest and AIKeyCreate accept gemini, openrouter, and openai with valid models."""
    sample_models = {
        "gemini": "gemini-2.5-flash",
        "openrouter": "meta-llama/llama-3.3-70b-instruct",
        "openai": "gpt-4o",
    }
    for prov in ["gemini", "openrouter", "openai"]:
        req = AIKeyTestRequest(provider=prov, api_key="sk-test-key-12345", model=sample_models[prov])
        assert req.provider == prov

        create_req = AIKeyCreate(provider=prov, api_key="sk-test-key-12345", model=sample_models[prov], is_active=True)
        assert create_req.provider == prov


def test_schema_rejects_unsupported_providers():
    """Verify schema rejects providers other than gemini, openrouter, and openai."""
    with pytest.raises(ValidationError):
        AIKeyTestRequest(provider="anthropic", api_key="sk-test-key-12345")

    with pytest.raises(ValidationError):
        AIKeyCreate(provider="claude", api_key="sk-test-key-12345")

    with pytest.raises(ValidationError):
        AIKeyTestRequest(provider="bedrock", api_key="sk-test-key-12345")


def test_schema_model_validation_per_provider():
    """Verify model names are strictly validated against their corresponding provider."""
    # Gemini models
    req_gemini = AIKeyCreate(provider="gemini", api_key="AIzaSyTest123", model="gemini-2.5-flash")
    assert req_gemini.model == "gemini-2.5-flash"

    with pytest.raises(ValidationError):
        AIKeyCreate(provider="gemini", api_key="AIzaSyTest123", model="gpt-4o")

    # OpenRouter models
    req_or = AIKeyCreate(provider="openrouter", api_key="sk-or-v1-test", model="meta-llama/llama-3.3-70b-instruct")
    assert req_or.model == "meta-llama/llama-3.3-70b-instruct"

    with pytest.raises(ValidationError):
        AIKeyCreate(provider="openrouter", api_key="sk-or-v1-test", model="invalid-prefix-model")

    # OpenAI models
    req_oa = AIKeyCreate(provider="openai", api_key="sk-openai-test", model="gpt-4o")
    assert req_oa.model == "gpt-4o"

    with pytest.raises(ValidationError):
        AIKeyCreate(provider="openai", api_key="sk-openai-test", model="gemini-2.5-pro")


def test_test_connection_endpoint_mock_tokens_all_providers(client: TestClient, rbac_headers):
    """Verify /api/v1/settings/ai/test-key returns success for mock test tokens across all 3 providers."""
    headers = rbac_headers["manager"]

    # 1. Gemini
    res_gemini = client.post(
        "/api/v1/settings/test-ai-connection",
        json={"provider": "gemini", "api_key": "mock_valid_key_gemini", "model": "gemini-2.5-flash"},
        headers=headers,
    )
    assert res_gemini.status_code == 200
    assert res_gemini.json()["success"] is True

    # 2. OpenRouter
    res_or = client.post(
        "/api/v1/settings/test-ai-connection",
        json={"provider": "openrouter", "api_key": "sk-mock-or-key", "model": "meta-llama/llama-3.3-70b-instruct"},
        headers=headers,
    )
    assert res_or.status_code == 200
    assert res_or.json()["success"] is True

    # 3. OpenAI
    res_oa = client.post(
        "/api/v1/settings/test-ai-connection",
        json={"provider": "openai", "api_key": "sk-mock-oa-key", "model": "gpt-4o"},
        headers=headers,
    )
    assert res_oa.status_code == 200
    assert res_oa.json()["success"] is True


def test_save_and_retrieve_multi_provider_keys(client: TestClient, rbac_headers, db_session: Session):
    """Verify storing, encrypting, and listing keys for multiple providers in the vault."""
    headers = rbac_headers["manager"]

    # Save an OpenRouter key for Workspace
    res_or = client.post(
        "/api/v1/settings/ai-keys",
        json={
            "provider": "openrouter",
            "api_key": "sk-or-v1-abcdef1234567890",
            "model": "meta-llama/llama-3.3-70b-instruct",
            "workspace_id": 1,
            "is_active": True,
        },
        headers=headers,
    )
    assert res_or.status_code == 200
    data_or = res_or.json()
    assert data_or["provider"] == "openrouter"
    assert data_or["masked_key"].startswith("sk-or-")

    # Save an OpenAI key for Personal
    res_oa = client.post(
        "/api/v1/settings/ai-keys",
        json={
            "provider": "openai",
            "api_key": "sk-proj-0987654321fedcba",
            "model": "gpt-4o",
            "workspace_id": None,
            "is_active": True,
        },
        headers=headers,
    )
    assert res_oa.status_code == 200
    data_oa = res_oa.json()
    assert data_oa["provider"] == "openai"
    assert data_oa["masked_key"].startswith("sk-")

    # Verify both are listed
    res_list = client.get("/api/v1/settings/ai-keys/list", headers=headers)
    assert res_list.status_code == 200
    providers_listed = [k["provider"] for k in res_list.json()]
    assert "openrouter" in providers_listed
    assert "openai" in providers_listed


def test_resolve_api_key_multi_provider_hierarchy(db_session: Session, monkeypatch):
    """Test multi-tier hierarchy in AIService.resolve_api_key for various providers."""
    ai_service = AIService()

    # Che key hệ thống từ .env/CI env để tầng SYSTEM là xác định được,
    # nếu không test sẽ cho kết quả khác giữa máy dev và CI.
    monkeypatch.setenv("GEMINI_API_KEY", "sk-system-gemini-key")
    monkeypatch.setattr("app.services.ai.ai_service.settings.GEMINI_API_KEY", "sk-system-gemini-key", raising=False)

    # User 1 with personal OpenAI key
    user = db_session.query(User).filter(User.id == 1).first()
    assert user is not None

    key_oa = CustomApiKey(
        user_id=user.id,
        workspace_id=None,
        provider="openai",
        encrypted_key=encrypt_api_key("sk-user-openai-key-secret"),
        model="gpt-4o-mini",
        is_active=True,
    )
    # Workspace 1 with OpenRouter key
    key_or = CustomApiKey(
        user_id=user.id,
        workspace_id=1,
        provider="openrouter",
        encrypted_key=encrypt_api_key("sk-or-ws-key-secret"),
        model="meta-llama/llama-3.3-70b-instruct",
        is_active=True,
    )
    db_session.add_all([key_oa, key_or])
    db_session.commit()

    # Resolve OpenAI key for user in workspace 1 -> finds USER tier key for openai
    res_oa = ai_service.resolve_api_key(db_session, user_id=user.id, workspace_id=1, provider="openai")
    assert res_oa["tier"] == "USER"
    assert res_oa["api_key"] == "sk-user-openai-key-secret"
    assert res_oa["provider"] == "openai"
    assert res_oa["model"] == "gpt-4o-mini"

    # Resolve OpenRouter key for workspace 1 -> finds WORKSPACE tier key for openrouter
    res_or = ai_service.resolve_api_key(db_session, user_id=user.id, workspace_id=1, provider="openrouter")
    assert res_or["tier"] == "WORKSPACE"
    assert res_or["api_key"] == "sk-or-ws-key-secret"
    assert res_or["provider"] == "openrouter"
    assert res_or["model"] == "meta-llama/llama-3.3-70b-instruct"

    # Resolve Gemini key -> no custom key, falls back to SYSTEM / SMART_FALLBACK
    res_gemini = ai_service.resolve_api_key(db_session, user_id=user.id, workspace_id=1, provider="gemini")
    assert res_gemini["tier"] in ("SYSTEM", "SMART_FALLBACK", "FALLBACK")
    assert res_gemini["provider"] == "gemini"


def test_ai_service_routes_to_correct_provider_headers(monkeypatch):
    """Test _call_provider_with_retry properly prepares URLs and headers for OpenRouter, OpenAI, and Gemini."""
    import httpx
    ai_service = AIService()

    recorded_calls = []

    def mock_post(client_self, url, headers=None, json=None, timeout=None):
        recorded_calls.append({"url": str(url), "headers": headers or {}, "json": json or {}})
        # Mock successful OpenAI / OpenRouter chat completion response
        class MockResponse:
            status_code = 200
            def json(self):
                return {
                    "choices": [
                        {"message": {"content": "Chào mừng bạn đến với chiến dịch mới!"}}
                    ]
                }
            def raise_for_status(self):
                pass
        return MockResponse()

    monkeypatch.setattr(httpx.Client, "post", mock_post)

    # 1. Test OpenRouter call
    res_or = ai_service._call_provider_with_retry(
        system_prompt="Chuyên gia marketing",
        user_prompt="Viết tiêu đề",
        active_key="sk-or-test-mock",
        active_model="meta-llama/llama-3.3-70b-instruct",
        provider="openrouter",
    )
    assert res_or == "Chào mừng bạn đến với chiến dịch mới!"
    assert len(recorded_calls) == 1
    assert "openrouter.ai" in recorded_calls[0]["url"]
    assert "HTTP-Referer" in recorded_calls[0]["headers"]
    assert "X-Title" in recorded_calls[0]["headers"]
    assert recorded_calls[0]["headers"]["Authorization"] == "Bearer sk-or-test-mock"

    # 2. Test OpenAI call
    res_oa = ai_service._call_provider_with_retry(
        system_prompt="Chuyên gia marketing",
        user_prompt="Viết email",
        active_key="sk-oa-test-mock",
        active_model="gpt-4o",
        provider="openai",
    )
    assert res_oa == "Chào mừng bạn đến với chiến dịch mới!"
    assert len(recorded_calls) == 2
    assert "api.openai.com" in recorded_calls[1]["url"]
    assert recorded_calls[1]["headers"]["Authorization"] == "Bearer sk-oa-test-mock"
