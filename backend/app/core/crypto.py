"""Module mã hóa đối xứng an toàn cho Enterprise BYOK Vault (FEAT-BE-23).
Sử dụng Fernet (AES-128-CBC + HMAC-SHA256) kết hợp PBKDF2HMAC Key Derivation.
Cung cấp khả năng chống can thiệp (Tamper Resistance), che giấu mặt nạ khóa an toàn,
tách biệt JWT Secret khỏi BYOK Encryption Key và hỗ trợ xoay vòng khóa qua MultiFernet.
"""

import base64
import logging
from typing import Optional, List, Union
from cryptography.fernet import Fernet, MultiFernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from sqlalchemy.orm import Session

from app.core.config import settings

logger = logging.getLogger(__name__)

# Salt cố định cho việc dẫn xuất khóa Fernet vault
VAULT_SALT = b"marketflow-byok-vault-pbkdf2-salt-v1"


def get_jwt_secret_key() -> str:
    """Trả về secret key dùng cho JWT HMAC-SHA256 signing & verification.
    Ưu tiên settings.JWT_SECRET_KEY, fallback về settings.SECRET_KEY.
    """
    jwt_key = getattr(settings, "JWT_SECRET_KEY", None)
    if jwt_key and str(jwt_key).strip():
        return str(jwt_key).strip()
    return settings.SECRET_KEY


def _derive_fernet_key(passphrase: str, salt: bytes = VAULT_SALT) -> bytes:
    """Dẫn xuất 32-byte URL-safe base64 key từ passphrase thông qua PBKDF2HMAC SHA-256."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100_000,
    )
    return base64.urlsafe_b64encode(kdf.derive(passphrase.encode("utf-8")))


def _format_or_derive_fernet_key(key_input: Union[str, bytes]) -> bytes:
    """Chuẩn hóa khóa đầu vào về 32-byte URL-safe base64 bytes.
    Nếu đã là URL-safe base64 32-byte (44 ký tự), sử dụng trực tiếp.
    Nếu là passphrase tự do, dẫn xuất qua PBKDF2HMAC.
    """
    if isinstance(key_input, bytes):
        raw_str = key_input.decode("utf-8", errors="ignore").strip()
    else:
        raw_str = str(key_input).strip()

    if len(raw_str) == 44:
        try:
            decoded = base64.urlsafe_b64decode(raw_str.encode("utf-8"))
            if len(decoded) == 32:
                return raw_str.encode("utf-8")
        except Exception:
            pass

    return _derive_fernet_key(raw_str)


def get_byok_encryption_key() -> bytes:
    """Trả về khóa mã hóa BYOK chính (primary key) dạng 32-byte URL-safe base64 bytes.
    Ưu tiên settings.BYOK_ENCRYPTION_KEY, fallback về settings.SECRET_KEY.
    """
    byok_key = getattr(settings, "BYOK_ENCRYPTION_KEY", None)
    if byok_key and str(byok_key).strip():
        return _format_or_derive_fernet_key(str(byok_key).strip())
    return _derive_fernet_key(settings.SECRET_KEY)


def _get_rotation_keys() -> List[bytes]:
    """Phân tích danh sách các khóa xoay vòng / fallback trong settings.BYOK_ROTATION_KEYS."""
    rotation_str = getattr(settings, "BYOK_ROTATION_KEYS", None)
    keys: List[bytes] = []
    if not rotation_str or not str(rotation_str).strip():
        return keys

    raw_items: List[str] = []
    cleaned_str = str(rotation_str).strip()
    if cleaned_str.startswith("[") and cleaned_str.endswith("]"):
        try:
            import json
            parsed = json.loads(cleaned_str)
            if isinstance(parsed, list):
                raw_items = [str(x).strip() for x in parsed if x]
        except Exception:
            raw_items = [x.strip() for x in cleaned_str.strip("[]").split(",") if x.strip()]
    else:
        raw_items = [x.strip() for x in cleaned_str.split(",") if x.strip()]

    for item in raw_items:
        if item:
            keys.append(_format_or_derive_fernet_key(item))
    return keys


def get_multi_fernet() -> MultiFernet:
    """Khởi tạo MultiFernet KeyRing hỗ trợ xoay vòng khóa (Key Rotation).
    Khóa đầu tiên (index 0) luôn là primary key dùng để mã hóa mới.
    Các khóa tiếp theo là fallback keys để giải mã dữ liệu cũ.
    """
    primary_key = get_byok_encryption_key()
    fernets = [Fernet(primary_key)]
    seen_keys = {primary_key}

    for rot_key in _get_rotation_keys():
        if rot_key not in seen_keys:
            fernets.append(Fernet(rot_key))
            seen_keys.add(rot_key)

    # Tự động hỗ trợ giải mã từ SECRET_KEY cũ nếu BYOK_ENCRYPTION_KEY khác biệt
    legacy_secret_key = _derive_fernet_key(settings.SECRET_KEY)
    if legacy_secret_key not in seen_keys:
        fernets.append(Fernet(legacy_secret_key))
        seen_keys.add(legacy_secret_key)

    return MultiFernet(fernets)


def get_fernet_cipher() -> Fernet:
    """Trả về cipher Fernet đơn tương ứng với primary key."""
    return Fernet(get_byok_encryption_key())


def encrypt_api_key(plain_key: str) -> str:
    """Mã hóa khóa API thô thành chuỗi ciphertext Fernet bảo mật.
    Luôn bắt đầu bằng tiền tố Fernet chuẩn 'gAAAAA'.
    """
    if not plain_key or not plain_key.strip():
        raise ValueError("API Key không được để trống hoặc chỉ chứa khoảng trắng.")
    cipher = get_multi_fernet()
    encrypted_bytes = cipher.encrypt(plain_key.strip().encode("utf-8"))
    return encrypted_bytes.decode("utf-8")


def decrypt_api_key(encrypted_key: str) -> str:
    """Giải mã chuỗi ciphertext về khóa API gốc sử dụng MultiFernet.
    
    Hỗ trợ giải mã với cả primary key hiện tại và các fallback rotation keys.
    Nếu ciphertext bị can thiệp (tampered), sai lệch HMAC hoặc hỏng,
    InvalidToken sẽ được bắt và chuyển thành ValueError('Tampered or invalid key').
    """
    if not encrypted_key or not encrypted_key.strip():
        raise ValueError("Chuỗi khóa mã hóa không hợp lệ.")
    cipher = get_multi_fernet()
    try:
        decrypted_bytes = cipher.decrypt(encrypted_key.strip().encode("utf-8"))
        return decrypted_bytes.decode("utf-8")
    except (InvalidToken, Exception) as exc:
        raise ValueError("Tampered or invalid key") from exc


def mask_api_key(plain_key: str) -> str:
    """Tạo chuỗi che mặt nạ (masked key) chuẩn bảo mật:
    - Nếu len >= 10: f"{plain_key[:6]}...{plain_key[-4:]}" (Ví dụ: AIzaSy...9999).
    - Ngược lại nếu len >= 4: f"{plain_key[:2]}...{plain_key[-2:]}".
    - Nếu len < 4: '...'.
    Luôn đảm bảo chứa chuỗi '...' (ít nhất 3 ký tự che chắn) để thỏa mãn
    test_t1_r6_03 và test_t2_r6_05.
    """
    if not plain_key:
        return ""
    clean = plain_key.strip()
    if len(clean) >= 10:
        return f"{clean[:6]}...{clean[-4:]}"
    elif len(clean) >= 4:
        return f"{clean[:2]}...{clean[-2:]}"
    return "..."


def rotate_custom_api_keys(db: Session, target_version: str = "v2") -> dict:
    """Tiện ích xoay vòng khóa (Key Rotation):
    Giải mã các khóa trong bảng custom_api_keys bằng MultiFernet (thử primary và fallback keys)
    và tái mã hóa bằng primary key hiện tại.
    """
    from app.models.entities import CustomApiKey

    records = db.query(CustomApiKey).all()
    rotated_count = 0
    failed_count = 0
    skipped_count = 0

    for record in records:
        if not getattr(record, "encrypted_key", None):
            skipped_count += 1
            continue
        try:
            plain_key = decrypt_api_key(record.encrypted_key)
            new_cipher = encrypt_api_key(plain_key)
            record.encrypted_key = new_cipher
            if hasattr(record, "key_version"):
                setattr(record, "key_version", target_version)
            db.add(record)
            rotated_count += 1
        except Exception as exc:
            failed_count += 1
            logger.error("[KeyRotation] Failed to rotate key id=%s: %s", getattr(record, "id", "unknown"), str(exc))

    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error("[KeyRotation] Database commit failed: %s", str(exc))
        raise

    return {
        "total": len(records),
        "rotated": rotated_count,
        "skipped": skipped_count,
        "failed": failed_count,
        "target_version": target_version,
    }

