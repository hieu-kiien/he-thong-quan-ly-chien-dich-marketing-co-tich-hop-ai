"""
MarketFlow AI - Empirical Adversarial Audit Runner
Executes all 7 challenge scenarios directly against the FastAPI application with clean test fixtures.
Reports PASS/FAIL with exact status codes and response bodies for evidence collection.
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import json
from datetime import timedelta
from unittest.mock import patch
import jwt
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.config import settings
from app.core.security import create_access_token
from app.main import app
from seed.seed_data import seed_data
from app.services.ai.ai_service import ai_service


# 1. Setup in-memory clean test engine with StaticPool (isolated & immune to Windows file locking)
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

@event.listens_for(test_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Initialize schema and seed data
Base.metadata.create_all(bind=test_engine)
init_session = TestingSessionLocal()
seed_data(session=init_session)
init_session.close()

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

results = []

def record(scenario_name, condition, expected, actual, passed, details=""):
    results.append({
        "scenario": scenario_name,
        "condition": condition,
        "expected": expected,
        "actual": actual,
        "passed": passed,
        "details": details
    })
    status_str = "PASS" if passed else "FAIL"
    print(f"[{status_str}] {scenario_name} | {condition} -> Expected {expected}, got {actual}")
    if not passed and details:
        print(f"       Details: {details}")


def get_token(email="marketer@ictu.edu.vn", password="Marketer@123"):
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]


def run_all_adversarial_tests():
    print("=" * 80)
    print("STARTING EMPIRICAL ADVERSARIAL QA AUDIT (7 MISSION SCENARIOS)")
    print("=" * 80)

    # --------------------------------------------------------------------------
    # SCENARIO 1: Unauthenticated Access Attempts (Must receive 401)
    # --------------------------------------------------------------------------
    print("\n--- Running Scenario 1: Unauthenticated Access ---")
    endpoints_to_test = [
        ("GET", "/api/v1/campaigns", None),
        ("POST", "/api/v1/campaigns", {"name": "No Auth"}),
        ("GET", "/api/v1/campaigns/1", None),
        ("PUT", "/api/v1/campaigns/1", {"name": "Hacked"}),
        ("DELETE", "/api/v1/campaigns/1", None),
        ("GET", "/api/v1/contents", None),
        ("POST", "/api/v1/contents", {"title": "No Auth"}),
        ("GET", "/api/v1/contents/1", None),
        ("PUT", "/api/v1/contents/1", {"title": "Hacked"}),
        ("POST", "/api/v1/contents/1/submit", None),
        ("POST", "/api/v1/contents/1/approve", None),
        ("POST", "/api/v1/contents/1/reject", {"decision": "REJECTED"}),
        ("GET", "/api/v1/campaigns/1/metrics", None),
        ("POST", "/api/v1/campaigns/1/metrics", {"metric_date": "2026-10-01"}),
        ("GET", "/api/v1/campaigns/1/kpi", None),
        ("GET", "/api/v1/analytics/dashboard", None),
        ("GET", "/api/v1/channels", None),
        ("GET", "/api/v1/products", None),
        ("GET", "/api/v1/product-categories", None),
        ("GET", "/api/v1/schedules", None),
        ("POST", "/api/v1/contents/1/schedule", {"scheduled_at": "2026-10-15"}),
        ("POST", "/api/v1/ai/ideas", {"campaign_id": 1}),
        ("POST", "/api/v1/ai/draft", {"campaign_id": 1}),
        ("POST", "/api/v1/ai/summary", {"campaign_id": 1}),
        ("GET", "/api/v1/ai/logs", None),
        ("GET", "/api/v1/auth/me", None),
    ]

    for method, path, payload in endpoints_to_test:
        if method == "GET":
            r = client.get(path)
        elif method == "POST":
            r = client.post(path, json=payload or {})
        elif method == "PUT":
            r = client.put(path, json=payload or {})
        elif method == "DELETE":
            r = client.delete(path)
        passed = (r.status_code == 401)
        record("Scenario 1: Unauthenticated", f"{method} {path}", 401, r.status_code, passed, r.text)

    # --------------------------------------------------------------------------
    # SCENARIO 2: Tampered / Expired JWT Tokens (Must receive 401)
    # --------------------------------------------------------------------------
    print("\n--- Running Scenario 2: Tampered / Expired JWT Tokens ---")
    # Expired token
    exp_tok = create_access_token(data={"sub": "1", "role": "MARKETER"}, expires_delta=timedelta(seconds=-10))
    r_exp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {exp_tok}"})
    record("Scenario 2: JWT", "Expired token", 401, r_exp.status_code, r_exp.status_code == 401, r_exp.text)

    # Forged secret token
    forged_tok = jwt.encode({"sub": "1", "role": "MARKETER"}, "FORGED_ATTACKER_KEY_THAT_DOES_NOT_MATCH_32_BYTES", algorithm="HS256")
    r_forged = client.get("/api/v1/campaigns", headers={"Authorization": f"Bearer {forged_tok}"})
    record("Scenario 2: JWT", "Forged signature", 401, r_forged.status_code, r_forged.status_code == 401, r_forged.text)

    # Truncated token
    r_trunc = client.get("/api/v1/contents", headers={"Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.corrupt"})
    record("Scenario 2: JWT", "Truncated token", 401, r_trunc.status_code, r_trunc.status_code == 401, r_trunc.text)

    # Non-integer sub
    bad_sub_tok = create_access_token(data={"sub": "not_an_int"})
    r_sub = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {bad_sub_tok}"})
    record("Scenario 2: JWT", "Non-integer sub", 401, r_sub.status_code, r_sub.status_code == 401, r_sub.text)

    # Missing sub
    no_sub_tok = create_access_token(data={"email": "nosub@test.com"})
    r_nosub = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {no_sub_tok}"})
    record("Scenario 2: JWT", "Missing sub", 401, r_nosub.status_code, r_nosub.status_code == 401, r_nosub.text)

    # Ghost user ID (99999)
    ghost_tok = create_access_token(data={"sub": "99999"})
    r_ghost = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {ghost_tok}"})
    record("Scenario 2: JWT", "Ghost user ID (99999)", 401, r_ghost.status_code, r_ghost.status_code == 401, r_ghost.text)

    # --------------------------------------------------------------------------
    # SCENARIO 3: SQL Injection & Payload Corruption (Must receive 422, NEVER 500)
    # --------------------------------------------------------------------------
    print("\n--- Running Scenario 3: SQLi & Payload Corruption (422, never 500) ---")
    mkt_token = get_token("marketer@ictu.edu.vn", "Marketer@123")
    mkt_headers = {"Authorization": f"Bearer {mkt_token}"}

    sqli_status_payloads = [
        "' OR '1'='1",
        "'; DROP TABLE marketing_contents; --",
        "UNION SELECT 1,2,3,4,5,6,7,8,9,10 --",
        "HACKED_STATUS",
        "draft",  # lower case not allowed
        "A" * 5000,
        "STATUS\x00NULL"
    ]
    for sqli in sqli_status_payloads:
        payload = {
            "campaign_id": 1,
            "channel_id": 1,
            "title": "SQLi Status",
            "body": "Test",
            "cta": "Click",
            "status": sqli
        }
        r = client.post("/api/v1/contents", json=payload, headers=mkt_headers)
        passed = (r.status_code == 422 and r.status_code != 500)
        record("Scenario 3: Status SQLi", f"status='{sqli[:20]}'", 422, r.status_code, passed, r.text)

    sqli_date_payloads = [
        "' OR '1'='1",
        "2026-10-01'; DROP TABLE campaigns; --",
        "2026-02-30",
        "2026-13-01",
        "2026-00-10",
        "2026-04-31",
        "2026/10/01",
        "not-a-date"
    ]
    for bad_d in sqli_date_payloads:
        payload = {
            "product_id": 1,
            "name": f"Date Injection Test",
            "objective": "Test",
            "audience": "Test",
            "start_date": bad_d,
            "end_date": "2026-12-31",
            "budget": 1000.0
        }
        r = client.post("/api/v1/campaigns", json=payload, headers=mkt_headers)
        passed = (r.status_code == 422 and r.status_code != 500)
        record("Scenario 3: Date SQLi", f"start_date='{bad_d}'", 422, r.status_code, passed, r.text)

    # Inverted date
    inverted_payload = {
        "product_id": 1,
        "name": "Inverted Date Campaign",
        "objective": "Test",
        "audience": "Test",
        "start_date": "2026-12-31",
        "end_date": "2026-10-01",
        "budget": 1000.0
    }
    r_inv = client.post("/api/v1/campaigns", json=inverted_payload, headers=mkt_headers)
    record("Scenario 3: Logic Date", "start_date > end_date", 422, r_inv.status_code, r_inv.status_code == 422, r_inv.text)

    # --------------------------------------------------------------------------
    # SCENARIO 4: Duplicate Metric Insertions (Must receive 409 Conflict, NEVER 500)
    # --------------------------------------------------------------------------
    print("\n--- Running Scenario 4: Duplicate Metric Insertions ---")
    metric_payload = {
        "campaign_id": 1,
        "channel_id": 1,
        "metric_date": "2026-11-20",
        "views": 200,
        "clicks": 20,
        "conversions": 2,
        "cost": 500.0,
        "revenue": 2000.0
    }
    r_m1 = client.post("/api/v1/campaigns/1/metrics", json=metric_payload, headers=mkt_headers)
    record("Scenario 4: Metric", "Initial metric record", 201, r_m1.status_code, r_m1.status_code == 201, r_m1.text)

    r_m2 = client.post("/api/v1/campaigns/1/metrics", json=metric_payload, headers=mkt_headers)
    passed_m2 = (r_m2.status_code == 409 and r_m2.status_code != 500 and "đã tồn tại" in r_m2.text)
    record("Scenario 4: Metric", "Duplicate metric (409 Conflict)", 409, r_m2.status_code, passed_m2, r_m2.text)

    # --------------------------------------------------------------------------
    # SCENARIO 5: HITL State Machine Bypass (Must receive 400 Bad Request)
    # --------------------------------------------------------------------------
    print("\n--- Running Scenario 5: HITL State Machine Bypass ---")
    mgr_token = get_token("manager@ictu.edu.vn", "Manager@123")
    mgr_headers = {"Authorization": f"Bearer {mgr_token}"}

    # Marketer direct PUT status APPROVED -> 400
    r_bypass_mkt = client.put("/api/v1/contents/1", json={"status": "APPROVED"}, headers=mkt_headers)
    record("Scenario 5: State Machine", "Marketer direct PUT status=APPROVED", 400, r_bypass_mkt.status_code, r_bypass_mkt.status_code == 400, r_bypass_mkt.text)

    # Manager direct PUT status APPROVED -> 400
    r_bypass_mgr = client.put("/api/v1/contents/1", json={"status": "APPROVED"}, headers=mgr_headers)
    record("Scenario 5: State Machine", "Manager direct PUT status=APPROVED", 400, r_bypass_mgr.status_code, r_bypass_mgr.status_code == 400, r_bypass_mgr.text)

    # Marketer calls /approve endpoint -> 403 Forbidden
    r_mkt_approve = client.post("/api/v1/contents/1/approve", headers=mkt_headers)
    record("Scenario 5: Authorization", "Marketer calls /approve endpoint", 403, r_mkt_approve.status_code, r_mkt_approve.status_code == 403, r_mkt_approve.text)

    # --------------------------------------------------------------------------
    # SCENARIO 6: Modifying APPROVED Content Reverts to AI_DRAFT
    # --------------------------------------------------------------------------
    print("\n--- Running Scenario 6: Modifying APPROVED Content Reverts to AI_DRAFT ---")
    # First ensure content 1 is approved
    # If content 1 is in IN_REVIEW, approve it
    r_app = client.post("/api/v1/contents/1/approve", headers=mgr_headers)
    record("Scenario 6: Setup", "Manager approves content 1", 200, r_app.status_code, r_app.status_code == 200, r_app.text)
    approved_content = client.get("/api/v1/contents/1", headers=mkt_headers).json()
    assert approved_content["status"] == "APPROVED"
    orig_ver = approved_content["version_no"]

    # Now marketer edits the title
    r_edit_title = client.put("/api/v1/contents/1", json={"title": "Tampered Title After Approval"}, headers=mkt_headers)
    data_title = r_edit_title.json()
    passed_title = (r_edit_title.status_code == 200 and data_title["status"] == "AI_DRAFT" and data_title["version_no"] == orig_ver + 1)
    record("Scenario 6: Revert", "Modifying title reverts status to AI_DRAFT", "AI_DRAFT & v+1", f"{data_title.get('status')} & v{data_title.get('version_no')}", passed_title, r_edit_title.text)

    # Submit and re-approve
    client.post("/api/v1/contents/1/submit", headers=mkt_headers)
    client.post("/api/v1/contents/1/approve", headers=mgr_headers)

    # Now edit body
    r_edit_body = client.put("/api/v1/contents/1", json={"body": "Tampered Body After Re-approval"}, headers=mkt_headers)
    data_body = r_edit_body.json()
    passed_body = (r_edit_body.status_code == 200 and data_body["status"] == "AI_DRAFT")
    record("Scenario 6: Revert", "Modifying body reverts status to AI_DRAFT", "AI_DRAFT", data_body.get("status"), passed_body, r_edit_body.text)

    # --------------------------------------------------------------------------
    # SCENARIO 7: AI Provider Schema Corruption & Smart Fallback (HTTP 200)
    # --------------------------------------------------------------------------
    print("\n--- Running Scenario 7: AI Schema Corruption & Smart Fallback ---")
    # AI ideas with corrupt schema
    corrupt_schema_json = json.dumps({"wrong_root": "unexpected", "items": [1, 2, 3]})
    with patch.object(ai_service, "_call_provider_with_retry", return_value=corrupt_schema_json):
        ai_service.api_key = "mock_key"
        ai_service.fallback_enabled = True

        r_ai_ideas = client.post("/api/v1/ai/ideas", json={"campaign_id": 1, "channel_code": "facebook"}, headers=mkt_headers)
        data_ideas = r_ai_ideas.json()
        passed_ideas = (r_ai_ideas.status_code == 200 and "ideas" in data_ideas and len(data_ideas["ideas"]) >= 1)
        record("Scenario 7: AI Fallback", "AI ideas corrupt schema activates fallback", "200 with ideas", f"{r_ai_ideas.status_code} with {len(data_ideas.get('ideas', []))} ideas", passed_ideas, r_ai_ideas.text[:200])

    # AI draft with malformed JSON
    broken_json = '{"title": "Unfinished draft...'
    with patch.object(ai_service, "_call_provider_with_retry", return_value=broken_json):
        ai_service.api_key = "mock_key"
        ai_service.fallback_enabled = True

        r_ai_draft = client.post("/api/v1/ai/draft", json={"campaign_id": 1, "channel_code": "facebook", "selected_idea": "Test"}, headers=mkt_headers)
        data_draft = r_ai_draft.json()
        passed_draft = (r_ai_draft.status_code == 200 and len(data_draft.get("title", "")) > 0 and len(data_draft.get("body", "")) > 0)
        record("Scenario 7: AI Fallback", "AI draft broken JSON activates fallback", "200 with title/body", f"{r_ai_draft.status_code}", passed_draft, r_ai_draft.text[:200])

    # AI provider error when fallback disabled -> 502 Bad Gateway
    with patch.object(ai_service, "_call_provider_with_retry", side_effect=RuntimeError("Provider Outage 503")):
        ai_service.api_key = "mock_key"
        ai_service.fallback_enabled = False

        r_ai_502 = client.post("/api/v1/ai/summary", json={"campaign_id": 1}, headers=mkt_headers)
        passed_502 = (r_ai_502.status_code == 502 and r_ai_502.status_code != 500)
        record("Scenario 7: AI Fallback Disabled", "AI outage when fallback disabled returns 502", 502, r_ai_502.status_code, passed_502, r_ai_502.text)

        ai_service.fallback_enabled = True
        ai_service.api_key = ""

    # --------------------------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------------------------
    total = len(results)
    passed_count = sum(1 for r in results if r["passed"])
    failed_count = total - passed_count
    print("\n" + "=" * 80)
    print(f"AUDIT SUMMARY: {passed_count}/{total} PASSED ({passed_count/total*100:.1f}%), {failed_count} FAILED")
    print("=" * 80)
    return total, passed_count, failed_count


if __name__ == "__main__":
    t, p, f = run_all_adversarial_tests()
    if f > 0:
        sys.exit(1)
    sys.exit(0)
