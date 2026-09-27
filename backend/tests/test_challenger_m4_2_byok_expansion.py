"""
Challenger 2 Empirical Verification Test Suite: Milestone M4
Focus: BYOK Multi-Provider Expansion (Gemini, OpenRouter, OpenAI)
- Schema validation (Valid/Invalid combinations, Mismatched models, Unknown providers)
- Multi-tier Resolver hierarchy & Multi-provider independence
- Settings test connection endpoint with mock tokens & invalid dummy tokens & error sanitization
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from pydantic import ValidationError

from app.schemas.schemas import AIKeyTestRequest, AIKeyCreate, AIKeyResponse
from app.services.ai.ai_service import AIService
from app.models.entities import CustomApiKey, Workspace, User
from app.core.crypto import encrypt_api_key
from app.core.config import settings


# ==============================================================================
# SECTION 1: EMPIRICAL SCHEMA VALIDATION TESTS
# ==============================================================================

class TestBYOKSchemaValidationChallenger:
    """Stress tests schema validation for AIKeyTestRequest and AIKeyCreate."""

    def test_valid_provider_and_model_combinations(self):
        """Test valid combinations specified in requirements:
        - gemini with gemini-1.5-flash
        - openrouter with meta-llama/llama-3.3-70b-instruct:free
        - openai with gpt-4o
        """
        # 1. Gemini + gemini-1.5-flash
        req_gemini_test = AIKeyTestRequest(
            provider="gemini",
            api_key="AIzaSyValidGeminiKeyTest123",
            model="gemini-1.5-flash"
        )
        assert req_gemini_test.provider == "gemini"
        assert req_gemini_test.model == "gemini-1.5-flash"

        req_gemini_create = AIKeyCreate(
            provider="gemini",
            api_key="AIzaSyValidGeminiKeyTest123",
            model="gemini-1.5-flash",
            is_active=True
        )
        assert req_gemini_create.provider == "gemini"
        assert req_gemini_create.model == "gemini-1.5-flash"

        # 2. OpenRouter + meta-llama/llama-3.3-70b-instruct:free
        req_or_test = AIKeyTestRequest(
            provider="openrouter",
            api_key="sk-or-v1-valid-openrouter-key",
            model="meta-llama/llama-3.3-70b-instruct:free"
        )
        assert req_or_test.provider == "openrouter"
        assert req_or_test.model == "meta-llama/llama-3.3-70b-instruct:free"

        req_or_create = AIKeyCreate(
            provider="openrouter",
            api_key="sk-or-v1-valid-openrouter-key",
            model="meta-llama/llama-3.3-70b-instruct:free",
            is_active=True
        )
        assert req_or_create.provider == "openrouter"
        assert req_or_create.model == "meta-llama/llama-3.3-70b-instruct:free"

        # 3. OpenAI + gpt-4o
        req_oa_test = AIKeyTestRequest(
            provider="openai",
            api_key="sk-proj-valid-openai-key-abc",
            model="gpt-4o"
        )
        assert req_oa_test.provider == "openai"
        assert req_oa_test.model == "gpt-4o"

        req_oa_create = AIKeyCreate(
            provider="openai",
            api_key="sk-proj-valid-openai-key-abc",
            model="gpt-4o",
            is_active=True
        )
        assert req_oa_create.provider == "openai"
        assert req_oa_create.model == "gpt-4o"

    def test_invalid_mismatched_provider_and_model(self):
        """Stress test: mismatched provider and model must raise ValidationError:
        - openai with gemini-1.5-flash
        - gemini with gpt-4o
        - openrouter without author/model format
        """
        # OpenAI with gemini model
        with pytest.raises(ValidationError) as exc_info:
            AIKeyTestRequest(
                provider="openai",
                api_key="sk-proj-valid-key",
                model="gemini-1.5-flash"
            )
        assert "OpenAI" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            AIKeyCreate(
                provider="openai",
                api_key="sk-proj-valid-key",
                model="gemini-1.5-flash"
            )
        assert "OpenAI" in str(exc_info.value)

        # Gemini with OpenAI model
        with pytest.raises(ValidationError) as exc_info:
            AIKeyTestRequest(
                provider="gemini",
                api_key="AIzaSyValidGeminiKey",
                model="gpt-4o"
            )
        assert "Gemini" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            AIKeyCreate(
                provider="gemini",
                api_key="AIzaSyValidGeminiKey",
                model="gpt-4o"
            )
        assert "Gemini" in str(exc_info.value)

        # OpenRouter with single word (no author/model format)
        with pytest.raises(ValidationError) as exc_info:
            AIKeyTestRequest(
                provider="openrouter",
                api_key="sk-or-valid-key",
                model="llama-3-70b"
            )
        assert "OpenRouter" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            AIKeyCreate(
                provider="openrouter",
                api_key="sk-or-valid-key",
                model="llama-3-70b"
            )
        assert "OpenRouter" in str(exc_info.value)

    def test_invalid_unknown_provider(self):
        """Stress test: unknown or prohibited provider must be rejected."""
        unsupported = ["unknown", "anthropic", "bedrock", "cohere", "mistral_direct", "aws"]
        for bad_prov in unsupported:
            with pytest.raises(ValidationError) as exc_info:
                AIKeyTestRequest(provider=bad_prov, api_key="sk-test-key-123", model="gpt-4o")
            assert "không được hỗ trợ" in str(exc_info.value)

            with pytest.raises(ValidationError) as exc_info:
                AIKeyCreate(provider=bad_prov, api_key="sk-test-key-123", model="gpt-4o")
            assert "không được hỗ trợ" in str(exc_info.value)

    def test_empty_or_whitespace_api_key_rejected(self):
        """Stress test: empty or whitespace-only API keys must be rejected."""
        empty_keys = ["", "   ", "\t\n", None]
        for empty_key in empty_keys:
            with pytest.raises(ValidationError):
                AIKeyTestRequest(provider="gemini", api_key=empty_key, model="gemini-1.5-flash")

            with pytest.raises(ValidationError):
                AIKeyCreate(provider="gemini", api_key=empty_key, model="gemini-1.5-flash")


# ==============================================================================
# SECTION 2: RESOLVER HIERARCHY & MULTI-PROVIDER INDEPENDENCE
# ==============================================================================

class TestBYOKResolverHierarchyChallenger:
    """Stress tests multi-tier resolution logic across providers independently."""

    def test_multi_provider_independent_resolution(self, db_session: Session):
        """Test that Gemini, OpenRouter, and OpenAI keys resolve independently
        without any cross-provider interference or state collision.
        """
        service = AIService()
        # Clean any preexisting keys in test session
        db_session.query(CustomApiKey).delete()
        db_session.commit()

        user = db_session.query(User).filter(User.id == 1).first()
        assert user is not None

        # Tier 1: Workspace Key for OpenRouter
        ws_or_key = CustomApiKey(
            user_id=user.id,
            workspace_id=1,
            provider="openrouter",
            encrypted_key=encrypt_api_key("sk-or-v1-ws-key-secret-123"),
            model="meta-llama/llama-3.3-70b-instruct:free",
            is_active=True
        )

        # Tier 2: User Personal Key for OpenAI
        user_oa_key = CustomApiKey(
            user_id=user.id,
            workspace_id=None,
            provider="openai",
            encrypted_key=encrypt_api_key("sk-proj-user-openai-secret-456"),
            model="gpt-4o",
            is_active=True
        )

        db_session.add_all([ws_or_key, user_oa_key])
        db_session.commit()

        # 1. Resolve OpenRouter: Should pick Tier WORKSPACE
        res_or = service.resolve_api_key(db_session, workspace_id=1, user_id=user.id, provider="openrouter")
        assert res_or["tier"] == "WORKSPACE"
        assert res_or["api_key"] == "sk-or-v1-ws-key-secret-123"
        assert res_or["provider"] == "openrouter"
        assert res_or["model"] == "meta-llama/llama-3.3-70b-instruct:free"

        # 2. Resolve OpenAI: Should pick Tier USER (no workspace key exists for openai)
        res_oa = service.resolve_api_key(db_session, workspace_id=1, user_id=user.id, provider="openai")
        assert res_oa["tier"] == "USER"
        assert res_oa["api_key"] == "sk-proj-user-openai-secret-456"
        assert res_oa["provider"] == "openai"
        assert res_oa["model"] == "gpt-4o"

        # 3. Resolve Gemini: Neither workspace nor user has key -> SYSTEM or FALLBACK
        res_gemini = service.resolve_api_key(db_session, workspace_id=1, user_id=user.id, provider="gemini")
        assert res_gemini["tier"] in ("SYSTEM", "FALLBACK")
        assert res_gemini["provider"] in ("gemini", "template-fallback-engine")

    def test_workspace_over_user_hierarchy_precedence(self, db_session: Session):
        """Test resolver precedence when BOTH Workspace Key and User Key exist for the SAME provider."""
        service = AIService()
        db_session.query(CustomApiKey).delete()
        db_session.commit()

        # Both keys exist for OpenAI
        ws_key = CustomApiKey(
            user_id=1,
            workspace_id=1,
            provider="openai",
            encrypted_key=encrypt_api_key("sk-ws-openai-override-key"),
            model="gpt-4o",
            is_active=True
        )
        user_key = CustomApiKey(
            user_id=1,
            workspace_id=None,
            provider="openai",
            encrypted_key=encrypt_api_key("sk-user-openai-personal-key"),
            model="gpt-4o-mini",
            is_active=True
        )
        db_session.add_all([ws_key, user_key])
        db_session.commit()

        # In workspace 1: Workspace key takes precedence over user key
        res_ws = service.resolve_api_key(db_session, workspace_id=1, user_id=1, provider="openai")
        assert res_ws["tier"] == "WORKSPACE"
        assert res_ws["api_key"] == "sk-ws-openai-override-key"

        # Outside workspace 1 (e.g. workspace_id=None or workspace 2 where no ws key exists): User key is used
        res_user = service.resolve_api_key(db_session, workspace_id=2, user_id=1, provider="openai")
        assert res_user["tier"] == "USER"
        assert res_user["api_key"] == "sk-user-openai-personal-key"

    def test_inactive_key_failover(self, db_session: Session):
        """Test failover when Workspace Key is deactivated (is_active=False).
        It must automatically fall back to User Key.
        """
        service = AIService()
        db_session.query(CustomApiKey).delete()
        db_session.commit()

        ws_key_inactive = CustomApiKey(
            user_id=1,
            workspace_id=1,
            provider="openrouter",
            encrypted_key=encrypt_api_key("sk-or-ws-inactive-key"),
            model="meta-llama/llama-3.3-70b-instruct",
            is_active=False  # Inactive
        )
        user_key_active = CustomApiKey(
            user_id=1,
            workspace_id=None,
            provider="openrouter",
            encrypted_key=encrypt_api_key("sk-or-user-active-key"),
            model="meta-llama/llama-3.3-70b-instruct:free",
            is_active=True
        )
        db_session.add_all([ws_key_inactive, user_key_active])
        db_session.commit()

        res = service.resolve_api_key(db_session, workspace_id=1, user_id=1, provider="openrouter")
        assert res["tier"] == "USER"
        assert res["api_key"] == "sk-or-user-active-key"

    def test_system_env_fallback_when_no_custom_keys(self, monkeypatch, db_session: Session):
        """Test system env fallback when neither Workspace nor User keys exist."""
        service = AIService()
        db_session.query(CustomApiKey).delete()
        db_session.commit()

        monkeypatch.setenv("OPENAI_API_KEY", "sk-proj-system-env-openai-key")
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-system-env-openrouter-key")

        res_oa = service.resolve_api_key(db_session, workspace_id=1, user_id=1, provider="openai")
        assert res_oa["tier"] == "SYSTEM"
        assert res_oa["api_key"] == "sk-proj-system-env-openai-key"

        res_or = service.resolve_api_key(db_session, workspace_id=1, user_id=1, provider="openrouter")
        assert res_or["tier"] == "SYSTEM"
        assert res_or["api_key"] == "sk-or-system-env-openrouter-key"


# ==============================================================================
# SECTION 3: TEST CONNECTION ENDPOINT EMPIRICAL VERIFICATION
# ==============================================================================

class TestBYOKConnectionEndpointChallenger:
    """Stress tests POST /api/v1/settings/test-ai-connection."""

    def test_mock_tokens_for_all_providers(self, client: TestClient, rbac_headers):
        """Verify mock tokens return success: True and HTTP 200 for all providers."""
        headers = rbac_headers["manager"]

        mock_payloads = [
            # Gemini
            {"provider": "gemini", "api_key": "AIzaSyMockKeyForGeminiTest", "model": "gemini-1.5-flash"},
            {"provider": "gemini", "api_key": "mock_gemini_token_test", "model": "gemini-1.5-flash"},
            # OpenRouter
            {"provider": "openrouter", "api_key": "sk-or-mock-openrouter-token", "model": "meta-llama/llama-3.3-70b-instruct:free"},
            {"provider": "openrouter", "api_key": "mock-openrouter-test-token", "model": "meta-llama/llama-3.3-70b-instruct:free"},
            # OpenAI
            {"provider": "openai", "api_key": "sk-mock-openai-token", "model": "gpt-4o"},
            {"provider": "openai", "api_key": "mock_openai_test_token", "model": "gpt-4o"},
        ]

        for p in mock_payloads:
            res = client.post("/api/v1/settings/test-ai-connection", json=p, headers=headers)
            assert res.status_code == 200, f"Failed for {p['provider']}: {res.text}"
            data = res.json()
            assert data["success"] is True, f"Expected success=True for {p['api_key']}"
            assert data["provider"] == p["provider"]
            assert data["model"] == p["model"]
            assert data["latency_ms"] >= 0
            assert "thành công" in data["message"].lower()

    def test_invalid_dummy_tokens_rejected(self, client: TestClient, rbac_headers):
        """Verify invalid dummy tokens return success: False with API_KEY_INVALID error."""
        headers = rbac_headers["manager"]

        invalid_payloads = [
            {"provider": "gemini", "api_key": "invalid_dummy_key_gemini", "model": "gemini-1.5-flash"},
            {"provider": "openrouter", "api_key": "invalid_dummy_key_openrouter", "model": "meta-llama/llama-3.3-70b-instruct:free"},
            {"provider": "openai", "api_key": "invalid_dummy_key_openai", "model": "gpt-4o"},
        ]

        for p in invalid_payloads:
            res = client.post("/api/v1/settings/test-ai-connection", json=p, headers=headers)
            assert res.status_code == 200
            data = res.json()
            assert data["success"] is False
            assert data["error"] == "API_KEY_INVALID"
            assert "không hợp lệ" in data["message"].lower()

    def test_mismatched_model_returns_422_unprocessable_entity(self, client: TestClient, rbac_headers):
        """Verify endpoint rejects mismatched provider and model at HTTP layer with 422."""
        headers = rbac_headers["manager"]

        mismatches = [
            {"provider": "openai", "api_key": "sk-mock-12345", "model": "gemini-1.5-flash"},
            {"provider": "gemini", "api_key": "AIzaSyMock12345", "model": "gpt-4o"},
            {"provider": "openrouter", "api_key": "sk-or-mock-12345", "model": "singlewordmodel"},
            {"provider": "unknown", "api_key": "sk-mock-12345", "model": "gpt-4o"},
        ]

        for p in mismatches:
            res = client.post("/api/v1/settings/test-ai-connection", json=p, headers=headers)
            assert res.status_code == 422, f"Expected 422 for {p}, got {res.status_code}: {res.text}"

    def test_unauthenticated_request_rejected(self, client: TestClient):
        """Verify that testing AI connection requires valid authentication."""
        res = client.post(
            "/api/v1/settings/test-ai-connection",
            json={"provider": "gemini", "api_key": "AIzaSyMockKey", "model": "gemini-1.5-flash"}
        )
        assert res.status_code == 401

    def test_error_sanitization_no_key_leakage(self, client: TestClient, rbac_headers, monkeypatch):
        """Stress test: when an external provider ping fails, the raw secret key must NEVER be leaked in response."""
        headers = rbac_headers["manager"]
        secret_key_canary = "sk-super-secret-canary-key-998877665544"

        # Mock httpx to simulate a provider error returning body with the canary key
        class MockResponse:
            status_code = 401
            text = f"Authentication failed for key {secret_key_canary}: unauthorized."

        class MockClient:
            def __init__(self, *args, **kwargs):
                pass
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def get(self, url, headers=None):
                return MockResponse()

        monkeypatch.setattr("httpx.Client", MockClient)

        res = client.post(
            "/api/v1/settings/test-ai-connection",
            json={"provider": "openai", "api_key": secret_key_canary, "model": "gpt-4o"},
            headers=headers
        )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is False
        # Canary key MUST NOT be present in message or error
        assert secret_key_canary not in str(data.get("message", ""))
        assert secret_key_canary not in str(data.get("error", ""))
        assert "[REDACTED_API_KEY]" in str(data.get("error", ""))
