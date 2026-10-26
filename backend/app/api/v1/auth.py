"""Router xác thực: đăng nhập, đăng xuất, thông tin cá nhân, đổi mật khẩu."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.core.security import CurrentUser, DbSession
from app.schemas.common import Message
from app.schemas.user import ChangePasswordIn, LoginIn, TokenOut, UserOut
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Xác thực"])


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, request: Request, db: DbSession) -> TokenOut:
    return auth_service.login(db, data, _client_ip(request))


@router.get("/me", response_model=UserOut)
def get_me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)


@router.post("/logout", response_model=Message)
def logout(user: CurrentUser, db: DbSession) -> Message:
    auth_service.logout(db, user)
    return Message(message="Đã đăng xuất thành công")


@router.post("/change-password", response_model=TokenOut)
def change_password(data: ChangePasswordIn, user: CurrentUser, db: DbSession) -> TokenOut:
    return auth_service.change_password(db, user, data)
