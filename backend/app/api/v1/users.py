"""Router quản lý người dùng (chỉ Quản lý marketing)."""

from __future__ import annotations

from fastapi import APIRouter, Query, status

from app.core.pagination import Page
from app.core.security import DbSession, ManagerUser
from app.models.enums import UserRole
from app.schemas.user import (
    ResetPasswordIn,
    UserCreate,
    UserFilters,
    UserOut,
    UserUpdate,
)
from app.services import user_service

router = APIRouter(prefix="/users", tags=["Người dùng"])


@router.get("", response_model=Page[UserOut])
def list_users(
    user: ManagerUser,
    db: DbSession,
    q: str | None = None,
    role: UserRole | None = None,
    is_active: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: str | None = None,
) -> Page[UserOut]:
    filters = UserFilters(q=q, role=role, is_active=is_active)
    return user_service.list_users(db, user, filters, page=page, page_size=page_size, sort=sort)


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(data: UserCreate, user: ManagerUser, db: DbSession) -> UserOut:
    return user_service.create_user(db, user, data)


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: int, data: UserUpdate, user: ManagerUser, db: DbSession) -> UserOut:
    return user_service.update_user(db, user, user_id, data)


@router.post("/{user_id}/reset-password", response_model=UserOut)
def reset_password(user_id: int, data: ResetPasswordIn, user: ManagerUser, db: DbSession) -> UserOut:
    return user_service.reset_password(db, user, user_id, data)
