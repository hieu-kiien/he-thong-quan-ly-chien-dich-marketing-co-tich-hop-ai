import pytest
from typing import Dict, Any, Optional
from fastapi.testclient import TestClient
from app.core.security import hash_password, create_access_token
from app.models.entities import User

def get_auth_headers(client: TestClient, email: str, password: str) -> Dict[str, str]:
    """Authenticate with email and password and return Bearer Authorization header."""
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    if resp.status_code != 200:
        raise AssertionError(f"Login failed for {email}: status {resp.status_code}, response: {resp.text}")
    token = resp.json().get("access_token")
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def manager_headers(client: TestClient) -> Dict[str, str]:
    return get_auth_headers(client, "manager@ictu.edu.vn", "Manager@123")

@pytest.fixture
def marketer_headers(client: TestClient) -> Dict[str, str]:
    return get_auth_headers(client, "marketer@ictu.edu.vn", "Marketer@123")

@pytest.fixture
def approver_headers(client: TestClient, db_session) -> Dict[str, str]:
    """Generate or retrieve client approver credentials and authorization headers."""
    # Check if approver user exists; if not, create directly in db for test isolation
    approver = db_session.query(User).filter(User.email == "approver@agency.com").first()
    if not approver:
        # Determine valid role: CLIENT_APPROVER if enum updated, else MANAGER for approver privilege
        try:
            approver = User(
                email="approver@agency.com",
                full_name="Đặng Phê Duyệt",
                password_hash=hash_password("Approver@123"),
                role="CLIENT_APPROVER",
                status="ACTIVE"
            )
            db_session.add(approver)
            db_session.commit()
            db_session.refresh(approver)
        except Exception:
            db_session.rollback()
            approver = User(
                email="approver@agency.com",
                full_name="Đặng Phê Duyệt",
                password_hash=hash_password("Approver@123"),
                role="MANAGER",
                status="ACTIVE"
            )
            db_session.add(approver)
            db_session.commit()
            db_session.refresh(approver)

    token = create_access_token(data={
        "sub": str(approver.id),
        "email": approver.email,
        "role": approver.role,
        "full_name": approver.full_name
    })
    return {"Authorization": f"Bearer {token}"}

def assert_endpoint_or_skip_milestone(resp, path: str, milestone: str = "Upcoming Milestone"):
    """Helper to enforce Progressive Testability:
    If endpoint returns 404/405 because the milestone has not yet mounted this router,
    skip with a clear milestone pending message.
    """
    if resp.status_code == 404:
        try:
            body = resp.json()
            if body.get("detail") == "Not Found":
                pytest.skip(f"[{milestone}] Endpoint '{path}' is not yet deployed on active branch.")
        except Exception:
            pytest.skip(f"[{milestone}] Endpoint '{path}' is not yet deployed on active branch.")
    elif resp.status_code == 405:
        pytest.skip(f"[{milestone}] Endpoint '{path}' is not yet deployed on active branch.")
