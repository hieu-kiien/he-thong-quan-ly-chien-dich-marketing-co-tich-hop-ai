"""
Unit tests for Wave 5 Credential and Secret Sanitization in logs, API responses, and exception messages.
Verifies that no raw Gemini API keys, ?key=... query parameters, or Bearer tokens leak into:
1. Settings API /test-ai-connection error responses and messages.
2. AI Service execution logs, warnings, and raised exceptions.
"""

import pytest
from unittest.mock import patch, MagicMock
import httpx
from fastapi.testclient import TestClient

from app.api.v1.settings import sanitize_error_text
from app.services.ai.ai_service import _sanitize_ai_error, AIService


class TestWave5CredentialSanitization:
    """Test suite for credential sanitization routines."""

    def test_sanitize_error_text_removes_query_param(self):
        raw = "Error requesting https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash?key=AIzaSyD-SecretKey1234567890abcdef"
        sanitized = sanitize_error_text(raw)
        assert "AIzaSyD-SecretKey1234567890abcdef" not in sanitized
        assert "key=[REDACTED]" in sanitized

    def test_sanitize_error_text_removes_raw_gemini_key(self):
        raw = "Failed to authenticate with key AIzaSyD-SecretKey1234567890abcdef in Google API"
        sanitized = sanitize_error_text(raw)
        assert "AIzaSyD-SecretKey1234567890abcdef" not in sanitized
        assert "[REDACTED_GEMINI_KEY]" in sanitized

    def test_sanitize_error_text_removes_explicit_secret_key(self):
        secret = "custom-super-secret-key-token-999"
        raw = f"Invalid response from server for key {secret}: 401 Unauthorized"
        sanitized = sanitize_error_text(raw, secret_key=secret)
        assert secret not in sanitized
        assert "[REDACTED_API_KEY]" in sanitized

    def test_sanitize_error_text_removes_bearer_token(self):
        raw = "Header Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.secret"
        sanitized = sanitize_error_text(raw)
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in sanitized
        assert "Bearer [REDACTED]" in sanitized

    def test_sanitize_error_text_handles_none_and_empty(self):
        assert sanitize_error_text(None) == ""
        assert sanitize_error_text("") == ""

    def test_ai_service_sanitize_error_removes_secrets(self):
        raw = "httpx.ConnectError: [Errno -2] Name or service not known while requesting 'https://generativelanguage.googleapis.com/v1beta/models/gemini-pro?key=AIzaSyC_test_raw_key_123456789012345'"
        active_key = "AIzaSyC_test_raw_key_123456789012345"
        sanitized = _sanitize_ai_error(raw, active_key=active_key)
        assert active_key not in sanitized
        assert "key=[REDACTED]" in sanitized

    def test_test_ai_connection_sanitizes_exception_error(self, client: TestClient, manager_headers: dict):
        sensitive_key = "AIzaSy_Secret_Leaking_Key_9876543210"
        with patch("httpx.Client.get") as mock_get:
            # Simulate httpx throwing an exception that includes the request URL with the secret key
            mock_get.side_effect = httpx.ConnectError(
                f"Connection failed to https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash?key={sensitive_key}"
            )
            resp = client.post(
                "/api/v1/settings/test-ai-connection",
                headers=manager_headers,
                json={
                    "provider": "gemini",
                    "model": "gemini-2.5-flash",
                    "api_key": sensitive_key
                }
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is False
            assert sensitive_key not in data["error"]
            assert sensitive_key not in data["message"]
            assert "[REDACTED" in data["error"] or "key=[REDACTED]" in data["error"]

    def test_test_ai_connection_sanitizes_response_body_error(self, client: TestClient, manager_headers: dict):
        sensitive_key = "AIzaSy_Secret_In_Body_Key_1234567890"
        with patch("httpx.Client.get") as mock_get:
            # Simulate Google Gemini returning a 400 error body containing the key
            mock_resp = MagicMock()
            mock_resp.status_code = 400
            mock_resp.text = f'{{"error": {{"message": "API key not valid: {sensitive_key}", "status": "INVALID_ARGUMENT"}}}}'
            mock_get.return_value = mock_resp

            resp = client.post(
                "/api/v1/settings/test-ai-connection",
                headers=manager_headers,
                json={
                    "provider": "gemini",
                    "model": "gemini-2.5-flash",
                    "api_key": sensitive_key
                }
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is False
            assert sensitive_key not in data["error"]
            assert "[REDACTED" in data["error"]

    def test_ai_service_execute_task_sanitizes_fallback_warnings(self, db_session):
        service = AIService()
        service.fallback_enabled = True
        sensitive_key = "AIzaSy_Sensitive_AI_Service_Key_456"

        with patch.object(service, "_call_provider_with_retry") as mock_call:
            mock_call.side_effect = RuntimeError(
                f"Provider failed connecting to https://generativelanguage.googleapis.com?key={sensitive_key}"
            )
            output = service.execute_task(
                db=db_session,
                user_id=1,
                campaign_id=1,
                task_type="idea_generation",
                task_code="IDEA",
                prompt_version="v1",
                context={"campaign_name": "Test Camp", "product_name": "Prod", "product_usp": "USP"}
            )
            assert output.get("is_fallback") is True
            warnings = output.get("warnings", [])
            for w in warnings:
                assert sensitive_key not in w
                if "Lỗi AI" in w:
                    assert "key=[REDACTED]" in w or "[REDACTED" in w

    def test_ai_service_execute_task_sanitizes_raised_error_when_fallback_disabled(self, db_session):
        service = AIService()
        service.fallback_enabled = False
        sensitive_key = "AIzaSy_No_Fallback_Key_78901234567"

        with patch.object(service, "_call_provider_with_retry") as mock_call:
            mock_call.side_effect = RuntimeError(
                f"Fatal connection timeout with key={sensitive_key}"
            )
            with pytest.raises(RuntimeError) as exc_info:
                service.execute_task(
                    db=db_session,
                    user_id=1,
                    campaign_id=1,
                    task_type="idea_generation",
                    task_code="IDEA",
                    prompt_version="v1",
                    context={"campaign_name": "Test Camp", "product_name": "Prod", "product_usp": "USP"}
                )
            assert sensitive_key not in str(exc_info.value)
            assert "key=[REDACTED]" in str(exc_info.value) or "[REDACTED" in str(exc_info.value)
