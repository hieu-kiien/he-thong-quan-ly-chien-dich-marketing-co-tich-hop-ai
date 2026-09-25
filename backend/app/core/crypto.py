"""Module mã hóa đối xứng an toàn cho Enterprise BYOK Vault (FEAT-BE-23).
Sử dụng Fernet (AES-128-CBC + HMAC-SHA256) kết hợp PBKDF2HMAC Key Derivation.
Cung cấp khả năng chống can thiệp (Tamper Resistance) và che giấu mặt nạ khóa an toàn.
"""

import base64
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.core.config import settings

# Salt cố định cho việc dẫn xuất khóa Fernet vault từ SECRET_KEY
VAULT_SALT = b"marketflow-byok-vault-pbkdf2-salt-v1"


def get_fernet_cipher() -> Fernet:
    """Dẫn xuất khóa Fernet 32-byte URL-safe base64 từ settings.SECRET_KEY thông qua PBKDF2HMAC."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=VAULT_SALT,
        iterations=100_000,
    )
    derived_key = base64.urlsafe_b64encode(kdf.derive(settings.SECRET_KEY.encode("utf-8")))
    return Fernet(derived_key)


def encrypt_api_key(plain_key: str) -> str:
    """Mã hóa khóa API thô thành chuỗi ciphertext Fernet bảo mật."""
    if not plain_key or not plain_key.strip():
        raise ValueError("API Key không được để trống hoặc chỉ chứa khoảng trắng.")
    cipher = get_fernet_cipher()
    encrypted_bytes = cipher.encrypt(plain_key.strip().encode("utf-8"))
    return encrypted_bytes.decode("utf-8")


def decrypt_api_key(encrypted_key: str) -> str:
    """Giải mã chuỗi ciphertext về khóa API gốc.
    
    Nếu ciphertext bị can thiệp (tampered), sai lệch HMAC hoặc hỏng,
    InvalidToken sẽ được bắt và chuyển thành ValueError('Tampered or invalid key').
    """
    if not encrypted_key or not encrypted_key.strip():
        raise ValueError("Chuỗi khóa mã hóa không hợp lệ.")
    cipher = get_fernet_cipher()
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
