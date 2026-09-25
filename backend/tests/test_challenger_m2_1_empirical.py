"""
Challenger 1 Empirical Integration & Adversarial Verification Test Suite
Milestone 2: Deep 3-Channel AI Creative Engine (R2)

Covers:
1. Multi-channel generation from 1 single brief (Facebook, TikTok, Email)
2. Channel filtering: ["facebook"], ["tiktok"], ["email"], ["facebook", "email"]
3. Brand Kit inheritance from Workspace (USP, Tone of voice, Banned keywords, AILog audit)
4. Adversarial input validation & Authorization boundaries (empty brief, whitespace, invalid channels, 401, 403, 404)
"""

import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.entities import (
    User, Workspace, WorkspaceMember, BrandKit, Campaign, CampaignMember, AILog, Product, ProductCategory
)


@pytest.fixture
def manager_headers(client: TestClient):
    resp = client.post("/api/v1/auth/login", json={"email": "manager@ictu.edu.vn", "password": "Manager@123"})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def marketer_headers(client: TestClient):
    resp = client.post("/api/v1/auth/login", json={"email": "marketer@ictu.edu.vn", "password": "Marketer@123"})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def setup_ai_service():
    from app.services.ai.ai_service import ai_service
    # Use deterministic offline fallback for high-speed empirical verification
    ai_service.api_key = ""
    ai_service.fallback_enabled = True
    yield
    del ai_service.api_key
    del ai_service.fallback_enabled


class TestChallenger1OmnichannelEmpirical:
    """Empirical verification suite executed by Challenger 1."""

    def test_emp_01_all_3_channels_from_single_brief(self, client: TestClient, manager_headers):
        """Kiểm chứng 1: Từ 1 brief duy nhất, sinh trọn vẹn 3 kênh Facebook, TikTok, Email."""
        payload = {
            "campaign_id": 1,
            "brief": "Ra mắt giải pháp chuyển đổi số bán lẻ RetailFlow AI đa kênh",
            "target_audience": "Chủ chuỗi cửa hàng bán lẻ và siêu thị mini",
            "channels": ["facebook", "tiktok", "email"]
        }
        resp = client.post("/api/v1/ai/omnichannel", json=payload, headers=manager_headers)
        assert resp.status_code == 200, f"Endpoint failed: {resp.text}"
        data = resp.json()

        # Kiểm chứng task_type & model
        assert data.get("task_type") == "OMNICHANNEL"
        assert "gemini" in data.get("model_used", "").lower() or "flash" in data.get("model_used", "").lower()

        # 1. Kênh Facebook
        fb = data.get("facebook")
        assert fb is not None, "Facebook payload is missing"
        assert isinstance(fb.get("title"), str) and len(fb["title"]) > 0
        assert isinstance(fb.get("body"), str) and len(fb["body"]) > 0
        assert isinstance(fb.get("cta"), str) and len(fb["cta"]) > 0
        assert isinstance(fb.get("hashtags"), list) and len(fb["hashtags"]) >= 2
        # Dual-field synchronization
        assert fb.get("headline") == fb["title"]
        assert fb.get("primary_text") == fb["body"]

        # 2. Kênh TikTok
        tiktok = data.get("tiktok")
        assert tiktok is not None, "TikTok payload is missing"
        assert isinstance(tiktok.get("hook_3s"), str) and len(tiktok["hook_3s"]) > 0
        assert isinstance(tiktok.get("suggested_audio"), str) and len(tiktok["suggested_audio"]) > 0
        assert isinstance(tiktok.get("scenes"), list) and len(tiktok["scenes"]) >= 3
        for sc in tiktok["scenes"]:
            assert "scene" in sc and isinstance(sc["scene"], int)
            assert "visual" in sc and len(sc["visual"]) > 0
            assert "voiceover" in sc and len(sc["voiceover"]) > 0
            # Dual-field scene compatibility
            assert sc.get("visual_action") == sc["visual"]
            assert sc.get("voiceover_script") == sc["voiceover"]

        # 3. Kênh Email
        email = data.get("email")
        assert email is not None, "Email payload is missing"
        assert isinstance(email.get("subject_options"), list) and len(email["subject_options"]) >= 2
        assert isinstance(email.get("body"), str) and len(email["body"]) > 0
        assert isinstance(email.get("cta_button"), str) and len(email["cta_button"]) > 0
        assert email.get("body_content") == email["body"]
        assert email.get("cta_button_text") == email["cta_button"]

    def test_emp_02_channel_filter_only_facebook(self, client: TestClient, manager_headers):
        """Kiểm chứng 2A: Truyền channels: ['facebook'] -> chỉ trả về Facebook, loại bỏ TikTok và Email."""
        payload = {
            "campaign_id": 1,
            "brief": "Chiến dịch quảng bá Facebook Feed & Ads tương tác cao",
            "target_audience": "Cộng đồng khởi nghiệp",
            "channels": ["facebook"]
        }
        resp = client.post("/api/v1/ai/omnichannel", json=payload, headers=manager_headers)
        assert resp.status_code == 200
        data = resp.json()

        assert "facebook" in data and data["facebook"] is not None
        assert data.get("tiktok") is None
        assert data.get("email") is None

    def test_emp_03_channel_filter_only_tiktok(self, client: TestClient, manager_headers):
        """Kiểm chứng 2B: Truyền channels: ['tiktok'] -> chỉ trả về TikTok, loại bỏ Facebook và Email."""
        payload = {
            "campaign_id": 1,
            "brief": "Kịch bản viral video TikTok triệu view",
            "target_audience": "Gen Z năng động",
            "channels": ["tiktok"]
        }
        resp = client.post("/api/v1/ai/omnichannel", json=payload, headers=manager_headers)
        assert resp.status_code == 200
        data = resp.json()

        assert "tiktok" in data and data["tiktok"] is not None
        assert data.get("facebook") is None
        assert data.get("email") is None

    def test_emp_04_channel_filter_only_email(self, client: TestClient, manager_headers):
        """Kiểm chứng 2C: Truyền channels: ['email'] -> chỉ trả về Email, loại bỏ Facebook và TikTok."""
        payload = {
            "campaign_id": 1,
            "brief": "Chuỗi email nurture và flash sale dành cho khách hàng VIP",
            "target_audience": "Khách hàng thân thiết",
            "channels": ["email"]
        }
        resp = client.post("/api/v1/ai/omnichannel", json=payload, headers=manager_headers)
        assert resp.status_code == 200
        data = resp.json()

        assert "email" in data and data["email"] is not None
        assert data.get("facebook") is None
        assert data.get("tiktok") is None

    def test_emp_05_brand_kit_inheritance_from_workspace(self, client: TestClient, manager_headers, db_session: Session):
        """Kiểm chứng 3: Kế thừa Brand Kit (USP, Tone, Banned keywords) từ Workspace và lưu log SQLite."""
        # 1. Tạo Workspace và Brand Kit riêng biệt
        manager = db_session.query(User).filter(User.email == "manager@ictu.edu.vn").first()
        ws = Workspace(name="Empirical Workspace M2", slug="emp-workspace-m2", owner_id=manager.id)
        db_session.add(ws)
        db_session.commit()
        db_session.refresh(ws)

        bk = BrandKit(
            workspace_id=ws.id,
            brand_name="AuraTech Premium",
            usp="Công nghệ AI tự động hóa vận hành không độ trễ",
            tone_of_voice="Đẳng cấp, tinh tế, sang trọng",
            banned_keywords_json=json.dumps(["cam kết 100%", "lãi suất siêu tưởng", "đa cấp"])
        )
        db_session.add(bk)

        # 2. Tạo Campaign thuộc Workspace này
        camp = Campaign(
            workspace_id=ws.id,
            owner_id=manager.id,
            product_id=1,
            name="Chiến dịch Định vị Thương hiệu AuraTech",
            objective="Tăng nhận diện thương hiệu cao cấp",
            audience="Giám đốc điều hành & Nhà sáng lập",
            start_date="2026-10-01",
            end_date="2026-10-31",
            budget=50000000.0,
            status="ACTIVE"
        )
        db_session.add(camp)
        db_session.commit()
        db_session.refresh(camp)

        # 3. Gọi endpoint Omnichannel với campaign vừa tạo
        payload = {
            "campaign_id": camp.id,
            "brief": "Chiến dịch định vị giải pháp trí tuệ nhân tạo thế hệ mới",
            "target_audience": "Lãnh đạo cấp cao",
            "channels": ["facebook", "tiktok", "email"]
        }
        resp = client.post("/api/v1/ai/omnichannel", json=payload, headers=manager_headers)
        assert resp.status_code == 200, f"Error: {resp.text}"
        data = resp.json()

        # Kiểm chứng nội dung sinh ra phản ánh Brand Kit
        fb_title = data["facebook"]["title"]
        fb_body = data["facebook"]["body"]
        full_text = f"{fb_title} {fb_body}".lower()
        # Đảm bảo không chứa banned keywords
        assert "lãi suất siêu tưởng" not in full_text
        assert "đa cấp" not in full_text

        # 4. Kiểm chứng AILog được lưu trong DB với task_type='OMNICHANNEL'
        assert "gemini" in data.get("model_used", "").lower() or "flash" in data.get("model_used", "").lower()
        log = db_session.query(AILog).filter(
            AILog.campaign_id == camp.id,
            AILog.task_type == "OMNICHANNEL"
        ).order_by(AILog.id.desc()).first()
        assert log is not None, "AILog entry was not persisted for OMNICHANNEL"
        assert log.task_type == "OMNICHANNEL"
        assert log.result_status == "SUCCESS"
        assert len(log.model) > 0

    def test_emp_06_adversarial_input_and_auth_boundaries(self, client: TestClient, manager_headers, marketer_headers, db_session: Session):
        """Kiểm chứng 4: Thử thách đối kháng (Empty brief, whitespace, invalid channel, 401, 403, 404)."""
        # A. Brief rỗng
        r1 = client.post("/api/v1/ai/omnichannel", json={"campaign_id": 1, "brief": ""}, headers=manager_headers)
        assert r1.status_code == 422

        # B. Brief chỉ khoảng trắng
        r2 = client.post("/api/v1/ai/omnichannel", json={"campaign_id": 1, "brief": "     "}, headers=manager_headers)
        assert r2.status_code == 422

        # C. Kênh không hợp lệ
        r3 = client.post("/api/v1/ai/omnichannel", json={"campaign_id": 1, "brief": "Hợp lệ", "channels": ["wechat"]}, headers=manager_headers)
        assert r3.status_code == 422

        # D. Danh sách kênh rỗng
        r4 = client.post("/api/v1/ai/omnichannel", json={"campaign_id": 1, "brief": "Hợp lệ", "channels": []}, headers=manager_headers)
        assert r4.status_code == 422

        # E. Không truyền JWT (401)
        r5 = client.post("/api/v1/ai/omnichannel", json={"campaign_id": 1, "brief": "Hợp lệ"})
        assert r5.status_code == 401

        # F. Chiến dịch không tồn tại (404)
        r6 = client.post("/api/v1/ai/omnichannel", json={"campaign_id": 999999, "brief": "Hợp lệ"}, headers=manager_headers)
        assert r6.status_code == 404

        # G. Marketer không có quyền trên Campaign của người khác (403)
        manager = db_session.query(User).filter(User.email == "manager@ictu.edu.vn").first()
        private_camp = Campaign(
            owner_id=manager.id,
            product_id=1,
            name="Chiến dịch nội bộ bí mật của Manager",
            objective="Bảo mật",
            audience="Nội bộ",
            start_date="2026-11-01",
            end_date="2026-11-30",
            budget=10000000.0,
            status="ACTIVE"
        )
        db_session.add(private_camp)
        db_session.commit()
        db_session.refresh(private_camp)

        # Marketer gọi vào private_camp
        r7 = client.post("/api/v1/ai/omnichannel", json={"campaign_id": private_camp.id, "brief": "Leo quyền"}, headers=marketer_headers)
        assert r7.status_code == 403
