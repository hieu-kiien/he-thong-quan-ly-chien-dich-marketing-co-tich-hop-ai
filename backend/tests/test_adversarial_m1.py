"""
MarketFlow AI — Adversarial & Empirical Verification Test Suite (Milestone 1)
Author: Challenger 1 (Backend & E2E Integration Challenger)
Purpose: Adversarially challenge edge cases, tenant isolation, boundary conditions,
         and interface contracts under Milestone 1.
"""

import pytest
import json
from fastapi.testclient import TestClient
from app.models.entities import User, Workspace, WorkspaceMember, BrandKit, Campaign

def get_token(client: TestClient, email: str, password: str = "TestPass123!"):
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]

def auth_headers(token: str):
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# Challenge 1: Registration Edge Cases & Email Uniqueness
# ==============================================================================
class TestAdversarialAuthRegistration:
    """Stress-test user registration for duplicate emails, case sensitivity, and boundary inputs."""

    def test_adv_duplicate_exact_email_rejected_with_400(self, client: TestClient):
        email = "adv_unique_1@agency.com"
        reg_payload = {"email": email, "password": "Password@123", "full_name": "Adv User 1"}
        r1 = client.post("/api/v1/auth/register", json=reg_payload)
        assert r1.status_code == 201

        # Duplicate exact email must fail with 400
        r2 = client.post("/api/v1/auth/register", json=reg_payload)
        assert r2.status_code == 400, f"Expected 400 for duplicate email, got {r2.status_code}: {r2.text}"

    def test_adv_duplicate_case_insensitive_email_rejected(self, client: TestClient):
        email = "adv_case_test@agency.com"
        reg_payload = {"email": email, "password": "Password@123", "full_name": "Adv User Case"}
        r1 = client.post("/api/v1/auth/register", json=reg_payload)
        assert r1.status_code == 201

        # Upper case variant should still be rejected with 400
        r2 = client.post("/api/v1/auth/register", json={
            "email": "ADV_CASE_TEST@AGENCY.COM",
            "password": "Password@123",
            "full_name": "Adv User Case Duplicate"
        })
        assert r2.status_code == 400, f"Case-insensitive duplicate email not rejected: {r2.text}"

    def test_adv_email_with_spaces_normalized_and_rejected(self, client: TestClient):
        email = "adv_spaces@agency.com"
        reg_payload = {"email": email, "password": "Password@123", "full_name": "Adv Spaces"}
        r1 = client.post("/api/v1/auth/register", json=reg_payload)
        assert r1.status_code == 201

        # Email with surrounding whitespace should be normalized and rejected as duplicate
        r2 = client.post("/api/v1/auth/register", json={
            "email": f"  {email}  ",
            "password": "Password@123",
            "full_name": "Adv Spaces Duplicate"
        })
        assert r2.status_code == 400, f"Trimmed duplicate email not rejected: {r2.text}"


# ==============================================================================
# Challenge 2: Workspace Boundary Conditions & Input Fuzzing
# ==============================================================================
class TestAdversarialWorkspaceBoundaries:
    """Stress-test workspace inputs: empty name, whitespace-only, special characters, XSS."""

    def test_adv_empty_workspace_name_rejected_422(self, client: TestClient):
        token = get_token(client, "manager@ictu.edu.vn", "Manager@123")
        resp = client.post("/api/v1/workspaces", json={"name": ""}, headers=auth_headers(token))
        assert resp.status_code == 422, f"Empty workspace name returned {resp.status_code} instead of 422"

    def test_adv_whitespace_only_workspace_name(self, client: TestClient):
        """Adversarial vector: name containing only spaces '   '."""
        token = get_token(client, "manager@ictu.edu.vn", "Manager@123")
        resp = client.post("/api/v1/workspaces", json={"name": "   "}, headers=auth_headers(token))
        # If whitespace-only is accepted without trimming, this is a data cleanliness vulnerability
        if resp.status_code in (200, 201):
            pytest.fail(f"VULNERABILITY: Workspace accepted whitespace-only name: {resp.text}")
        else:
            assert resp.status_code == 422

    def test_adv_xss_and_special_chars_in_workspace(self, client: TestClient):
        token = get_token(client, "manager@ictu.edu.vn", "Manager@123")
        payload = {
            "name": "<script>alert('xss')</script> Brand Việt Nam 🇻🇳",
            "description": "SQL' OR '1'='1 -- test"
        }
        resp = client.post("/api/v1/workspaces", json=payload, headers=auth_headers(token))
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert "🇻🇳" in data["name"]


# ==============================================================================
# Challenge 3: Unauthorized Workspace Access (BOLA / IDOR)
# ==============================================================================
class TestAdversarialWorkspaceBOLA:
    """Stress-test unauthorized access across workspaces (Broken Object Level Auth)."""

    def test_adv_external_user_cannot_read_workspace(self, client: TestClient):
        # Register User A (Agency A)
        r_a = client.post("/api/v1/auth/register", json={
            "email": "user_a_agency@test.com", "password": "Password123!", "full_name": "User A"
        })
        token_a = get_token(client, "user_a_agency@test.com", "Password123!")

        # Create Workspace A
        ws_resp = client.post("/api/v1/workspaces", json={"name": "Workspace A Confidential"}, headers=auth_headers(token_a))
        ws_a_id = ws_resp.json()["id"]

        # Register User B (Agency B - Competitor)
        r_b = client.post("/api/v1/auth/register", json={
            "email": "user_b_competitor@test.com", "password": "Password123!", "full_name": "User B"
        })
        token_b = get_token(client, "user_b_competitor@test.com", "Password123!")

        # Competitor attempts to read Workspace A
        resp = client.get(f"/api/v1/workspaces/{ws_a_id}", headers=auth_headers(token_b))
        assert resp.status_code == 403, f"BOLA Vulnerability: Competitor read workspace details: {resp.text}"

    def test_adv_external_user_cannot_modify_workspace(self, client: TestClient):
        # Register User A
        client.post("/api/v1/auth/register", json={
            "email": "user_a_mod@test.com", "password": "Password123!", "full_name": "User A Mod"
        })
        token_a = get_token(client, "user_a_mod@test.com", "Password123!")
        ws_a = client.post("/api/v1/workspaces", json={"name": "Workspace A Mod"}, headers=auth_headers(token_a)).json()

        # Register User B
        client.post("/api/v1/auth/register", json={
            "email": "user_b_mod@test.com", "password": "Password123!", "full_name": "User B Mod"
        })
        token_b = get_token(client, "user_b_mod@test.com", "Password123!")

        # User B attempts to overwrite Workspace A
        resp = client.put(f"/api/v1/workspaces/{ws_a['id']}", json={"name": "Defaced by Competitor"}, headers=auth_headers(token_b))
        assert resp.status_code == 403, f"BOLA Vulnerability: Competitor updated workspace: {resp.text}"

    def test_adv_external_user_cannot_read_or_update_brand_kit(self, client: TestClient):
        # User A workspace
        client.post("/api/v1/auth/register", json={
            "email": "user_a_bk@test.com", "password": "Password123!", "full_name": "User A BK"
        })
        token_a = get_token(client, "user_a_bk@test.com", "Password123!")
        ws_a = client.post("/api/v1/workspaces", json={"name": "Workspace A BK"}, headers=auth_headers(token_a)).json()

        # User B
        client.post("/api/v1/auth/register", json={
            "email": "user_b_bk@test.com", "password": "Password123!", "full_name": "User B BK"
        })
        token_b = get_token(client, "user_b_bk@test.com", "Password123!")

        # Read Brand Kit of A by B
        r_get = client.get(f"/api/v1/brand-kit?workspace_id={ws_a['id']}", headers=auth_headers(token_b))
        assert r_get.status_code == 403, f"BOLA Vulnerability: Competitor read Brand Kit: {r_get.text}"

        # Update Brand Kit of A by B
        r_put = client.put(f"/api/v1/brand-kit?workspace_id={ws_a['id']}", json={"brand_name": "Hacked"}, headers=auth_headers(token_b))
        assert r_put.status_code == 403, f"BOLA Vulnerability: Competitor updated Brand Kit: {r_put.text}"


# ==============================================================================
# Challenge 4: Tenant Isolation & Cross-Workspace Campaign Leakage
# ==============================================================================
class TestAdversarialTenantIsolation:
    """Stress-test multi-tenant data boundary: campaigns must never cross-pollinate workspaces."""

    def test_adv_tenant_isolation_campaign_visibility_between_workspaces(self, client: TestClient):
        # Agency X Manager
        client.post("/api/v1/auth/register", json={
            "email": "agency_x_mgr@test.com", "password": "Password123!", "full_name": "Agency X Manager", "role": "AGENCY_MANAGER"
        })
        token_x = get_token(client, "agency_x_mgr@test.com", "Password123!")
        ws_x = client.post("/api/v1/workspaces", json={"name": "Agency X Workspace"}, headers=auth_headers(token_x)).json()

        # Create Campaign in Workspace X
        camp_x_payload = {
            "name": "Secret Campaign Agency X",
            "workspace_id": ws_x["id"],
            "product_id": 1,
            "objective": "Confidential Launch",
            "audience": "Enterprise X",
            "start_date": "2026-10-01",
            "end_date": "2026-10-10",
            "budget": 5000000.0
        }
        camp_x = client.post("/api/v1/campaigns", json=camp_x_payload, headers=auth_headers(token_x)).json()

        # Agency Y Manager (Separate tenant)
        client.post("/api/v1/auth/register", json={
            "email": "agency_y_mgr@test.com", "password": "Password123!", "full_name": "Agency Y Manager", "role": "AGENCY_MANAGER"
        })
        token_y = get_token(client, "agency_y_mgr@test.com", "Password123!")
        ws_y = client.post("/api/v1/workspaces", json={"name": "Agency Y Workspace"}, headers=auth_headers(token_y)).json()

        # 1. Agency Y lists campaigns in their own workspace Y: should NOT contain Agency X's campaign
        list_y = client.get(f"/api/v1/campaigns?workspace_id={ws_y['id']}", headers=auth_headers(token_y)).json()
        campaign_ids_in_y = [c["id"] for c in list_y]
        assert camp_x["id"] not in campaign_ids_in_y, "TENANT LEAK: Agency X campaign appeared in Agency Y campaign list!"

        # 2. Agency Y explicitly asks for campaigns in Workspace X (?workspace_id=ws_x['id'])
        # In strict multi-tenancy, Agency Y has NO MEMBERSHIP in Workspace X and must be blocked (403) or return empty list!
        resp_leak_query = client.get(f"/api/v1/campaigns?workspace_id={ws_x['id']}", headers=auth_headers(token_y))
        if resp_leak_query.status_code == 200:
            leak_campaigns = resp_leak_query.json()
            leaked_ids = [c["id"] for c in leak_campaigns if c["id"] == camp_x["id"]]
            if leaked_ids:
                pytest.fail(f"CRITICAL TENANT ISOLATION BREACH: Agency Y Manager accessed Agency X campaigns via ?workspace_id={ws_x['id']}")

        # 3. Agency Y attempts direct access to Agency X's campaign GET /api/v1/campaigns/{id}
        resp_direct = client.get(f"/api/v1/campaigns/{camp_x['id']}", headers=auth_headers(token_y))
        if resp_direct.status_code == 200:
            pytest.fail(f"CRITICAL TENANT ISOLATION BREACH: Agency Y Manager accessed Agency X campaign {camp_x['id']} directly via GET /campaigns/{camp_x['id']}!")
        else:
            assert resp_direct.status_code in (403, 404)


# ==============================================================================
# Challenge 5: Interface Contract Consistency on Brand Kit Endpoint
# ==============================================================================
class TestAdversarialBrandKitContract:
    """Stress-test whether Brand Kit endpoints accept requests with or without workspace_id query param."""

    def test_adv_put_brand_kit_without_workspace_id_query_param(self, client: TestClient):
        """As specified in PROJECT.md interface contract: PUT /api/v1/brand-kit can be called with JSON body."""
        token = get_token(client, "manager@ictu.edu.vn", "Manager@123")
        payload = {
            "brand_name": "Test Brand",
            "usp": "Test USP",
            "tone_of_voice": "Friendly",
            "banned_keywords": ["badword"]
        }
        resp = client.put("/api/v1/brand-kit", json=payload, headers=auth_headers(token))
        # If this returns 422, it proves why E2E tests test_t1_r1_04 and test_t2_r1_02 failed!
        if resp.status_code == 422:
            detail = resp.json().get("detail", [])
            is_missing_query = any(d.get("loc") == ["query", "workspace_id"] for d in detail if isinstance(d, dict))
            if is_missing_query:
                pytest.fail("CONTRACT MISMATCH: PUT /api/v1/brand-kit requires query parameter 'workspace_id', breaking E2E tests and client calls that provide workspace via body or context.")
        assert resp.status_code in (200, 201)
