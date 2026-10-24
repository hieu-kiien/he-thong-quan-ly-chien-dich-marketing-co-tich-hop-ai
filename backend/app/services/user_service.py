"""Quản lý người dùng (chỉ MANAGER)."""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import Conflict, PermissionDenied, ValidationFailed
from app.core.pagination import Page, apply_sort, paginate
from app.core.security import hash_password, validate_password_strength
from app.models import User
from app.models.enums import UserRole
from app.schemas.user import (
    ResetPasswordIn,
    UserCreate,
    UserFilters,
    UserOut,
    UserUpdate,
)
from app.services.common import get_or_404, like_pattern


def _require_manager(user: User) -> None:
    if not user.is_manager:
        raise PermissionDenied("Chỉ Quản lý marketing được quản lý người dùng")


def list_users(
    db: Session, user: User, filters: UserFilters, page: int = 1, page_size: int = 20, sort: str | None = None
) -> Page[UserOut]:
    _require_manager(user)
    stmt = select(User)
    if filters.q:
        pattern = like_pattern(filters.q)
        stmt = stmt.where(or_(User.email.ilike(pattern, escape="\\"), User.full_name.ilike(pattern, escape="\\")))
    if filters.role:
        stmt = stmt.where(User.role == filters.role)
    if filters.is_active is not None:
        stmt = stmt.where(User.is_active == filters.is_active)
    stmt = apply_sort(
        stmt,
        sort,
        {"full_name": User.full_name, "email": User.email, "created_at": User.created_at, "role": User.role},
        "full_name",
        User.id,
    )
    items, total = paginate(db, stmt, page, page_size)
    return Page[UserOut](
        items=[UserOut.model_validate(u) for u in items], total=total, page=page, page_size=page_size
    )


def list_active_user_refs(db: Session) -> list[User]:
    return list(db.execute(select(User).where(User.is_active.is_(True)).order_by(User.full_name)).scalars())


def create_user(db: Session, user: User, data: UserCreate) -> UserOut:
    _require_manager(user)
    problem = validate_password_strength(data.password)
    if problem:
        raise ValidationFailed(problem, fields={"password": problem})
    exists = db.execute(select(User.id).where(func.lower(User.email) == data.email)).first()
    if exists:
        raise Conflict("Email đã được sử dụng", code="EMAIL_EXISTS", fields={"email": "Email đã được sử dụng"})
    new_user = User(
        email=data.email,
        full_name=data.full_name,
        role=data.role,
        password_hash=hash_password(data.password),
        is_active=True,
        token_version=0,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return UserOut.model_validate(new_user)


def update_user(db: Session, user: User, user_id: int, data: UserUpdate) -> UserOut:
    _require_manager(user)
    target = get_or_404(db, User, user_id, "Không tìm thấy người dùng")
    if target.id == user.id:
        if data.role is not None and data.role != UserRole.MANAGER:
            raise PermissionDenied("Bạn không thể tự hạ quyền của chính mình", code="CANNOT_MODIFY_SELF")
        if data.is_active is False:
            raise PermissionDenied("Bạn không thể tự khoá tài khoản của chính mình", code="CANNOT_MODIFY_SELF")
    if data.full_name is not None:
        target.full_name = data.full_name
    if data.role is not None:
        target.role = data.role
    if data.is_active is not None and data.is_active != target.is_active:
        target.is_active = data.is_active
        if not data.is_active:
            target.token_version = (target.token_version or 0) + 1
    db.commit()
    db.refresh(target)
    return UserOut.model_validate(target)


def reset_password(db: Session, user: User, user_id: int, data: ResetPasswordIn) -> UserOut:
    _require_manager(user)
    target = get_or_404(db, User, user_id, "Không tìm thấy người dùng")
    problem = validate_password_strength(data.new_password)
    if problem:
        raise ValidationFailed(problem, fields={"new_password": problem})
    target.password_hash = hash_password(data.new_password)
    target.token_version = (target.token_version or 0) + 1
    db.commit()
    db.refresh(target)
    return UserOut.model_validate(target)


def get_active_user(db: Session, user_id: int, field: str = "assignee_id") -> User:
    target = db.get(User, user_id)
    if target is None or not target.is_active:
        raise ValidationFailed(fields={field: "Người dùng không tồn tại hoặc đã bị khoá"})
    return target


def active_manager_ids(db: Session) -> list[int]:
    return list(
        db.execute(
            select(User.id).where(User.role == UserRole.MANAGER, User.is_active.is_(True))
        ).scalars()
    )
