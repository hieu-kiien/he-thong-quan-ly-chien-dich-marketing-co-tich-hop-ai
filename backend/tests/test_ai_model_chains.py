"""Test chuỗi fallback model (AIModelChain, kiểu 9Router).

Phủ 3 tầng:
1. CRUD API `/settings/ai-chains` (RBAC, trùng tên, default duy nhất, toggle).
2. `AIService.execute_task` với chuỗi: failover hop, schema-failover, hết chuỗi
   -> Smart Fallback, bỏ qua hop thiếu key, resolver bỏ qua chuỗi tắt/ngoài phạm vi.
3. Nối tiếp qua endpoint `/ai/ideas` (chain_id trong request) và payload job.
"""

import json
from unittest.mock import patch

import pytest

from app.core.crypto import encrypt_api_key
from app.models.entities import AIModelChain, CustomApiKey, User
from app.schemas.schemas import AIIdeaRequest
from app.services.ai.ai_service import AIService, ai_service
from app.api.v1.ai_jobs import AIJobCreateRequest, _validate_job_payload

VALID_IDEA_JSON = json.dumps({
    "ideas": [{
        "id": 1,
        "angle": "Lợi ích cốt lõi",
        "headline": "Tăng trưởng bền vững",
        "concept": "Tập trung vào giá trị thật",
        "target_emotion": "Hy vọng",
    }]
})


def _login(client, email, password):
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _manager_user(db):
    u = db.query(User).filter(User.email.in_(["manager@gmail.com", "manager@gmail.com"])).first()
    assert u is not None
    return u


def _add_personal_key(db, user_id, provider, model, plain):
    db.add(CustomApiKey(
        user_id=user_id,
        workspace_id=None,
        provider=provider,
        model=model,
        encrypted_key=encrypt_api_key(plain),
        is_active=True,
    ))
    db.commit()


def _add_chain(db, user_id, name, hops, **kw):
    chain = AIModelChain(
        user_id=user_id,
        workspace_id=kw.get("workspace_id"),
        name=name,
        hops_json=json.dumps(hops, ensure_ascii=False),
        is_active=kw.get("is_active", True),
        is_default=kw.get("is_default", False),
    )
    db.add(chain)
    db.commit()
    db.refresh(chain)
    return chain


def _execute_with_chain(db, user_id, chain_id, **context_extra):
    context = {
        "campaign_name": "Chiến dịch Test",
        "product_name": "Sản phẩm Test",
        "product_usp": "USP Test",
        "channel_name": "Facebook",
        "tone": "chuyên nghiệp",
        "model_chain_id": chain_id,
    }
    context.update(context_extra)
    return ai_service.execute_task(
        db=db,
        user_id=user_id,
        campaign_id=None,
        task_type="idea_generation",
        task_code="IDEA",
        prompt_version="v3",
        context=context,
    )


HOPS_2 = [
    {"provider": "openai", "model": "gpt-4o"},
    {"provider": "gemini", "model": "gemini-2.5-flash"},
]


# ==============================================================================
# 1. CRUD API
# ==============================================================================

def test_create_chain_201_and_roundtrip(client, db_session):
    headers = _login(client, "manager@gmail.com", "Manager@123")
    resp = client.post("/api/v1/settings/ai-chains", headers=headers, json={
        "name": "Chuỗi Vip",
        "hops": HOPS_2,
    })
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["name"] == "Chuỗi Vip"
    assert [h["provider"] for h in body["hops"]] == ["openai", "gemini"]
    assert body["scope"] == "personal"
    assert body["is_default"] is False

    listed = client.get("/api/v1/settings/ai-chains", headers=headers)
    assert listed.status_code == 200
    assert any(c["id"] == body["id"] for c in listed.json())


def test_create_chain_model_optional_defaults_to_provider_model(client, db_session):
    """Hop thiếu model được điền model mặc định của provider (không 422)."""
    headers = _login(client, "manager@gmail.com", "Manager@123")
    resp = client.post("/api/v1/settings/ai-chains", headers=headers, json={
        "name": "Model Mặc Định",
        "hops": [{"provider": "gemini"}],
    })
    assert resp.status_code == 201, resp.text
    hop = resp.json()["hops"][0]
    assert hop["provider"] == "gemini"
    assert hop["model"].startswith("gemini")


def test_create_chain_duplicate_name_409(client, db_session):
    headers = _login(client, "manager@gmail.com", "Manager@123")
    payload = {"name": "Trùng Tên", "hops": HOPS_2}
    assert client.post("/api/v1/settings/ai-chains", headers=headers, json=payload).status_code == 201
    dup = client.post("/api/v1/settings/ai-chains", headers=headers, json=payload)
    assert dup.status_code == 409


def test_create_chain_invalid_provider_or_model_422(client, db_session):
    headers = _login(client, "manager@gmail.com", "Manager@123")
    bad_provider = client.post("/api/v1/settings/ai-chains", headers=headers, json={
        "name": "Provider Lạ", "hops": [{"provider": "skynet", "model": "skynet-1"}],
    })
    assert bad_provider.status_code == 422
    bad_model = client.post("/api/v1/settings/ai-chains", headers=headers, json={
        "name": "Model Lệch Hệ", "hops": [{"provider": "openai", "model": "gemini-2.5-flash"}],
    })
    assert bad_model.status_code == 422


def test_default_chain_uniqueness_per_scope(client, db_session):
    headers = _login(client, "manager@gmail.com", "Manager@123")
    a = client.post("/api/v1/settings/ai-chains", headers=headers, json={
        "name": "Default A", "hops": HOPS_2, "is_default": True,
    }).json()
    b = client.post("/api/v1/settings/ai-chains", headers=headers, json={
        "name": "Default B", "hops": HOPS_2, "is_default": True,
    }).json()
    listed = {c["name"]: c for c in client.get("/api/v1/settings/ai-chains", headers=headers).json()}
    assert listed["Default A"]["is_default"] is False
    assert listed["Default B"]["is_default"] is True
    assert a["id"] != b["id"]


def test_toggle_off_default_chain_releases_default(client, db_session):
    headers = _login(client, "manager@gmail.com", "Manager@123")
    chain = client.post("/api/v1/settings/ai-chains", headers=headers, json={
        "name": "Toggle Me", "hops": HOPS_2, "is_default": True,
    }).json()
    toggled = client.patch(f"/api/v1/settings/ai-chains/{chain['id']}/toggle", headers=headers)
    assert toggled.status_code == 200
    assert toggled.json()["is_active"] is False
    assert toggled.json()["is_default"] is False

    # Chuỗi đang tắt không được đặt làm mặc định.
    denied = client.patch(f"/api/v1/settings/ai-chains/{chain['id']}/default", headers=headers)
    assert denied.status_code == 409


def test_delete_chain(client, db_session):
    headers = _login(client, "manager@gmail.com", "Manager@123")
    chain = client.post("/api/v1/settings/ai-chains", headers=headers, json={
        "name": "Xóa Nhanh", "hops": HOPS_2,
    }).json()
    deleted = client.delete(f"/api/v1/settings/ai-chains/{chain['id']}", headers=headers)
    assert deleted.status_code == 200
    listed = client.get("/api/v1/settings/ai-chains", headers=headers).json()
    assert all(c["id"] != chain["id"] for c in listed)


def test_marketer_cannot_delete_workspace_chain_of_manager(client, db_session, workspace_alpha):
    manager_headers = _login(client, "manager@gmail.com", "Manager@123")
    ws_chain = client.post("/api/v1/settings/ai-chains", headers=manager_headers, json={
        "name": "Chuỗi Workspace Alpha", "hops": HOPS_2, "workspace_id": workspace_alpha.id,
    })
    assert ws_chain.status_code == 201, ws_chain.text

    marketer_headers = _login(client, "marketer@gmail.com", "Marketer@123")
    denied = client.delete(
        f"/api/v1/settings/ai-chains/{ws_chain.json()['id']}", headers=marketer_headers
    )
    assert denied.status_code == 403


# ==============================================================================
# 2. execute_task: failover giữa các hop
# ==============================================================================

def test_chain_failover_second_hop_succeeds(db_session):
    """Hop 1 lỗi HTTP -> hop 2 trả JSON hợp lệ -> kết quả nhận của hop 2."""
    user = _manager_user(db_session)
    _add_personal_key(db_session, user.id, "openai", "gpt-4o", "sk-test-openai-123")
    _add_personal_key(db_session, user.id, "gemini", "gemini-2.5-flash", "AIza-test-gemini-123")
    chain = _add_chain(db_session, user.id, "Failover Vip", HOPS_2)

    calls = []

    def fake_call(self, system_prompt, user_prompt, active_key=None, active_model=None,
                  provider=None, timeout_override=None, retries_override=None, **kw):
        calls.append({
            "provider": provider, "model": active_model, "key": active_key,
            "timeout": timeout_override, "retries": retries_override,
        })
        if provider == "openai":
            raise RuntimeError("AI Provider trả về lỗi HTTP 500: Internal Server Error")
        return VALID_IDEA_JSON

    with patch.object(AIService, "_call_provider_with_retry", fake_call):
        out = _execute_with_chain(db_session, user.id, chain.id)

    assert [c["provider"] for c in calls] == ["openai", "gemini"]
    # Multi-hop: mỗi bước nhận ngân sách timeout/retries riêng, không None.
    assert isinstance(calls[0]["timeout"], int) and calls[0]["timeout"] >= 15
    assert calls[0]["retries"] is not None
    assert out["is_fallback"] is False
    assert out["model_used"] == "gemini-2.5-flash"
    # Key cá nhân -> tier USER; nguồn gốc phải gắn đúng provider đã gọi.
    assert out["model_provider"] == "gemini-user"
    assert any("đã bỏ qua" in w and "openai" in w for w in out.get("warnings", []))


def test_chain_schema_error_moves_to_next_hop(db_session):
    """Hop 1 trả JSON sai schema -> chuyển hop 2 (đúng tinh thần 9Router)."""
    user = _manager_user(db_session)
    _add_personal_key(db_session, user.id, "openai", "gpt-4o", "sk-test-openai-123")
    _add_personal_key(db_session, user.id, "gemini", "gemini-2.5-flash", "AIza-test-gemini-123")
    chain = _add_chain(db_session, user.id, "Schema Failover", HOPS_2)

    def fake_call(self, system_prompt, user_prompt, active_key=None, active_model=None,
                  provider=None, timeout_override=None, retries_override=None, **kw):
        if provider == "openai":
            return '{"ideas": [{"id": "sai-kieu"}]}'  # id phải int -> ValidationError
        return VALID_IDEA_JSON

    with patch.object(AIService, "_call_provider_with_retry", fake_call):
        out = _execute_with_chain(db_session, user.id, chain.id)

    assert out["is_fallback"] is False
    assert out["model_used"] == "gemini-2.5-flash"


def test_chain_all_hops_fail_falls_back_to_template(db_session):
    """Hết chuỗi -> template Smart Fallback, cảnh báo nêu rõ từng hop đã thử."""
    user = _manager_user(db_session)
    _add_personal_key(db_session, user.id, "openai", "gpt-4o", "sk-test-openai-123")
    _add_personal_key(db_session, user.id, "gemini", "gemini-2.5-flash", "AIza-test-gemini-123")
    chain = _add_chain(db_session, user.id, "Chuỗi Hỏng", HOPS_2)

    def fake_call(self, *a, **kw):
        raise RuntimeError("AI Provider trả về lỗi HTTP 503: Down")

    with patch.object(AIService, "_call_provider_with_retry", fake_call):
        out = _execute_with_chain(db_session, user.id, chain.id)

    assert out["is_fallback"] is True
    assert out["model_provider"] == "template-fallback-engine"
    assert out["model_used"].endswith("(Chain Failover Fallback)")
    assert any("Chuỗi “Chuỗi Hỏng”" in w and "đã kích hoạt Smart Fallback" in w for w in out["warnings"])
    assert out["ideas"], "template vẫn phải sinh dữ liệu an toàn"


def test_chain_skips_hop_without_key(db_session, monkeypatch):
    """Hop thiếu API key bị bỏ qua im lặng, hop có key vẫn chạy."""
    user = _manager_user(db_session)
    _add_personal_key(db_session, user.id, "gemini", "gemini-2.5-flash", "AIza-test-gemini-123")
    chain = _add_chain(db_session, user.id, "Thiếu Key OpenAI", HOPS_2)

    # Ép môi trường không có khoá hệ thống cho openai để hop 1 thiếu key thật.
    from app.core.config import settings as app_settings
    from app.services.ai import providers as provider_registry
    monkeypatch.setattr(app_settings, "AI_API_KEY", "")
    for spec in provider_registry.PROVIDERS:
        for env_name in spec.env_key_names:
            monkeypatch.delenv(env_name, raising=False)
            if hasattr(app_settings, env_name):
                monkeypatch.setattr(app_settings, env_name, "")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    calls = []

    def fake_call(self, system_prompt, user_prompt, active_key=None, active_model=None,
                  provider=None, timeout_override=None, retries_override=None, **kw):
        calls.append(provider)
        return VALID_IDEA_JSON

    with patch.object(AIService, "_call_provider_with_retry", fake_call):
        out = _execute_with_chain(db_session, user.id, chain.id)

    assert calls == ["gemini"]
    assert out["is_fallback"] is False
    assert out["model_used"] == "gemini-2.5-flash"
    assert any("thiếu API key" in w for w in out.get("warnings", []))


# ==============================================================================
# 3. Resolver: chuỗi mặc định, bỏ qua chuỗi tắt/ngoài phạm vi, fixture mode
# ==============================================================================

def test_resolver_picks_default_chain_when_no_explicit_id(db_session):
    user = _manager_user(db_session)
    _add_chain(db_session, user.id, "Mặc Định Cá Nhân", HOPS_2, is_default=True)
    svc = AIService()
    resolved = svc._resolve_chain_hops(db_session, user.id, None, {})
    assert resolved is not None
    assert resolved["name"] == "Mặc Định Cá Nhân"
    assert len(resolved["hops"]) == 2


def test_resolver_workspace_default_beats_personal_default(db_session, workspace_alpha):
    user = _manager_user(db_session)
    _add_chain(db_session, user.id, "Cá Nhân Mặc Định", HOPS_2, is_default=True)
    _add_chain(db_session, user.id, "Workspace Mặc Định", HOPS_2,
               workspace_id=workspace_alpha.id, is_default=True)
    svc = AIService()
    resolved = svc._resolve_chain_hops(db_session, user.id, workspace_alpha.id, {})
    assert resolved is not None
    assert resolved["name"] == "Workspace Mặc Định"


def test_resolver_ignores_inactive_and_foreign_chains(db_session, workspace_beta):
    user = _manager_user(db_session)
    inactive = _add_chain(db_session, user.id, "Đang Tắt", HOPS_2, is_active=False)
    svc = AIService()
    assert svc._resolve_chain_hops(db_session, user.id, None, {"model_chain_id": inactive.id}) is None

    active = _add_chain(db_session, user.id, "Đang Bật", HOPS_2)
    beta_user = db_session.query(User).filter(
        User.email.in_(["agency_mgr_beta@gmail.com", "agency_mgr_beta@gmail.com"])
    ).first()
    assert beta_user is not None
    # User Beta không thuộc workspace nào của chuỗi cá nhân này -> bỏ qua.
    assert svc._resolve_chain_hops(db_session, beta_user.id, None, {"model_chain_id": active.id}) is None


def test_resolver_fixture_mode_never_uses_chain(db_session):
    user = _manager_user(db_session)
    _add_chain(db_session, user.id, "Fixture Chain", HOPS_2, is_default=True)
    svc = AIService()
    svc._api_key = "fixture-key"
    try:
        assert svc._resolve_chain_hops(db_session, user.id, None, {}) is None
        assert svc._resolve_chain_hops(db_session, user.id, None, {"model_chain_id": 1}) is None
    finally:
        del svc._api_key


# ==============================================================================
# 4. Nối tiếp: endpoint /ai/ideas và payload job
# ==============================================================================

def test_ai_ideas_endpoint_accepts_chain_id(client, db_session):
    """POST /ai/ideas nhận chain_id; offline suite chặn mạng nên mọi hop thất bại
    -> template, nhưng cảnh báo phải nêu đúng tên chuỗi (chứng minh chuỗi đã chạy)."""
    headers = _login(client, "manager@gmail.com", "Manager@123")
    chain = client.post("/api/v1/settings/ai-chains", headers=headers, json={
        "name": "Endpoint Chain", "hops": HOPS_2,
    }).json()

    resp = client.post("/api/v1/ai/ideas", headers=headers, json={
        "channel_code": "facebook",
        "custom_topic": "Chủ đề test nối tiếp",
        "chain_id": chain["id"],
    })
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["is_fallback"] is True
    assert any("Chuỗi “Endpoint Chain”" in w for w in body.get("warnings", []))


def test_job_payload_preserves_chain_id():
    req = AIJobCreateRequest(kind="ideas", chain_id=7, custom_topic="Test job chain")
    payload = req.payload_for_queue()
    assert payload.get("chain_id") == 7
    # Payload phải validate được bằng chính model của endpoint đồng bộ.
    validated = _validate_job_payload("ideas", payload)
    assert isinstance(validated, AIIdeaRequest)
    assert validated.chain_id == 7


def test_idea_request_schema_has_optional_chain_id():
    req = AIIdeaRequest(custom_topic="x")
    assert req.chain_id is None
    req2 = AIIdeaRequest(custom_topic="x", chain_id=3)
    assert req2.chain_id == 3
