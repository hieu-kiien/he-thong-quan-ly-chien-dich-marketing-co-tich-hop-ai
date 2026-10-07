from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
import ipaddress
import logging
import re
import threading
import time
from collections import defaultdict, deque
from contextlib import contextmanager
from contextvars import ContextVar
import bcrypt
import jwt

logger = logging.getLogger(__name__)
from fastapi import Depends, HTTPException, status
from fastapi import params
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

# Mạng được coi là proxy ngược đáng tin (loopback + docker/k8s private range).
# Mục đích: chỉ khi request đến từ một trong các mạng này thì mới chấp nhận giá trị
# X-Forwarded-For / CF-Connecting-IP. Nếu không kiểm tra, bất kỳ client nào cũng
# tự khai IP giả qua header và né được rate limit đăng nhập.
TRUSTED_PROXY_NETWORKS = tuple(
    ipaddress.ip_network(cidr)
    for cidr in ("127.0.0.0/8", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "::1/128")
)


def is_trusted_proxy(host: str) -> bool:
    """True nếu `host` nằm trong dải mạng nội bộ được coi là proxy ngược."""
    if not host:
        return False
    try:
        addr = ipaddress.ip_address(host.strip())
    except ValueError:
        return False
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped:
        addr = addr.ipv4_mapped
    return any(addr in net for net in TRUSTED_PROXY_NETWORKS)

# Định dạng bcrypt hợp lệ: $2<version>$<cost 2 chữ số>$<salt 22 ký tự><digest 31 ký tự>
_BCRYPT_RE = re.compile(r"^\$2[abxy]\$\d{2}\$[./A-Za-z0-9]{53}$")


def _is_bcrypt_hash_wellformed(raw: str) -> bool:
    """Chặn hash bcrypt hỏng TRƯỚC khi gọi checkpw.

    pyo3-bcrypt panic (không phải exception) khi salt/digest sai độ dài, nên phải
    kiểm tra định dạng bằng regex thay vì chỉ bắt lỗi.
    """
    return bool(_BCRYPT_RE.match(raw))


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
    if not _is_bcrypt_hash_wellformed(raw):
        logger.warning("[Security] stored hash is not a well-formed bcrypt hash; refusing login.")
        return False
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), raw.encode("utf-8"))
    except BaseException:
        # bcrypt (pyo3) panic trên hash hỏng là BaseException, không phải Exception.
        # Bắt BaseException để mọi lỗi bcrypt / hash dị thường đều fail-closed an toàn trả về False.
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
# Import dạng module (không phải `from app.core.database import SessionLocal`).
# `RoleChecker` tự mở session khi được gọi trực tiếp ngoài vòng đời request
# FastAPI. Nếu bind tên `SessionLocal` vào namespace của module này lúc import,
# thì việc conftest gán lại `core_database.SessionLocal` cho session kiểm thử sẽ
# không có tác dụng ở đây — RoleChecker âm thầm truy vấn CSDL thật (SQLite file
# hoặc Postgres production) thay vì CSDL test. Triệu chứng: test pass khi chạy
# cục bộ (CSDL thật tình cờ có bảng `users`) nhưng fail trên CI với
# "no such table: users".
from app.core import database as _database
from app.core.database import get_db
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

        # 1. Vai trò KHÔNG được đọc từ token. JWT là base64 không mã hoá, nên
        # `payload["role"]` là dữ liệu do client kiểm soát — tin vào nó là tin
        # dữ liệu không đáng tin. Vai trò thật được nạp từ DB ở bước 5.
        # Trước đây bước này chặn cả khi token thiếu `role`, buộc phải nhúng role
        # (và cả email/full_name) vào JWT chỉ để kiểm tra quyền: vừa lộ PII cho
        # mọi XSS đọc được từ localStorage, vừa cho phép token cũ giữ quyền cũ
        # sau khi admin đã hạ quyền người dùng.
        #
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
        # Khi gọi trực tiếp (ngoài vòng đời request của FastAPI, ví dụ trong test
        # hoặc script kiểm thử), tham số `db` vẫn là giá trị mặc định
        # `Depends(get_db)` — tức MỘT ĐỐI TƯỢNG Depends chứ không phải Session.
        # Kiểm tra `is None` như trước đây không bắt được trường hợp này và dẫn
        # tới AttributeError: 'Depends' object has no attribute 'query'.
        # Chỉ loại đúng `Depends` (không dùng isinstance(Session)) để vẫn giữ được
        # session giả/mock trong test, vốn chỉ cần interface `query`.
        if active_db is None or isinstance(active_db, params.Depends):
            # Đọc qua module để conftest gán session kiểm thử có tác dụng.
            active_db = _database.SessionLocal()
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


# --- Generic quota limiter (in-memory, per-process) ---------------------------------
# Dùng cho endpoint AI và đăng ký tài khoản. Trước đây KHÔNG endpoint nào được
# giới hạn: bất kỳ ai giữ token (hoặc khoá BYOK trong localStorage) đều có thể gọi
# /ai/draft liên tục và tiêu hết hạn mức của tổ chức.
# Cùng giới hạn với login: bộ nhớ trong tiến trình, chỉ là lớp phòng thủ bổ sung,
# không thay thế rate limiting ở reverse proxy / Cloudflare.
QUOTA_MAX_CALLS = 30
QUOTA_WINDOW_SECONDS = 60 * 60

# Cờ "hạn mứng đã được tính ở tầng khác".
#
# Job AI bất đồng bộ (POST /ai/jobs) chạy lại ĐÚNG endpoint đồng bộ, mà endpoint
# đó tự gọi `enforce_quota` ở đầu hàm. Nếu ta gọi `enforce_quota` thêm một lần ở
# lúc enqueue thì mỗi job bị tính HAI lần, tức hạn mứng 30 lượt/giờ chỉ còn ~15
# job/giờ mà không có gì giải thích được cho người dùng. `quota_already_enforced()`
# giải quyết đúng chỗ đó: tính một lần khi nhận job, rồi bọc lời gọi endpoint trong
# ngữ cảnh "đã tính rồi".
#
# Additif: không ai bọc context này thì `enforce_quota` y hệt cũ.
_quota_suppressed: ContextVar[bool] = ContextVar("marketflow_quota_suppressed", default=False)


@contextmanager
def quota_already_enforced():
    """Trong khối này, `enforce_quota` trở thành no-op (hạn mứng đã tiêu ở tầng API)."""
    token = _quota_suppressed.set(True)
    try:
        yield
    finally:
        _quota_suppressed.reset(token)

_quota_buckets: Dict[str, deque] = defaultdict(deque)
_quota_lock = threading.Lock()


def _prune_quota(now: float) -> None:
    cutoff = now - QUOTA_WINDOW_SECONDS
    for key in list(_quota_buckets.keys()):
        bucket = _quota_buckets.get(key)
        if not bucket:
            _quota_buckets.pop(key, None)
            continue
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        if not bucket:
            _quota_buckets.pop(key, None)


def enforce_quota(identifier: str, max_calls: int = QUOTA_MAX_CALLS, window_seconds: int = QUOTA_WINDOW_SECONDS) -> None:
    """Ném 429 nếu `identifier` đã vượt `max_calls` lần gọi trong cửa sổ thời gian.

    Gọi TRƯỚC khi thực hiện tác vụ tốn tài nguyên (gọi nhà cung cấp AI, tạo workspace).
    """
    if not identifier:
        return
    # Bỏ qua khi tiến trình đã tiêu hạn mứng ở tầng API xong (xem quota_already_enforced).
    if _quota_suppressed.get():
        return
    now = time.monotonic()
    retry_after = 0
    with _quota_lock:
        cutoff = now - window_seconds
        bucket = _quota_buckets[identifier]
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        if len(bucket) >= max_calls:
            retry_after = max(1, int(window_seconds - (now - bucket[0])))
            used = len(bucket)
    if retry_after:
        logger.warning("[Security] Quota exceeded for %s (used=%d, retry_after=%ds).", identifier, used, retry_after)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Bạn đã vượt giới hạn số lượt gọi. Vui lòng thử lại sau.",
            headers={"Retry-After": str(retry_after)},
        )
    with _quota_lock:
        _quota_buckets[identifier].append(now)


def reset_all_quotas() -> None:
    """Xoá toàn bộ bộ đếm quota trong bộ nhớ.

    Bộ đếm sống trong tiến trình và KHÔNG tự hết hạn theo test, nên nếu không có
    hàm này thì các test gọi API hàng loạt sẽ đụng trần của nhau và fail với 429
    một cách khó hiểu. Test fixture gọi hàm này giữa các test, tương đương cách
    DB được rollback cho dữ liệu.
    """
    with _quota_lock:
        _quota_buckets.clear()

