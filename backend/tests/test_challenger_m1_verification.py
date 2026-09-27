"""Empirical Verification & Adversarial Stress Tests for Milestone M1.

Milestone: Deployment Infrastructure, Zero Cold-Start DB & Legacy Auth Purge.
Tested items:
1. Auto-seeding on fresh empty DB (isolated in-memory SQLite engine).
2. Auth endpoint rejection of legacy @ictu.edu.vn credentials (strict 401, no silent rewrite).
3. Auth login with modern @gmail.com credentials (HTTP 200 + valid JWT claims).
4. Idempotency of seed_data and zero cold-start resilience.
5. Auth negative and adversarial vectors (bad password, SQL injection, duplicate email, privilege escalation).
"""

import jwt
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import Base, init_db
from app.core.security import verify_password
from app.models.entities import (
    User, Workspace, WorkspaceMember, BrandKit,
    ProductCategory, Product, MarketingChannel
)
from seed.seed_data import seed_data


def test_auto_seeding_on_fresh_isolated_db():
    """Verify that init_db and seed_data auto-populate all demo entities on a clean empty database."""
    # 1. Khởi tạo một SQLite in-memory engine hoàn toàn cô lập
    isolated_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    IsolatedSession = sessionmaker(autocommit=False, autoflush=False, bind=isolated_engine)

    # 2. Chạy init_db và kiểm tra CSDL rỗng trước seed
    init_db(isolated_engine)
    session = IsolatedSession()
    try:
        assert session.query(User).count() == 0, "Clean DB must start with 0 users"
        assert session.query(Workspace).count() == 0, "Clean DB must start with 0 workspaces"

        # 3. Chạy seed_data trên session cô lập
        seed_data(session=session)

        # 4. Kiểm chứng các tài khoản demo chuẩn @gmail.com
        manager = session.query(User).filter(User.email == "manager@gmail.com").first()
        assert manager is not None, "manager@gmail.com must exist after seeding"
        assert manager.role == "MANAGER"
        assert manager.status == "ACTIVE"
        assert manager.full_name == "Nguyễn Văn Quản Lý"
        assert verify_password("Manager@123", manager.password_hash) is True, "Manager password hash verification failed"

        marketer = session.query(User).filter(User.email == "marketer@gmail.com").first()
        assert marketer is not None, "marketer@gmail.com must exist after seeding"
        assert marketer.role == "MARKETER"
        assert marketer.status == "ACTIVE"
        assert marketer.full_name == "Trần Thị Marketing"
        assert verify_password("Marketer@123", marketer.password_hash) is True, "Marketer password hash verification failed"

        approver = session.query(User).filter(User.email == "approver@gmail.com").first()
        assert approver is not None, "approver@gmail.com must exist after seeding"
        assert approver.role == "CLIENT_APPROVER"
        assert approver.status == "ACTIVE"
        assert approver.full_name == "Đại Diện Khách Hàng (Approver)"
        assert verify_password("Approver@123", approver.password_hash) is True, "Approver password hash verification failed"

        # 5. Kiểm chứng Workspace mặc định và Brand Kit
        default_ws = session.query(Workspace).filter(Workspace.id == 1).first()
        if not default_ws:
            default_ws = session.query(Workspace).filter(Workspace.slug == "default-agency").first()
        assert default_ws is not None, "Default agency workspace must exist"
        assert default_ws.name == "Default Agency Workspace"
        assert default_ws.owner_id == manager.id
        assert default_ws.status == "ACTIVE"

        brand_kit = session.query(BrandKit).filter(BrandKit.workspace_id == default_ws.id).first()
        assert brand_kit is not None, "Default brand kit must exist for workspace"
        assert brand_kit.brand_name == "MarketFlow AI"

        # 6. Kiểm chứng danh mục, sản phẩm, kênh tiếp thị
        assert session.query(ProductCategory).count() >= 2, "Default categories must be seeded"
        assert session.query(Product).count() >= 2, "Default products must be seeded"
        assert session.query(MarketingChannel).count() >= 3, "Default channels must be seeded"

        # 7. Stress-test Idempotency: Chạy seed_data lần 2 trên cùng CSDL
        seed_data(session=session)
        assert session.query(User).count() == 3, "Idempotent re-seed must not duplicate users"
        assert session.query(Workspace).count() == 1, "Idempotent re-seed must not duplicate workspace"
    finally:
        session.close()
        isolated_engine.dispose()


def test_auth_login_rejects_legacy_ictu_credentials(client: TestClient):
    """Stress-test legacy @ictu.edu.vn authentication.
    Verifies that requests with @ictu.edu.vn are NOT silently rewritten to @gmail.com
    and are strictly rejected with HTTP 401 Unauthorized.
    """
    legacy_payloads = [
        {"email": "manager@ictu.edu.vn", "password": "Manager@123"},
        {"email": "marketer@ictu.edu.vn", "password": "Marketer@123"},
        {"email": "approver@ictu.edu.vn", "password": "Approver@123"},
        {"email": "unknown@ictu.edu.vn", "password": "AnyPassword123"},
    ]

    for payload in legacy_payloads:
        resp = client.post("/api/v1/auth/login", json=payload)
        assert resp.status_code == 401, (
            f"Expected HTTP 401 for legacy email '{payload['email']}', but got {resp.status_code}: {resp.text}"
        )
        data = resp.json()
        assert "detail" in data
        assert data["detail"] == "Email hoặc mật khẩu không chính xác"


def test_auth_login_succeeds_with_gmail_credentials(client: TestClient):
    """Empirically verify login with modern @gmail.com demo accounts and check JWT token."""
    from app.core.security import decode_access_token

    accounts = [
        ("manager@gmail.com", "Manager@123", "MANAGER", "Nguyễn Văn Quản Lý"),
        ("marketer@gmail.com", "Marketer@123", "MARKETER", "Trần Thị Marketing"),
        ("approver@gmail.com", "Approver@123", "CLIENT_APPROVER", "Đại Diện Khách Hàng (Approver)"),
    ]

    for email, password, expected_role, expected_name in accounts:
        resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
        data = resp.json()

        # Check response structure
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == email
        assert data["user"]["role"] == expected_role
        assert data["user"]["full_name"] == expected_name

        # Verify JWT cryptographic payload claims via decode_access_token
        token = data["access_token"]
        payload = decode_access_token(token)
        assert payload["email"] == email
        assert payload["role"] == expected_role
        assert payload["full_name"] == expected_name
        assert "exp" in payload
        assert "sub" in payload


def test_auth_negative_and_adversarial_vectors(client: TestClient):
    """Adversarial stress-testing on authentication endpoints."""
    # 1. Invalid password for valid user
    resp = client.post("/api/v1/auth/login", json={"email": "manager@gmail.com", "password": "WrongPassword!999"})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Email hoặc mật khẩu không chính xác"

    # 2. Malformed email (Pydantic schema validation rejects with HTTP 422 before reaching DB)
    resp = client.post("/api/v1/auth/login", json={"email": "' OR '1'='1' --", "password": "anything"})
    assert resp.status_code == 422

    # 2b. Syntactically valid email containing SQL injection attempt (handled safely without error, returns 401)
    resp = client.post("/api/v1/auth/login", json={"email": "sqli_attack@example.com", "password": "' OR '1'='1"})
    assert resp.status_code == 401

    # 3. Duplicate email registration rejected with HTTP 400
    resp = client.post("/api/v1/auth/register", json={
        "email": "manager@gmail.com",
        "password": "NewPassword@123",
        "full_name": "Duplicate Tester"
    })
    assert resp.status_code == 400
    assert "đã được sử dụng" in resp.json()["detail"]

    # 4. Privilege escalation on self-registration rejected with HTTP 403
    for prohibited_role in ["AGENCY_MANAGER", "CLIENT_APPROVER", "ADMIN", "MANAGER"]:
        resp = client.post("/api/v1/auth/register", json={
            "email": f"hacker_{prohibited_role.lower()}@test.com",
            "password": "Password123!",
            "full_name": "Hacker Escalate",
            "role": prohibited_role
        })
        assert resp.status_code == 403, f"Self-registration with role {prohibited_role} must be rejected with 403"
        assert "Privilege Escalation" in resp.json()["detail"] or "not allowed" in resp.json()["detail"]

    # 5. Legitimate new registration succeeds with HTTP 201 and auto-provisions workspace
    resp = client.post("/api/v1/auth/register", json={
        "email": "genuine_marketer@company.vn",
        "password": "ValidPassword@123",
        "full_name": "Nguyễn Văn Thật",
        "role": "MARKETER"
    })
    assert resp.status_code == 201
    reg_data = resp.json()
    assert reg_data["email"] == "genuine_marketer@company.vn"
    assert reg_data["role"] == "MARKETER"
