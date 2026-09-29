from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
import logging
import threading
import time
from collections import defaultdict, deque
import bcrypt
import jwt

logger = logging.getLogger(__name__)
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings
from app.core.crypto import (
    get_jwt_secret_key,
    get_byok_encryption_key,
    get_fernet_cipher,
    get_multi_fernet,
    encrypt_api_key,
    decrypt_api_key,
    mask_api_key,
    rotate_custom_api_keys,
)

security_bearer = HTTPBearer(auto_error=False)

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Xác minh mật khẩu bằng bcrypt.

    KHÔNG BAO GIỜ có đường fallback trả về True khi bcrypt lỗi: đó là đường
    vòng bỏ xác thực. Mọi lỗi bcrypt đều coi là thất bại đăng nhập.
    """
    if not plain_password or not hashed_password:
        return False
    raw = hashed_password.strip()
    if raw.startswith(("$2a$", "$2b$", "$2y$")):
        pass
    elif raw.startswith(("$2$",)):
        return False
    else:
        raw = "$2b$" + raw
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), raw.encode("utf-8"))
    except Exception:
        # Bắt tất cả exception để mọi lỗi bcrypt / hash dị thường đều fail-closed an toàn trả về False
        logger.warning("[Security] bcrypt rejected stored hash format; refusing login.")
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    secret_key = get_jwt_secret_key()
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> dict:
    try:
        secret_key = get_jwt_secret_key()
        payload = jwt.decode(token, secret_key, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ hoặc đã hết hạn",
            headers={"WWW-Authenticate": "Bearer"},
        )

from sqlalchemy.orm import Session
from app.core.database import get_db, SessionLocal
from app.models.entities import User

class UserStatus:
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"

class RoleChecker:
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(
        self,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
        db: Optional[Session] = Depends(get_db)
    ):
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Yêu cầu xác thực đăng nhập (Thiếu Bearer Token)",
                headers={"WWW-Authenticate": "Bearer"},
            )
        token = credentials.credentials
        payload = decode_access_token(token)

        # 1. Kiểm tra trường role trong token payload
        token_role = payload.get("role")
        if not token_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Thao tác trái quyền. Quyền yêu cầu: {', '.join(self.allowed_roles)}, quyền hiện tại: {token_role}",
            )
        if token_role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Thao tác trái quyền. Quyền yêu cầu: {', '.join(self.allowed_roles)}, quyền hiện tại: {token_role}",
            )

        # 2. Bắt buộc có trường "sub" không rỗng trong payload
        sub = payload.get("sub")
        if sub is None or str(sub).strip() == "":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token không chứa định danh người dùng (sub)",
                headers={"WWW-Authenticate": "Bearer"},
            )

        sub_str = str(sub).strip()

        # Quản lý Database Session (hỗ trợ cả FastAPI injection và standalone call)
        close_db = False
        active_db = db
        if active_db is None:
            active_db = SessionLocal()
            close_db = True

        try:
            # 3. Load user từ Database theo id hoặc email
            user = None
            try:
                user_id = int(sub_str)
                user = active_db.query(User).filter(User.id == user_id).first()
            except (ValueError, TypeError):
                if "@" in sub_str:
                    user = active_db.query(User).filter(User.email == sub_str).first()
                else:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Định danh người dùng trong Token không hợp lệ",
                        headers={"WWW-Authenticate": "Bearer"},
                    )

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Người dùng không tồn tại trong hệ thống",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # 4. Xác minh user.status == UserStatus.ACTIVE
            if user.status != UserStatus.ACTIVE:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User account is not active (inactive or suspended) (Tài khoản đã bị vô hiệu hóa)",
                )

            # 5. So sánh vai trò thực tế trong Database với allowed_roles (không tin payload role)
            if user.role not in self.allowed_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Thao tác trái quyền. Quyền yêu cầu: {', '.join(self.allowed_roles)}, quyền thực tế của người dùng: {user.role}",
                )

            payload["sub"] = str(user.id)
            payload["role"] = user.role
            payload["db_user"] = user

        finally:
            if close_db:
                active_db.close()

        return payload

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    db: Session = Depends(get_db)
) -> User:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Yêu cầu xác thực đăng nhập (Thiếu Bearer Token)",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(credentials.credentials)
    sub = payload.get("sub")
    if sub is None or str(sub).strip() == "":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không chứa định danh người dùng",
            headers={"WWW-Authenticate": "Bearer"},
        )
    sub_str = str(sub).strip()
    user = None
    try:
        user_id = int(sub_str)
        user = db.query(User).filter(User.id == user_id).first()
    except (ValueError, TypeError):
        if "@" in sub_str:
            user = db.query(User).filter(User.email == sub_str).first()
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Định danh người dùng trong Token không hợp lệ",
                headers={"WWW-Authenticate": "Bearer"},
            )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Người dùng không tồn tại",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not active (inactive or suspended) (Tài khoản đã bị vô hiệu hóa)"
        )

    return user


# --- Login rate limiting (in-memory, per-process) ---------------------------------
# Chống brute-force ở tầng ứng dụng: tối đa LOGIN_MAX_ATTEMPTS lần sai trong
# LOGIN_RATE_LIMIT_WINDOW_SECONDS cho mỗi khoá (email, client host).
# KHÔNG dùng thư viện ngoài. Lưu ý: bộ nhớ trong tiến trình, nên khi chạy nhiều
# worker/instance thì mỗi instance có bộ đếm riêng; đây chỉ là lớp phòng thủ
# bổ sung, không thay thế rate limiting ở tầng reverse proxy / Cloudflare.
LOGIN_MAX_ATTEMPTS = 5
LOGIN_RATE_LIMIT_WINDOW_SECONDS = 15 * 60

_login_attempts: Dict[str, deque] = defaultdict(deque)
# Uvicorn/Gunicorn chạy nhiều thread trong cùng tiến trình; deque.append/popleft là
# atomic nhưng thao tác "đọc bộ đếm -> quyết định -> ghi" thì không. Lock giữ cho
# việc kiểm đếm và ghi nhận là nguyên tử, tránh kẻ tấn công lách được ngạch bằng
# việc gửi song song nhiều request.
_login_attempts_lock = threading.Lock()


def _prune_login_attempts(now: float) -> None:
    """Dọn các khoá đã hết cửa sổ để tránh rò rỉ bộ nhớ theo thời gian."""
    cutoff = now - LOGIN_RATE_LIMIT_WINDOW_SECONDS
    for key in list(_login_attempts.keys()):
        bucket = _login_attempts.get(key)
        if not bucket:
            _login_attempts.pop(key, None)
            continue
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        if not bucket:
            _login_attempts.pop(key, None)


def check_login_rate_limit(identifier: str) -> None:
    """Ném HTTPException(429) nếu khoá (email, host) đã vượt ngạch thử sai.

    Gọi hàm này TRƯỚC khi kiểm tra mật khẩu trong endpoint đăng nhập.
    """
    if not identifier:
        return
    now = time.monotonic()
    retry_after = 0
    with _login_attempts_lock:
        _prune_login_attempts(now)
        bucket = _login_attempts.get(identifier)
        if bucket and len(bucket) >= LOGIN_MAX_ATTEMPTS:
            retry_after = max(1, int(LOGIN_RATE_LIMIT_WINDOW_SECONDS - (now - bucket[0])))
            attempts = len(bucket)
    if retry_after:
        logger.warning(
            "[Security] Login rate limit triggered for %s (attempts=%d, retry_after=%ds).",
            identifier, attempts, retry_after,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Bạn đã đăng nhập sai quá nhiều lần. Vui lòng thử lại sau.",
            headers={"Retry-After": str(retry_after)},
        )


def record_login_failure(identifier: str) -> None:
    """Ghi nhận một lần đăng nhập sai cho khoá (email, host)."""
    if not identifier:
        return
    now = time.monotonic()
    with _login_attempts_lock:
        _prune_login_attempts(now)
        _login_attempts[identifier].append(now)


def reset_login_rate_limit(identifier: str) -> None:
    """Xoá bộ đếm sau khi đăng nhập thành công."""
    if not identifier:
        return
    with _login_attempts_lock:
        _login_attempts.pop(identifier, None)

