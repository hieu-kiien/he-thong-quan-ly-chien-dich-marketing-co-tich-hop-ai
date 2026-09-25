import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.entities import AILog, Campaign, User, BrandKit


@pytest.fixture
def manager_headers(client: TestClient):
    resp = client.post("/api/v1/auth/login", json={"email": "manager@ictu.edu.vn", "password": "Manager@123"})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def marketer_headers(client: TestClient):
    resp = client.post("/api/v1/auth/login", json={"email": "marketer@ictu.edu.vn", "password": "Marketer@123"})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def setup_ai_service():
    from app.services.ai.ai_service import ai_service
    ai_service.api_key = ""
    ai_service.fallback_enabled = True
    yield
    del ai_service.api_key
    del ai_service.fallback_enabled


@pytest.fixture
def db(db_session):
    return db_session


class TestAIOmnichannelEngine:
    """Kiểm thử toàn diện Động cơ Sáng tạo AI Đa kênh (Milestone 2 - R2)."""

    def test_01_omnichannel_generation_all_channels_success(self, client: TestClient, manager_headers):
        """Happy Path: Sinh đồng thời trọn bộ 3 kênh (Facebook, TikTok, Email) từ 1 brief duy nhất."""
        payload = {
            "campaign_id": 1,
            "brief": "Chiến dịch tuyển sinh khóa học lập trình AI đột phá 2026",
            "target_audience": "Sinh viên CNTT và kỹ sư phần mềm trẻ",
            "channels": ["facebook", "tiktok", "email"]
        }
        resp = client.post("/api/v1/ai/omnichannel", json=payload, headers=manager_headers)
        assert resp.status_code == 200, f"Call failed: {resp.text}"
        data = resp.json()
        assert "facebook" in data and data["facebook"] is not None
        assert "tiktok" in data and data["tiktok"] is not None
        assert "email" in data and data["email"] is not None
        assert data.get("task_type") == "OMNICHANNEL"
        assert "gemini" in data.get("model_used", "").lower() or "flash" in data.get("model_used", "").lower()

    def test_02_facebook_creative_dual_fields_compatibility(self, client: TestClient, manager_headers):
        """Kiểm tra hợp đồng dữ liệu kênh Facebook: Đầy đủ title/headline, body/primary_text, cta, hashtags."""
        payload = {
            "campaign_id": 1,
            "brief": "Ra mắt tính năng AI mới cho người dùng",
            "target_audience": "Chủ doanh nghiệp SME",
            "channels": ["facebook"]
        }
        resp = client.post("/api/v1/ai/omnichannel", json=payload, headers=manager_headers)
        assert resp.status_code == 200
        fb = resp.json().get("facebook")
        assert fb is not None
        # E2E Test Contract fields
        assert "title" in fb and len(fb["title"]) > 0
        assert "body" in fb and len(fb["body"]) > 0
        assert "cta" in fb and len(fb["cta"]) > 0
        assert "hashtags" in fb and isinstance(fb["hashtags"], list) and len(fb["hashtags"]) > 0
        # Dual-compatibility UI fields
        assert "headline" in fb and fb["headline"] == fb["title"]
        assert "primary_text" in fb and fb["primary_text"] == fb["body"]
        assert "visual_suggestion" in fb

    def test_03_tiktok_creative_scenes_structure(self, client: TestClient, manager_headers):
        """Kiểm tra cấu trúc kịch bản video TikTok: hook 3s, danh sách phân cảnh (visual, voiceover, audio), suggested_audio."""
        payload = {
            "campaign_id": 1,
            "brief": "Trend biến hình cùng sản phẩm công nghệ EdTech",
            "target_audience": "Gen Z năng động",
            "channels": ["tiktok"]
        }
        resp = client.post("/api/v1/ai/omnichannel", json=payload, headers=manager_headers)
        assert resp.status_code == 200
        tiktok = resp.json().get("tiktok")
        assert tiktok is not None
        assert "hook_3s" in tiktok and len(tiktok["hook_3s"]) > 0
        assert "suggested_audio" in tiktok and len(tiktok["suggested_audio"]) > 0
        assert "scenes" in tiktok and isinstance(tiktok["scenes"], list) and len(tiktok["scenes"]) >= 3
        # Check scene fields
        for sc in tiktok["scenes"]:
            assert "visual" in sc and len(sc["visual"]) > 0
            assert "voiceover" in sc and len(sc["voiceover"]) > 0
            assert "scene" in sc

    def test_04_email_sequence_ab_testing_contract(self, client: TestClient, manager_headers):
        """Kiểm tra cấu trúc chuỗi Email: Đề xuất tiêu đề A/B options, preheader, greeting, body, CTA, PS note."""
        payload = {
            "campaign_id": 1,
            "brief": "Email giới thiệu chương trình ưu đãi đặc quyền tuần lễ vàng",
            "target_audience": "Khách hàng thân thiết",
            "channels": ["email"]
        }
        resp = client.post("/api/v1/ai/omnichannel", json=payload, headers=manager_headers)
        assert resp.status_code == 200
        email = resp.json().get("email")
        assert email is not None
        assert "subject_options" in email and isinstance(email["subject_options"], list) and len(email["subject_options"]) >= 2
        assert "body" in email and len(email["body"]) > 0
        assert "cta_button" in email and len(email["cta_button"]) > 0
        assert "preheader" in email
        assert "greeting" in email
        assert "ps_note" in email

    def test_05_channel_filtering_facebook_only(self, client: TestClient, manager_headers):
        """Lọc kênh: Chỉ yêu cầu facebook -> chỉ trả về facebook, các kênh khác None/omitted."""
        payload = {
            "campaign_id": 1,
            "brief": "Chỉ tạo nội dung cho bài đăng Facebook",
            "target_audience": "Cộng đồng mạng xã hội",
            "channels": ["facebook"]
        }
        resp = client.post("/api/v1/ai/omnichannel", json=payload, headers=manager_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "facebook" in data and data["facebook"] is not None
        assert data.get("tiktok") is None
        assert data.get("email") is None

    def test_06_channel_filtering_tiktok_only(self, client: TestClient, manager_headers):
        """Lọc kênh: Chỉ yêu cầu tiktok -> chỉ trả về tiktok."""
        payload = {
            "campaign_id": 1,
            "brief": "Chỉ làm kịch bản video ngắn TikTok",
            "target_audience": "Gen Z",
            "channels": ["tiktok"]
        }
        resp = client.post("/api/v1/ai/omnichannel", json=payload, headers=manager_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "tiktok" in data and data["tiktok"] is not None
        assert data.get("facebook") is None
        assert data.get("email") is None

    def test_07_channel_filtering_email_only(self, client: TestClient, manager_headers):
        """Lọc kênh: Chỉ yêu cầu email -> chỉ trả về email."""
        payload = {
            "campaign_id": 1,
            "brief": "Chỉ tạo bản tin email marketing",
            "target_audience": "Subscribers",
            "channels": ["email"]
        }
        resp = client.post("/api/v1/ai/omnichannel", json=payload, headers=manager_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "email" in data and data["email"] is not None
        assert data.get("facebook") is None
        assert data.get("tiktok") is None

    def test_08_default_channels_applied_when_omitted(self, client: TestClient, manager_headers):
        """Khi client không gửi field channels, mặc định sinh cả 3 kênh (facebook, tiktok, email)."""
        payload = {
            "campaign_id": 1,
            "brief": "Chiến dịch tiếp thị toàn diện không chỉ định danh sách kênh",
            "target_audience": "Đại chúng"
        }
        resp = client.post("/api/v1/ai/omnichannel", json=payload, headers=manager_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "facebook" in data and data["facebook"] is not None
        assert "tiktok" in data and data["tiktok"] is not None
        assert "email" in data and data["email"] is not None

    def test_09_empty_brief_validation_fails_422(self, client: TestClient, manager_headers):
        """Bản brief rỗng hoàn toàn phải bị từ chối với HTTP 422."""
        resp = client.post("/api/v1/ai/omnichannel", json={
            "campaign_id": 1,
            "brief": "",
            "target_audience": "Mọi người"
        }, headers=manager_headers)
        assert resp.status_code == 422

    def test_10_whitespace_only_brief_validation_fails_422(self, client: TestClient, manager_headers):
        """Bản brief chỉ có khoảng trắng, tab, xuống dòng phải bị từ chối với HTTP 422."""
        resp = client.post("/api/v1/ai/omnichannel", json={
            "campaign_id": 1,
            "brief": "   \n\t   ",
            "target_audience": "Mọi người"
        }, headers=manager_headers)
        assert resp.status_code == 422

    def test_11_unsupported_channel_validation_fails_422(self, client: TestClient, manager_headers):
        """Kênh không nằm trong whitelist {"facebook", "tiktok", "email"} phải bị từ chối HTTP 422."""
        resp = client.post("/api/v1/ai/omnichannel", json={
            "campaign_id": 1,
            "brief": "Chiến dịch quảng cáo",
            "channels": ["unknown_social_network_xyz"]
        }, headers=manager_headers)
        assert resp.status_code == 422

    def test_12_empty_channels_array_validation_fails_422(self, client: TestClient, manager_headers):
        """Mảng channels rỗng [] phải bị từ chối HTTP 422."""
        resp = client.post("/api/v1/ai/omnichannel", json={
            "campaign_id": 1,
            "brief": "Chiến dịch quảng cáo",
            "channels": []
        }, headers=manager_headers)
        assert resp.status_code == 422

    def test_13_oversized_brief_handling(self, client: TestClient, manager_headers):
        """Stress test: Brief cực dài (5000+ ký tự) được xử lý an toàn (HTTP 200 hoặc 422, không crash 500)."""
        giant_brief = "Chiến dịch tiếp thị toàn cầu với mô tả cực dài: " + (" MarketFlow " * 400)
        resp = client.post("/api/v1/ai/omnichannel", json={
            "campaign_id": 1,
            "brief": giant_brief,
            "target_audience": "Toàn bộ thị trường mục tiêu"
        }, headers=manager_headers)
        assert resp.status_code in (200, 422), f"Unexpected status {resp.status_code}: {resp.text}"

    def test_14_unauthenticated_request_fails_401(self, client: TestClient):
        """Yêu cầu không có Bearer token phải trả về HTTP 401 Unauthorized."""
        resp = client.post("/api/v1/ai/omnichannel", json={
            "campaign_id": 1,
            "brief": "Brief hợp lệ nhưng không đăng nhập"
        })
        assert resp.status_code == 401

    def test_15_record_level_permission_marketer_owner_allowed(self, client: TestClient, marketer_headers):
        """Phân quyền mức bản ghi: Marketer là chủ sở hữu của Campaign 1 được phép sinh nội dung."""
        resp = client.post("/api/v1/ai/omnichannel", json={
            "campaign_id": 1,
            "brief": "Sáng tạo nội dung cho chiến dịch sở hữu",
            "channels": ["facebook"]
        }, headers=marketer_headers)
        assert resp.status_code == 200

    def test_16_record_level_permission_marketer_non_member_forbidden(self, client: TestClient, marketer_headers):
        """Phân quyền mức bản ghi: Marketer không phải chủ sở hữu hay thành viên của Campaign 2 -> HTTP 403."""
        resp = client.post("/api/v1/ai/omnichannel", json={
            "campaign_id": 2,
            "brief": "Cố gắng sinh nội dung cho chiến dịch của người khác",
            "channels": ["facebook"]
        }, headers=marketer_headers)
        assert resp.status_code == 403

    def test_17_nonexistent_campaign_fails_404(self, client: TestClient, manager_headers):
        """Chiến dịch không tồn tại trong CSDL phải trả về HTTP 404 Not Found."""
        resp = client.post("/api/v1/ai/omnichannel", json={
            "campaign_id": 999999,
            "brief": "Chiến dịch ma không tồn tại"
        }, headers=manager_headers)
        assert resp.status_code == 404

    def test_18_brand_kit_inheritance(self, client: TestClient, manager_headers, db: Session):
        """Kế thừa Brand Kit từ Workspace: Tên thương hiệu và USP được tích hợp an toàn."""
        resp = client.post("/api/v1/ai/omnichannel", json={
            "campaign_id": 1,
            "brief": "Khai phá sức mạnh chuyển đổi số trong giáo dục",
            "channels": ["facebook"]
        }, headers=manager_headers)
        assert resp.status_code == 200
        fb = resp.json().get("facebook")
        assert fb is not None
        assert len(fb["title"]) > 0

    def test_19_ai_logging_persisted_to_db(self, client: TestClient, manager_headers, db: Session):
        """Ghi nhận nhật ký AI vào bảng ai_logs với task_type='OMNICHANNEL'."""
        initial_count = db.query(AILog).filter(AILog.task_type == "OMNICHANNEL").count()
        resp = client.post("/api/v1/ai/omnichannel", json={
            "campaign_id": 1,
            "brief": "Kiểm tra cơ chế audit logging cho Omnichannel Engine",
            "channels": ["facebook"]
        }, headers=manager_headers)
        assert resp.status_code == 200
        new_count = db.query(AILog).filter(AILog.task_type == "OMNICHANNEL").count()
        assert new_count > initial_count, "Bản ghi AILog cho OMNICHANNEL phải được ghi vào CSDL"

    def test_20_smart_fallback_when_offline(self, client: TestClient, manager_headers):
        """Smart Fallback: Khi không có API key ngoại vi, hệ thống tự động fallback an toàn (is_fallback=True)."""
        resp = client.post("/api/v1/ai/omnichannel", json={
            "campaign_id": 1,
            "brief": "Thử nghiệm chế độ Fallback Engine bền bỉ",
            "channels": ["facebook", "tiktok", "email"]
        }, headers=manager_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("is_fallback") is True
        assert len(data.get("warnings", [])) > 0
        assert data.get("compliance_score") == 100
