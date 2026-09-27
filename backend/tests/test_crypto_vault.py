"""Comprehensive Test Suite for Crypto Vault, Secret Decoupling & MultiFernet Key Rotation.
Sprint S2 (Squad 2 - Crypto & BYOK Secrets).
Covers:
1. Cryptographic Key Separation (JWT_SECRET_KEY vs BYOK_ENCRYPTION_KEY).
2. Fernet Ciphertext Invariant ('gAAAAA' prefix, tamper resistance).
3. Multi-Version Key Rotation via MultiFernet and DB re-encryption (rotate_custom_api_keys).
4. Startup Security Validation (rejection of insecure placeholders, length < 32, missing keys in production).
5. Clean Helper Re-exports in security.py.
"""

import base64
import os
import pytest
from cryptography.fernet import Fernet
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings, validate_security_configuration, settings
import app.core.crypto as crypto
from app.core.crypto import (
    get_jwt_secret_key,
    get_byok_encryption_key,
    get_fernet_cipher,
    get_multi_fernet,
    encrypt_api_key,
    decrypt_api_key,
    mask_api_key,
    rotate_custom_api_keys,
    _derive_fernet_key,
    _format_or_derive_fernet_key,
    VAULT_SALT,
)
import app.core.security as security
from app.core.security import create_access_token, decode_access_token
from app.models.entities import Base, CustomApiKey, User


@pytest.fixture
def memory_db():
    """In-memory SQLite database session for key rotation tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


# ==============================================================================
# 1. KEY SEPARATION TESTS
# ==============================================================================

class TestKeySeparation:
    """Kiểm tra tính độc lập và phân tách giữa JWT_SECRET_KEY và BYOK_ENCRYPTION_KEY."""

    def test_01_default_fallback_to_secret_key(self, monkeypatch):
        """Khi JWT_SECRET_KEY và BYOK_ENCRYPTION_KEY chưa thiết lập, fallback về SECRET_KEY."""
        monkeypatch.setattr(settings, "JWT_SECRET_KEY", None)
        monkeypatch.setattr(settings, "BYOK_ENCRYPTION_KEY", None)

        jwt_key = get_jwt_secret_key()
        assert jwt_key == settings.SECRET_KEY

        byok_key = get_byok_encryption_key()
        expected_byok = _derive_fernet_key(settings.SECRET_KEY)
        assert byok_key == expected_byok

    def test_02_explicit_jwt_secret_key_decoupled(self, monkeypatch):
        """Khi JWT_SECRET_KEY được cấu hình riêng, get_jwt_secret_key trả về key riêng."""
        custom_jwt = "custom-jwt-dedicated-secret-key-32chars-min!!"
        monkeypatch.setattr(settings, "JWT_SECRET_KEY", custom_jwt)
        assert get_jwt_secret_key() == custom_jwt

    def test_03_explicit_byok_encryption_key_decoupled(self, monkeypatch):
        """Khi BYOK_ENCRYPTION_KEY được cấu hình riêng, get_byok_encryption_key sử dụng key riêng."""
        custom_byok = Fernet.generate_key().decode("utf-8")
        monkeypatch.setattr(settings, "BYOK_ENCRYPTION_KEY", custom_byok)
        assert get_byok_encryption_key() == custom_byok.encode("utf-8")

    def test_04_rotating_jwt_key_does_not_break_byok_vault(self, monkeypatch):
        """Xoay JWT_SECRET_KEY không làm ảnh hưởng đến giải mã khóa BYOK đã lưu."""
        # 1. Mã hóa dữ liệu bằng BYOK
        plain_secret = "AIzaSySecretGeminiKey123456789"
        ciphertext = encrypt_api_key(plain_secret)

        # 2. Xoay JWT_SECRET_KEY sang giá trị mới
        monkeypatch.setattr(settings, "JWT_SECRET_KEY", "brand-new-jwt-key-rotation-32chars-safe!!")

        # 3. Giải mã BYOK ciphertext phải thành công tuyệt đối
        decrypted = decrypt_api_key(ciphertext)
        assert decrypted == plain_secret

    def test_05_rotating_byok_key_does_not_break_existing_jwt_tokens(self, monkeypatch):
        """Thay đổi BYOK_ENCRYPTION_KEY không làm mất hiệu lực token JWT đang hoạt động."""
        monkeypatch.setattr(settings, "JWT_SECRET_KEY", "stable-jwt-signing-key-32chars-long!!")
        token = create_access_token({"sub": "user123", "role": "MARKETER"})

        # Thay đổi BYOK key
        new_byok_key = Fernet.generate_key().decode("utf-8")
        monkeypatch.setattr(settings, "BYOK_ENCRYPTION_KEY", new_byok_key)

        # Token JWT vẫn giải mã và xác thực thành công
        payload = decode_access_token(token)
        assert payload["sub"] == "user123"
        assert payload["role"] == "MARKETER"


# ==============================================================================
# 2. FERNET CIPHERTEXT INVARIANT & TAMPER RESISTANCE
# ==============================================================================

class TestFernetCiphertextInvariant:
    """Đảm bảo format Fernet chuẩn và khả năng chống can thiệp."""

    def test_06_ciphertext_always_starts_with_gAAAAA(self):
        """Bắt buộc ciphertext luôn bắt đầu bằng 'gAAAAA' để tương thích toàn bộ test suites."""
        plain = "AIzaSyTestFernetPrefixConsistencyKey999"
        cipher = encrypt_api_key(plain)
        assert cipher.startswith("gAAAAA")
        assert len(cipher) > 50

    def test_07_roundtrip_encryption_decryption(self):
        """Kiểm tra mã hóa và giải mã trọn vẹn với chuỗi Unicode và ký tự đặc biệt."""
        test_strings = [
            "AIzaSySimpleAsciiKey123",
            "Khóa-Bảo-Mật-Tiếng-Việt-Có-Dấu-1234567890",
            '{"provider": "gemini", "secret": "AIzaSySpecial!@#$%^&*()_+="}',
            "a" * 5000,  # Large payload
        ]
        for plain in test_strings:
            cipher = encrypt_api_key(plain)
            assert cipher.startswith("gAAAAA")
            assert decrypt_api_key(cipher) == plain

    def test_08_tampered_ciphertext_rejected(self):
        """Ciphertext bị can thiệp ném ValueError với thông điệp 'Tampered or invalid key'."""
        cipher = encrypt_api_key("AIzaSyTamperTest123")
        tampered = list(cipher)
        tampered[25] = "Z" if tampered[25] != "Z" else "A"
        tampered_cipher = "".join(tampered)

        with pytest.raises(ValueError, match="Tampered or invalid key"):
            decrypt_api_key(tampered_cipher)

    def test_09_empty_or_whitespace_key_validation(self):
        """Không cho phép mã hóa hoặc giải mã chuỗi rỗng / khoảng trắng."""
        with pytest.raises(ValueError, match="API Key không được để trống"):
            encrypt_api_key("")
        with pytest.raises(ValueError, match="API Key không được để trống"):
            encrypt_api_key("   \t\n  ")
        with pytest.raises(ValueError, match="Chuỗi khóa mã hóa không hợp lệ"):
            decrypt_api_key("")
        with pytest.raises(ValueError, match="Chuỗi khóa mã hóa không hợp lệ"):
            decrypt_api_key("   ")

    def test_10_masking_ladder_integrity(self):
        """Che mặt nạ theo đúng nấc thang bảo mật."""
        assert mask_api_key("AIzaSy123456789") == "AIzaSy...6789"
        assert mask_api_key("123456") == "12...56"
        assert mask_api_key("123") == "..."
        assert mask_api_key("") == ""
        assert mask_api_key(None) == ""


# ==============================================================================
# 3. MULTIFERNET KEY ROTATION & DATABASE RE-ENCRYPTION
# ==============================================================================

class TestMultiFernetKeyRotation:
    """Kiểm tra cơ chế xoay vòng khóa không gián đoạn với MultiFernet."""

    def test_11_multifernet_decrypts_with_rotation_keys(self, monkeypatch):
        """Dữ liệu được mã hóa bằng khóa cũ vẫn giải mã được khi khai báo trong BYOK_ROTATION_KEYS."""
        key_v1 = Fernet.generate_key().decode("utf-8")
        key_v2 = Fernet.generate_key().decode("utf-8")

        # 1. Mã hóa với key_v1
        monkeypatch.setattr(settings, "BYOK_ENCRYPTION_KEY", key_v1)
        monkeypatch.setattr(settings, "BYOK_ROTATION_KEYS", None)
        plain_text = "AIzaSySecretUnderOldKeyV1"
        cipher_v1 = encrypt_api_key(plain_text)
        assert cipher_v1.startswith("gAAAAA")

        # 2. Xoay sang key_v2 làm primary, key_v1 làm rotation/fallback
        monkeypatch.setattr(settings, "BYOK_ENCRYPTION_KEY", key_v2)
        monkeypatch.setattr(settings, "BYOK_ROTATION_KEYS", key_v1)

        # 3. Giải mã cipher_v1 vẫn thành công nhờ MultiFernet
        decrypted_old = decrypt_api_key(cipher_v1)
        assert decrypted_old == plain_text

        # 4. Mã hóa mới sử dụng key_v2
        cipher_v2 = encrypt_api_key(plain_text)
        assert cipher_v2.startswith("gAAAAA")
        assert cipher_v2 != cipher_v1
        assert decrypt_api_key(cipher_v2) == plain_text

    def test_12_multifernet_supports_json_list_rotation_keys(self, monkeypatch):
        """Hỗ trợ cấu hình BYOK_ROTATION_KEYS dạng JSON list chuỗi."""
        k1 = Fernet.generate_key().decode("utf-8")
        k2 = Fernet.generate_key().decode("utf-8")
        k3 = Fernet.generate_key().decode("utf-8")

        # Mã hóa với k1
        monkeypatch.setattr(settings, "BYOK_ENCRYPTION_KEY", k1)
        cipher_k1 = encrypt_api_key("TargetSecretK1")

        # Cấu hình k3 là primary, [k2, k1] là rotation keys
        monkeypatch.setattr(settings, "BYOK_ENCRYPTION_KEY", k3)
        monkeypatch.setattr(settings, "BYOK_ROTATION_KEYS", f'["{k2}", "{k1}"]')

        assert decrypt_api_key(cipher_k1) == "TargetSecretK1"

    def test_13_rotate_custom_api_keys_in_database(self, memory_db, monkeypatch):
        """Tiện ích rotate_custom_api_keys giải mã toàn bộ DB bằng khóa cũ và tái mã hóa bằng khóa mới."""
        old_key = Fernet.generate_key().decode("utf-8")
        new_key = Fernet.generate_key().decode("utf-8")

        # Tạo user giả lập
        test_user = User(
            email="rotate_test@example.com",
            full_name="Rotate Tester",
            password_hash="fake-hash-for-test",
            role="MARKETER",
            status="ACTIVE",
        )
        memory_db.add(test_user)
        memory_db.commit()

        # 1. Mã hóa 3 bản ghi bằng old_key
        monkeypatch.setattr(settings, "BYOK_ENCRYPTION_KEY", old_key)
        monkeypatch.setattr(settings, "BYOK_ROTATION_KEYS", None)

        record1 = CustomApiKey(user_id=test_user.id, provider="gemini", encrypted_key=encrypt_api_key("Key-Alpha-12345"))
        record2 = CustomApiKey(user_id=test_user.id, provider="gemini", encrypted_key=encrypt_api_key("Key-Beta-67890"))
        # Bản ghi rác/hỏng để test khả năng chống lỗi
        record_bad = CustomApiKey(user_id=test_user.id, provider="gemini", encrypted_key="gAAAAABadCorruptKeyString==")

        memory_db.add_all([record1, record2, record_bad])
        memory_db.commit()

        # 2. Chuyển sang new_key làm primary, old_key làm fallback
        monkeypatch.setattr(settings, "BYOK_ENCRYPTION_KEY", new_key)
        monkeypatch.setattr(settings, "BYOK_ROTATION_KEYS", old_key)

        # 3. Thực thi rotate_custom_api_keys
        res = rotate_custom_api_keys(memory_db, target_version="v2")

        assert res["total"] == 3
        assert res["rotated"] == 2
        assert res["failed"] == 1

        # 4. Kiểm tra lại dữ liệu sau khi rotate: đã được re-encrypt bằng new_key
        # Tháo old_key khỏi fallback để chứng minh bản ghi đã chuyển hẳn sang new_key!
        monkeypatch.setattr(settings, "BYOK_ROTATION_KEYS", None)

        memory_db.refresh(record1)
        memory_db.refresh(record2)

        assert record1.encrypted_key.startswith("gAAAAA")
        assert record2.encrypted_key.startswith("gAAAAA")

        assert decrypt_api_key(record1.encrypted_key) == "Key-Alpha-12345"
        assert decrypt_api_key(record2.encrypted_key) == "Key-Beta-67890"


# ==============================================================================
# 4. STARTUP VALIDATION & INSECURE PLACEHOLDER REJECTION
# ==============================================================================

class TestStartupSecurityValidation:
    """Kiểm tra từ chối khởi động khi cấu hình bảo mật không an toàn."""

    def test_14_rejects_insecure_placeholder_in_production(self):
        """Từ chối khởi động trên production nếu SECRET_KEY là placeholder mặc định."""
        prod_settings = Settings(
            APP_ENV="production",
            SECRET_KEY="aia331-secret-key-change-in-production-super-secure",
            JWT_SECRET_KEY=None,
            BYOK_ENCRYPTION_KEY=None,
        )
        with pytest.raises(RuntimeError, match="placeholder không an toàn"):
            validate_security_configuration(prod_settings, enforce_production=True)

    def test_15_rejects_short_secret_in_production(self):
        """Từ chối khởi động trên production nếu secret ngắn hơn 32 ký tự."""
        prod_settings = Settings(
            APP_ENV="production",
            SECRET_KEY="too-short-key",
            JWT_SECRET_KEY="short-jwt-key",
            BYOK_ENCRYPTION_KEY="short-byok-key",
        )
        with pytest.raises(RuntimeError, match="độ dài nhỏ hơn 32 ký tự"):
            validate_security_configuration(prod_settings, enforce_production=True)

    def test_16_rejects_empty_secrets_in_production(self):
        """Từ chối khởi động trên production nếu thiếu secret key."""
        prod_settings = Settings(
            APP_ENV="production",
            SECRET_KEY="",
            JWT_SECRET_KEY="",
            BYOK_ENCRYPTION_KEY="",
        )
        with pytest.raises(RuntimeError, match="không được để trống"):
            validate_security_configuration(prod_settings, enforce_production=True)

    def test_17_accepts_valid_secure_secrets_in_production(self):
        """Chấp nhận khởi động trên production khi secret key hợp lệ >= 32 ký tự và không phải placeholder."""
        secure_jwt = "production-jwt-very-secure-secret-key-xyz-32chars!!"
        secure_byok = Fernet.generate_key().decode("utf-8")
        prod_settings = Settings(
            APP_ENV="production",
            SECRET_KEY="production-system-master-key-32chars-long-secure!",
            JWT_SECRET_KEY=secure_jwt,
            BYOK_ENCRYPTION_KEY=secure_byok,
        )
        assert validate_security_configuration(prod_settings, enforce_production=True) is True

    def test_18_allows_development_mode_without_error(self):
        """Trong môi trường development/test, cho phép chạy mà không ném lỗi fatal."""
        dev_settings = Settings(
            APP_ENV="development",
            SECRET_KEY="aia331-secret-key-change-in-production-super-secure",
        )
        # Không raise RuntimeError
        result = validate_security_configuration(dev_settings, enforce_production=False)
        assert result in (True, False)


# ==============================================================================
# 5. SECURITY RE-EXPORT VERIFICATION
# ==============================================================================

class TestSecurityReExports:
    """Xác nhận các crypto helpers được re-export sạch sẽ qua security.py."""

    def test_19_security_module_reexports_crypto_helpers(self):
        """Các hàm mã hóa và helper chính từ crypto được cung cấp đồng bộ từ security."""
        assert callable(security.get_jwt_secret_key)
        assert callable(security.get_byok_encryption_key)
        assert callable(security.get_fernet_cipher)
        assert callable(security.get_multi_fernet)
        assert callable(security.encrypt_api_key)
        assert callable(security.decrypt_api_key)
        assert callable(security.mask_api_key)
        assert callable(security.rotate_custom_api_keys)

        assert security.get_jwt_secret_key is crypto.get_jwt_secret_key
        assert security.encrypt_api_key is crypto.encrypt_api_key
        assert security.decrypt_api_key is crypto.decrypt_api_key
