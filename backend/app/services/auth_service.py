"""Đăng nhập, đăng ký, đăng xuất (thu hồi token), đổi mật khẩu."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import Conflict, PermissionDenied, Unauthorized, ValidationFailed
from app.core.security import (
    create_access_token,
    hash_password,
    login_rate_limiter,
    register_rate_limiter,
    validate_password_strength,
    verify_password,
)
from app.models import User
from app.models.enums import UserRole
from app.schemas.user import ChangePasswordIn, LoginIn, RegisterIn, TokenOut, UserOut


def _token_out(user: User) -> TokenOut:
    return TokenOut(access_token=create_access_token(user), user=UserOut.model_validate(user))


def login(db: Session, data: LoginIn, client_ip: str | None) -> TokenOut:
    key = f"{data.email}|{client_ip or '-'}"
    login_rate_limiter.check(key)
    user = db.execute(select(User).where(func.lower(User.email) == data.email)).scalar_one_or_none()
    if user is None or not verify_password(data.password, user.password_hash):
        login_rate_limiter.record_failure(key)
        raise Unauthorized("Email hoặc mật khẩu không đúng", code="INVALID_CREDENTIALS")
    if not user.is_active:
        raise PermissionDenied("Tài khoản đã bị khoá, vui lòng liên hệ quản lý", code="ACCOUNT_DISABLED")
    login_rate_limiter.reset(key)
    return _token_out(user)


def register(db: Session, data: RegisterIn, client_ip: str | None = None) -> TokenOut:
    if not settings.ALLOW_SELF_REGISTER:
        raise PermissionDenied(
            "Hệ thống không mở đăng ký tự do. Vui lòng liên hệ Quản lý để được cấp tài khoản.",
            code="REGISTER_DISABLED",
        )
    # Mỗi lượt đăng ký (thành công hay không) đều tính vào hạn mức theo IP, chống tạo hàng loạt tài khoản rác
    reg_key = f"register|{client_ip or '-'}"
    register_rate_limiter.check(reg_key)
    register_rate_limiter.record_failure(reg_key)
    problem = validate_password_strength(data.password)
    if problem:
        raise ValidationFailed(problem, fields={"password": problem})
    exists = db.execute(select(User.id).where(func.lower(User.email) == data.email)).first()
    if exists:
        raise Conflict("Email đã được sử dụng", code="EMAIL_EXISTS", fields={"email": "Email đã được sử dụng"})
    new_user = User(
        email=data.email,
        full_name=data.full_name,
        role=UserRole.MANAGER,
        password_hash=hash_password(data.password),
        is_active=True,
        token_version=0,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return _token_out(new_user)


def logout(db: Session, user: User) -> None:
    user.token_version = (user.token_version or 0) + 1
    db.commit()


def change_password(db: Session, user: User, data: ChangePasswordIn) -> TokenOut:
    if not verify_password(data.current_password, user.password_hash):
        raise ValidationFailed(
            "Mật khẩu hiện tại không đúng", fields={"current_password": "Mật khẩu hiện tại không đúng"}
        )
    problem = validate_password_strength(data.new_password)
    if problem:
        raise ValidationFailed(problem, fields={"new_password": problem})
    if data.new_password == data.current_password:
        msg = "Mật khẩu mới phải khác mật khẩu hiện tại"
        raise ValidationFailed(msg, fields={"new_password": msg})
    user.password_hash = hash_password(data.new_password)
    user.token_version = (user.token_version or 0) + 1
    db.commit()
    db.refresh(user)
    return _token_out(user)
