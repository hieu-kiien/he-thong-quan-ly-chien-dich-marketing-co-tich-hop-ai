"""Router xác thực: đăng nhập, đăng ký, đăng xuất, thông tin cá nhân, đổi mật khẩu."""

from __future__ import annotations

from fastapi import APIRouter, Request, status

from app.core.security import CurrentUser, DbSession
from app.schemas.common import Message
from app.schemas.user import ChangePasswordIn, LoginIn, RegisterIn, TokenOut, UserOut
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Xác thực"])


_LOOPBACK = {"127.0.0.1", "::1"}


def _client_ip(request: Request) -> str | None:
    """IP thật của client, dùng cho giới hạn đăng nhập/đăng ký.

    Chỉ tin các header proxy khi kết nối đến từ chính proxy của mình (loopback: cloudflared/nginx).
    Cloudflare tự đặt CF-Connecting-IP nên client không giả mạo được; X-Forwarded-For thì phần tử
    ĐẦU do client gửi nên không dùng — chỉ lấy phần tử CUỐI (do nginx của mình nối vào).
    """
    peer = request.client.host if request.client else None
    if peer in _LOOPBACK:
        for header in ("cf-connecting-ip", "x-real-ip"):
            value = request.headers.get(header)
            if value:
                return value.split(",")[0].strip()
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[-1].strip()
    return peer


@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, request: Request, db: DbSession) -> TokenOut:
    return auth_service.login(db, data, _client_ip(request))


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(data: RegisterIn, request: Request, db: DbSession) -> TokenOut:
    return auth_service.register(db, data, _client_ip(request))


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
