"""Mật khẩu (bcrypt), JWT truy cập, dependency xác thực và giới hạn đăng nhập sai."""

from __future__ import annotations

import re
import threading
import time
from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

import bcrypt
import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.errors import PermissionDenied, RateLimited, Unauthorized
from app.models.user import User

ACCESS_TOKEN_TYPE = "access"

_bearer = HTTPBearer(auto_error=False)
_BCRYPT_RE = re.compile(r"^\$2[aby]\$\d{2}\$[./A-Za-z0-9]{53}$")


# --- Mật khẩu -----------------------------------------------------------------

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """So khớp bcrypt, mọi lỗi (hash hỏng...) đều coi là sai mật khẩu (fail-closed)."""
    if not plain_password or not hashed_password:
        return False
    raw = hashed_password.strip()
    if not _BCRYPT_RE.match(raw):
        return False
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), raw.encode("utf-8"))
    except BaseException:  # noqa: BLE001 - pyo3 panic là BaseException
        return False


def validate_password_strength(password: str) -> str | None:
    """Trả về thông báo lỗi tiếng Việt nếu mật khẩu yếu, None nếu hợp lệ."""
    if len(password) < 8:
        return "Mật khẩu tối thiểu 8 ký tự"
    if len(password) > 128:
        return "Mật khẩu tối đa 128 ký tự"
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        return "Mật khẩu phải có cả chữ và số"
    return None


# --- JWT ----------------------------------------------------------------------

def create_access_token(user: User, expires_minutes: int | None = None) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user.id),
        "tv": user.token_version or 0,
        "typ": ACCESS_TOKEN_TYPE,
        "iat": int(now.timestamp()),
        "exp": now + timedelta(minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def encode_token(payload: dict[str, Any]) -> str:
    """Ký một JWT tuỳ ý bằng JWT_SECRET (dùng cho run-token của trợ lý)."""
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise Unauthorized("Phiên đăng nhập đã hết hạn, vui lòng đăng nhập lại", code="TOKEN_EXPIRED") from exc
    except jwt.PyJWTError as exc:
        raise Unauthorized("Token không hợp lệ", code="INVALID_TOKEN") from exc


def user_from_token(db: Session, token: str) -> User:
    payload = decode_token(token)
    if payload.get("typ") != ACCESS_TOKEN_TYPE:
        raise Unauthorized("Token không hợp lệ", code="INVALID_TOKEN")
    try:
        user_id = int(payload.get("sub"))
        token_version = int(payload.get("tv"))
    except (TypeError, ValueError) as exc:
        raise Unauthorized("Token không hợp lệ", code="INVALID_TOKEN") from exc
    user = db.get(User, user_id)
    if user is None:
        raise Unauthorized("Tài khoản không tồn tại", code="INVALID_TOKEN")
    if not user.is_active:
        raise Unauthorized("Tài khoản đã bị khoá", code="ACCOUNT_DISABLED")
    if token_version != (user.token_version or 0):
        raise Unauthorized("Phiên đăng nhập đã bị thu hồi, vui lòng đăng nhập lại", code="TOKEN_REVOKED")
    return user


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise Unauthorized(headers={"WWW-Authenticate": "Bearer"})
    return user_from_token(db, credentials.credentials)


def require_manager(user: Annotated[User, Depends(get_current_user)]) -> User:
    if not user.is_manager:
        raise PermissionDenied("Chỉ Quản lý marketing được thực hiện thao tác này")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
ManagerUser = Annotated[User, Depends(require_manager)]
DbSession = Annotated[Session, Depends(get_db)]


# --- Giới hạn đăng nhập sai (bộ nhớ trong tiến trình) ---------------------------

class LoginRateLimiter:
    """Tối đa `max_failures` lần sai trong `window` giây cho mỗi khoá email+IP."""

    def __init__(
        self,
        max_failures: int,
        window_seconds: int,
        message: str | None = None,
        code: str = "LOGIN_RATE_LIMITED",
    ) -> None:
        self.max_failures = max_failures
        self.window = window_seconds
        self.message = message
        self.code = code
        self._failures: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> deque[float]:
        bucket = self._failures[key]
        while bucket and bucket[0] <= now - self.window:
            bucket.popleft()
        return bucket

    def check(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            bucket = self._prune(key, now)
            if len(bucket) >= self.max_failures:
                retry_after = max(1, int(self.window - (now - bucket[0])))
            else:
                retry_after = 0
                if not bucket:
                    self._failures.pop(key, None)
        if retry_after:
            wait = f"{max(1, retry_after // 60)} phút"
            raise RateLimited(
                f"{self.message} Vui lòng thử lại sau {wait}."
                if self.message
                else f"Bạn đã đăng nhập sai quá nhiều lần. Vui lòng thử lại sau {wait}.",
                code=self.code,
                headers={"Retry-After": str(retry_after)},
            )

    MAX_KEYS = 10_000

    def record_failure(self, key: str) -> None:
        with self._lock:
            now = time.monotonic()
            self._prune(key, now).append(now)
            if len(self._failures) > self.MAX_KEYS:
                # Chặn tăng bộ nhớ vô hạn (vd tấn công đổi email/IP liên tục): bỏ bucket đã hết hạn,
                # nếu vẫn quá nhiều thì bỏ các bucket cũ nhất.
                for k in [k for k, b in self._failures.items() if not b or b[-1] <= now - self.window]:
                    del self._failures[k]
                while len(self._failures) > self.MAX_KEYS:
                    del self._failures[next(iter(self._failures))]

    def reset(self, key: str | None = None) -> None:
        with self._lock:
            if key is None:
                self._failures.clear()
            else:
                self._failures.pop(key, None)


login_rate_limiter = LoginRateLimiter(settings.LOGIN_MAX_FAILURES, settings.LOGIN_WINDOW_SECONDS)
register_rate_limiter = LoginRateLimiter(
    settings.REGISTER_MAX_PER_HOUR,
    60 * 60,
    message="Bạn đã đăng ký quá nhiều tài khoản từ địa chỉ này.",
    code="REGISTER_RATE_LIMITED",
)
