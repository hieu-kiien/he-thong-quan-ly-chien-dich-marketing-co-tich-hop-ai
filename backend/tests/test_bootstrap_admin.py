"""Test co che bootstrap ADMIN tu bien moi truong.

Trong khi khong co co che nay, moi endpoint gan ADMIN (ke ca /export/data)
khong bao gio goi duoc tren moi deployment, vi khong tai khoan ADMIN nao duoc tao.
"""

import pytest
from app.core import bootstrap_admin
from app.core.bootstrap_admin import MIN_PASSWORD_LENGTH, ensure_bootstrap_admin
from app.models.entities import User


def _env(monkeypatch, email, password, name=None):
    monkeypatch.setenv("BOOTSTRAP_ADMIN_EMAIL", email or "")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_PASSWORD", password or "")
    if name is not None:
        monkeypatch.setenv("BOOTSTRAP_ADMIN_NAME", name)


def test_skipped_when_env_empty(monkeypatch, db_session):
    """Khong co bien moi truong => khong tao gi."""
    _env(monkeypatch, None, None)
    assert ensure_bootstrap_admin(db_session) == "skipped"
    assert db_session.query(User).filter(User.role == "ADMIN").count() == 0


def test_skipped_when_email_but_no_password(monkeypatch, db_session):
    """Thieu mat khau thi BO QUA, khong tao account khong mat khau."""
    _env(monkeypatch, "boot@test.local", "")
    assert ensure_bootstrap_admin(db_session) == "skipped"
    assert db_session.query(User).filter(User.email == "boot@test.local").first() is None


def test_rejects_weak_password(monkeypatch, db_session):
    _env(monkeypatch, "boot@test.local", "short")
    assert ensure_bootstrap_admin(db_session) == "rejected_weak_password"
    assert db_session.query(User).filter(User.email == "boot@test.local").first() is None


def test_creates_admin(monkeypatch, db_session):
    pw = "Str0ng-Bootstrap-Pw-123"
    _env(monkeypatch, "Boot@Test.Local", pw, name="Boot Admin")

    assert ensure_bootstrap_admin(db_session) == "created"

    admin = db_session.query(User).filter(User.email == "boot@test.local").first()
    assert admin is not None
    # Email phai chuan hoa lowercase.
    assert admin.email == "boot@test.local"
    assert admin.role == "ADMIN"
    assert admin.status == "ACTIVE"
    assert admin.full_name == "Boot Admin"
    assert admin.password_hash != pw


def test_is_idempotent(monkeypatch, db_session):
    pw = "Str0ng-Bootstrap-Pw-123"
    _env(monkeypatch, "boot@test.local", pw)

    assert ensure_bootstrap_admin(db_session) == "created"
    assert ensure_bootstrap_admin(db_session) == "already_admin"
    assert db_session.query(User).filter(User.email == "boot@test.local").count() == 1


def test_never_demotes_existing_admin(monkeypatch, db_session):
    pw = "Str0ng-Bootstrap-Pw-123"
    _env(monkeypatch, "boot@test.local", pw)
    ensure_bootstrap_admin(db_session)

    # Mat khau doi trong bien moi truong => KHONG duoc demote admin hien huu.
    _env(monkeypatch, "boot@test.local", "An0ther-Str0ng-Pw-999")
    assert ensure_bootstrap_admin(db_session) == "already_admin"

    admin = db_session.query(User).filter(User.email == "boot@test.local").first()
    assert admin.role == "ADMIN"


def test_conflicts_with_existing_non_admin(monkeypatch, db_session):
    """Email da cap cho user thuong thi KHONG duoc tu demote len ADMIN."""
    existing = User(
        email="taken@test.local",
        full_name="Existing",
        password_hash="x",
        role="MARKETER",
        status="ACTIVE",
    )
    db_session.add(existing)
    db_session.commit()

    _env(monkeypatch, "taken@test.local", "Str0ng-Bootstrap-Pw-123")
    assert ensure_bootstrap_admin(db_session) == "conflict_email_in_use"

    still = db_session.query(User).filter(User.email == "taken@test.local").first()
    assert still.role == "MARKETER"


def test_password_length_constant_is_enforced(monkeypatch, db_session):
    _env(monkeypatch, "boot@test.local", "a" * (MIN_PASSWORD_LENGTH - 1))
    assert ensure_bootstrap_admin(db_session) == "rejected_weak_password"


def test_settings_expose_bootstrap_fields():
    from app.core.config import Settings

    s = Settings()
    assert hasattr(s, "BOOTSTRAP_ADMIN_EMAIL")
    assert hasattr(s, "BOOTSTRAP_ADMIN_PASSWORD")
    assert hasattr(s, "BOOTSTRAP_ADMIN_NAME")


def test_default_settings_bootstrap_is_inert():
    """Mac dinh phai la rong -> moi cai dat moi khong bi dot nhieu ADMIN."""
    from app.core.config import Settings

    s = Settings()
    if not s.BOOTSTRAP_ADMIN_EMAIL:
        assert s.BOOTSTRAP_ADMIN_PASSWORD is None
