import json
import pytest
from fastapi.testclient import TestClient
from app.models.entities import MarketingContent, BrandKit, Workspace, WorkspaceMember


def get_token(client: TestClient, email: str, password: str) -> str:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    return resp.json()["access_token"]


@pytest.fixture
def auth_headers(client: TestClient):
    marketer_token = get_token(client, "marketer@ictu.edu.vn", "Marketer@123")
    manager_token = get_token(client, "manager@ictu.edu.vn", "Manager@123")
    approver_token = get_token(client, "approver@ictu.edu.vn", "Approver@123")
    return {
        "marketer": {"Authorization": f"Bearer {marketer_token}"},
        "manager": {"Authorization": f"Bearer {manager_token}"},
        "approver": {"Authorization": f"Bearer {approver_token}"},
    }


# ==============================================================================
# CHALLENGER 1 (M3): EMPIRICAL VERIFICATION OF COMPLIANCE & HITL REVIEW GATE
# ==============================================================================

class TestEmpiricalComplianceScanScenarios:
    """Kiểm nghiệm trực tiếp kịch bản API quét tuân thủ (POST /api/v1/contents/compliance-check)."""

    def test_scenario_1_clean_content_passed(self, client: TestClient, auth_headers):
        """Kịch bản 1: Quét nội dung sạch -> Trả về PASSED, score=100, can_submit=True, violations=[]."""
        payload = {
            "workspace_id": 1,
            "channel": "facebook",
            "title": "Ra mắt khoá học Trí tuệ Nhân tạo thực chiến 2026",
            "body": "Nâng cao kỹ năng lập trình AI cùng các chuyên gia giàu kinh nghiệm. Đăng ký ngay để nhận tư vấn lộ trình học!",
            "cta": "Tìm hiểu ngay"
        }
        resp = client.post("/api/v1/contents/compliance-check", json=payload, headers=auth_headers["marketer"])
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["status"] == "PASSED", f"Expected PASSED, got {data['status']}"
        assert data["score"] == 100, f"Expected score 100, got {data['score']}"
        assert data["can_submit"] is True, "can_submit must be True for clean content"
        assert data["violations"] == [], f"violations should be empty, got {data['violations']}"

    def test_scenario_2_ad_policy_violations(self, client: TestClient, auth_headers):
        """Kịch bản 2: Quét nội dung vi phạm Ad Policy Meta/TikTok ('cam kết 100%', 'chữa dứt điểm', v.v.) -> Trả về VIOLATION/WARNING."""
        # 2a. HIGH severity violation: "cam kết 100%"
        payload_high = {
            "workspace_id": 1,
            "channel": "facebook",
            "title": "Khoá học cam kết 100% việc làm ngay sau khi tốt nghiệp",
            "body": "Chương trình đào tạo đặc biệt, cam kết không rủi ro cho học viên."
        }
        resp_high = client.post("/api/v1/contents/compliance-check", json=payload_high, headers=auth_headers["marketer"])
        assert resp_high.status_code == 200
        data_high = resp_high.json()
        assert data_high["status"] == "VIOLATION"
        assert data_high["can_submit"] is False
        assert any(v["severity"] == "HIGH" for v in data_high["violations"])

        # 2b. HIGH severity medical claim: "chữa dứt điểm"
        payload_med = {
            "workspace_id": 1,
            "channel": "tiktok",
            "title": "Bí quyết cải thiện sức khỏe",
            "body": "Phương pháp này giúp chữa dứt điểm mọi cơn đau nhức chỉ sau 1 tuần sử dụng."
        }
        resp_med = client.post("/api/v1/contents/compliance-check", json=payload_med, headers=auth_headers["marketer"])
        assert resp_med.status_code == 200
        data_med = resp_med.json()
        assert data_med["status"] == "VIOLATION"
        assert data_med["can_submit"] is False
        assert any("chữa dứt điểm" in v["word"] for v in data_med["violations"])

        # 2c. MEDIUM severity price claim: "giá rẻ như cho", "rẻ nhất thị trường"
        payload_medium = {
            "workspace_id": 1,
            "channel": "facebook",
            "title": "Ưu đãi giá rẻ như cho",
            "body": "Phần mềm chất lượng cao với mức chi phí rẻ nhất thị trường hiện nay."
        }
        resp_medium = client.post("/api/v1/contents/compliance-check", json=payload_medium, headers=auth_headers["marketer"])
        assert resp_medium.status_code == 200
        data_medium = resp_medium.json()
        assert data_medium["status"] == "WARNING"
        assert data_medium["can_submit"] is True
        assert all(v["severity"] != "HIGH" for v in data_medium["violations"])
        assert any(v["severity"] == "MEDIUM" for v in data_medium["violations"])

    def test_scenario_3_brand_kit_banned_keywords(self, client: TestClient, auth_headers):
        """Kịch bản 3: Quét nội dung chứa từ cấm trong Workspace Brand Kit ('bán phá giá') -> Trả về vi phạm thuộc danh mục BRAND_BANNED."""
        payload = {
            "workspace_id": 1,
            "channel": "facebook",
            "title": "Chiến dịch xả hàng",
            "body": "Chúng tôi quyết định bán phá giá toàn bộ tồn kho để đón đợt hàng mới!"
        }
        resp = client.post("/api/v1/contents/compliance-check", json=payload, headers=auth_headers["marketer"])
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "VIOLATION"
        assert data["can_submit"] is False
        brand_banned_items = [v for v in data["violations"] if v["category"] == "BRAND_BANNED"]
        assert len(brand_banned_items) > 0, "Must contain at least one BRAND_BANNED violation"
        assert any("bán phá giá" in v["word"].lower() for v in brand_banned_items)
        assert all(v["severity"] == "HIGH" for v in brand_banned_items)


class TestEmpiricalReviewGateScenarios:
    """Kiểm nghiệm trực tiếp quy trình kiểm soát gửi duyệt và duyệt bài viết (Human-in-the-loop Gate)."""

    def test_scenario_4_submit_blocked_with_high_severity(self, client: TestClient, auth_headers, db_session):
        """Kịch bản 4: Thử nghiệm gửi duyệt bài viết (POST /{id}/submit) khi bài chứa vi phạm mức HIGH -> BẮT BUỘC bị chặn với HTTP 400 Bad Request!"""
        # 4a. Tạo bài viết chứa cam kết sai sự thật (HIGH violation)
        create_resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Cam kết 100% hoàn tiền nếu không hài lòng",
            "body": "Đăng ký khóa học và chúng tôi cam kết 100% việc làm với mức lương 50 triệu/tháng.",
            "status": "DRAFT"
        }, headers=auth_headers["marketer"])
        assert create_resp.status_code == 201, f"Failed to create draft: {create_resp.text}"
        content_id = create_resp.json()["id"]

        # Marketer thử gửi duyệt -> BẮT BUỘC HTTP 400 Bad Request!
        submit_resp = client.post(f"/api/v1/contents/{content_id}/submit", headers=auth_headers["marketer"])
        assert submit_resp.status_code == 400, f"Expected HTTP 400, got {submit_resp.status_code}: {submit_resp.text}"
        err_msg = submit_resp.json().get("detail", "")
        assert "an toàn thương hiệu" in err_msg or "HIGH" in err_msg or "vi phạm" in err_msg

        # Kiểm tra trạng thái bài viết: KHÔNG được chuyển sang IN_REVIEW, phải giữ nguyên DRAFT
        get_resp = client.get(f"/api/v1/contents/{content_id}", headers=auth_headers["marketer"])
        assert get_resp.status_code == 200
        assert get_resp.json()["status"] == "DRAFT"

        # 4b. Tạo bài viết chứa từ cấm trong Brand Kit của Workspace 1 ("bán phá giá")
        create_resp_brand = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Xả kho giảm giá sập sàn",
            "body": "Chương trình bán phá giá chưa từng có trong lịch sử ngành.",
            "status": "DRAFT"
        }, headers=auth_headers["marketer"])
        assert create_resp_brand.status_code == 201
        content_id_brand = create_resp_brand.json()["id"]

        # Gửi duyệt bài chứa từ cấm Brand Kit -> BẮT BUỘC HTTP 400!
        submit_resp_brand = client.post(f"/api/v1/contents/{content_id_brand}/submit", headers=auth_headers["marketer"])
        assert submit_resp_brand.status_code == 400, f"Brand kit violation must be blocked with HTTP 400, got {submit_resp_brand.status_code}"

    def test_scenario_5_submit_clean_content_succeeds(self, client: TestClient, auth_headers):
        """Kịch bản 5: Thử nghiệm gửi duyệt bài viết sạch -> Thành công HTTP 200, chuyển sang IN_REVIEW."""
        create_resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Khóa học AI Ứng dụng Thực chiến",
            "body": "Đồng hành cùng các chuyên gia công nghệ hàng đầu để làm chủ kỹ năng ứng dụng AI vào tự động hóa tiếp thị.",
            "status": "DRAFT"
        }, headers=auth_headers["marketer"])
        assert create_resp.status_code == 201
        content_id = create_resp.json()["id"]

        # Marketer gửi duyệt bài viết sạch -> HTTP 200 OK
        submit_resp = client.post(f"/api/v1/contents/{content_id}/submit", headers=auth_headers["marketer"])
        assert submit_resp.status_code == 200, f"Clean submission should succeed: {submit_resp.text}"
        data = submit_resp.json()
        assert data["status"] == "IN_REVIEW", f"Status must be IN_REVIEW, got {data['status']}"

    def test_scenario_6_submit_with_medium_warning_permitted(self, client: TestClient, auth_headers):
        """Bài viết chỉ có cảnh báo mức MEDIUM (không có HIGH) -> Được phép gửi duyệt (200), lưu warnings_json."""
        create_resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Mức giá hợp lý cho mọi khách hàng",
            "body": "Chúng tôi cung cấp giải pháp với chi phí rẻ nhất thị trường trong phân khúc doanh nghiệp nhỏ.",
            "status": "DRAFT"
        }, headers=auth_headers["marketer"])
        assert create_resp.status_code == 201
        content_id = create_resp.json()["id"]

        submit_resp = client.post(f"/api/v1/contents/{content_id}/submit", headers=auth_headers["marketer"])
        assert submit_resp.status_code == 200, f"Medium warning submission should pass: {submit_resp.text}"
        data = submit_resp.json()
        assert data["status"] == "IN_REVIEW"
        assert data.get("warnings_json") is not None
        warnings = json.loads(data["warnings_json"])
        assert len(warnings) > 0
        assert all(w.get("severity") != "HIGH" for w in warnings)

    def test_scenario_7_strict_hitl_rbac_workflow(self, client: TestClient, auth_headers):
        """Kiểm nghiệm toàn trình RBAC: Marketer không được duyệt/từ chối/xuất bản (403); Manager & Approver duyệt thành công."""
        # 1. Tạo bài viết sạch và submit sang IN_REVIEW
        create_resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Bài viết thẩm định RBAC",
            "body": "Nội dung chất lượng cao phục vụ kiểm thử phân quyền duyệt.",
            "status": "DRAFT"
        }, headers=auth_headers["marketer"])
        content_id = create_resp.json()["id"]

        client.post(f"/api/v1/contents/{content_id}/submit", headers=auth_headers["marketer"])

        # 2. Marketer cố tình tự phê duyệt -> 403 Forbidden
        appr_mkt = client.post(f"/api/v1/contents/{content_id}/approve", headers=auth_headers["marketer"])
        assert appr_mkt.status_code == 403, "Marketer must not be allowed to approve content"

        # 3. Marketer cố tình từ chối -> 403 Forbidden
        rej_mkt = client.post(f"/api/v1/contents/{content_id}/reject", json={
            "decision": "REJECTED",
            "reason": "Thử nghiệm từ chối bởi Marketer"
        }, headers=auth_headers["marketer"])
        assert rej_mkt.status_code == 403, "Marketer must not be allowed to reject content"

        # 4. Marketer cố tình xuất bản -> 403 Forbidden
        pub_mkt = client.post(f"/api/v1/contents/{content_id}/publish", headers=auth_headers["marketer"])
        assert pub_mkt.status_code == 403, "Marketer must not be allowed to publish content"

        # 5. Client Approver phê duyệt -> 200 OK -> APPROVED
        appr_client = client.post(f"/api/v1/contents/{content_id}/approve", headers=auth_headers["approver"])
        assert appr_client.status_code == 200, f"Client Approver must succeed: {appr_client.text}"
        assert appr_client.json()["status"] == "APPROVED"

        # 6. Client Approver cố tình xuất bản -> 403 Forbidden (chỉ Manager được xuất bản)
        pub_client = client.post(f"/api/v1/contents/{content_id}/publish", headers=auth_headers["approver"])
        assert pub_client.status_code == 403, "Client Approver cannot publish, only Manager can publish"

        # 7. Manager xuất bản -> 200 OK -> PUBLISHED
        pub_mgr = client.post(f"/api/v1/contents/{content_id}/publish", headers=auth_headers["manager"])
        assert pub_mgr.status_code == 200, f"Manager publish must succeed: {pub_mgr.text}"
        assert pub_mgr.json()["status"] == "PUBLISHED"


class TestEmpiricalAdversarialEvasionsAndHardening:
    """Kiểm thử đối kháng (Adversarial stress-testing): vượt rào dấu, chữ hoa, khoảng trắng, và ranh giới."""

    def test_adversarial_unaccented_evasion(self, client: TestClient, auth_headers):
        """Cố tình gõ không dấu để né bộ lọc: 'cam ket 100%', 'chua dut diem' -> Vẫn phải bị bắt!"""
        payload = {
            "workspace_id": 1,
            "channel": "facebook",
            "title": "Khoa hoc cam ket 100% viec lam",
            "body": "Phuong phap giup chua dut diem benh tri chi sau 3 ngay."
        }
        resp = client.post("/api/v1/contents/compliance-check", json=payload, headers=auth_headers["marketer"])
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "VIOLATION"
        assert data["can_submit"] is False
        assert len(data["violations"]) >= 2

    def test_adversarial_uppercase_and_special_chars(self, client: TestClient, auth_headers):
        """Cố tình gõ hoa xen kẽ hoặc thêm dấu câu: 'CAM KẾT 100%!!!', 'bÁn pHá GiÁ???' -> Bắt chuẩn xác!"""
        payload = {
            "workspace_id": 1,
            "channel": "facebook",
            "title": "BÁN PHÁ GIÁ TOÀN BỘ SẢN PHẨM???",
            "body": "CHÚNG TÔI CAM KẾT 100% HOÀN VỐN NGAY LẬP TỨC!!!"
        }
        resp = client.post("/api/v1/contents/compliance-check", json=payload, headers=auth_headers["marketer"])
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "VIOLATION"
        assert data["can_submit"] is False

    def test_adversarial_false_positive_protection(self, client: TestClient, auth_headers):
        """Chống báo động giả (False-Positive Protection): 'số 10' không được bắt nhầm thành 'số 1'."""
        payload = {
            "workspace_id": 1,
            "channel": "facebook",
            "title": "Top 10 mẹo tiếp thị số",
            "body": "Mẹo số 10 là xây dựng phễu email marketing thông minh cùng các chuyên gia hàng đầu."
        }
        resp = client.post("/api/v1/contents/compliance-check", json=payload, headers=auth_headers["marketer"])
        assert resp.status_code == 200
        data = resp.json()
        # Không được chứa vi phạm 'số 1' hay 'chuyên gia hàng đầu'
        flagged_words = [v["word"].lower() for v in data["violations"]]
        assert "số 1" not in flagged_words, f"False positive: 'số 10' was falsely matched as 'số 1'"
        assert data["status"] == "PASSED"
        assert data["score"] == 100

    def test_adversarial_tenant_isolation_banned_keywords(self, client: TestClient, auth_headers, db_session):
        """Kiểm tra cô lập từ cấm đa Workspace (Tenant Isolation): Từ cấm của WS 1 không làm ảnh hưởng WS 2."""
        # Tạo Workspace 2 độc lập
        ws2 = Workspace(
            id=2,
            name="Client B Workspace",
            slug="client-b",
            owner_id=1,
            status="ACTIVE"
        )
        db_session.add(ws2)
        db_session.commit()

        # Tạo Brand Kit riêng cho WS 2 với từ cấm duy nhất: "siêu phẩm số 1 châu á"
        bk2 = BrandKit(
            workspace_id=2,
            brand_name="Brand B",
            banned_keywords_json='["siêu phẩm số 1 châu á"]'
        )
        db_session.add(bk2)
        db_session.commit()

        # 1. Quét từ "siêu phẩm số 1 châu á" tại Workspace 2 -> Bị bắt BRAND_BANNED
        resp_ws2 = client.post("/api/v1/contents/compliance-check", json={
            "workspace_id": 2,
            "title": "Giới thiệu siêu phẩm số 1 châu á",
            "body": "Nội dung chất lượng."
        }, headers=auth_headers["marketer"])
        assert resp_ws2.status_code == 200
        data_ws2 = resp_ws2.json()
        assert any(v["category"] == "BRAND_BANNED" and "siêu phẩm số 1 châu á" in v["word"] for v in data_ws2["violations"])

        # 2. Quét từ "siêu phẩm số 1 châu á" tại Workspace 1 -> KHÔNG bị bắt BRAND_BANNED (cô lập dữ liệu thành công)
        resp_ws1 = client.post("/api/v1/contents/compliance-check", json={
            "workspace_id": 1,
            "title": "Giới thiệu siêu phẩm số 1 châu á",
            "body": "Nội dung chất lượng."
        }, headers=auth_headers["marketer"])
        assert resp_ws1.status_code == 200
        data_ws1 = resp_ws1.json()
        assert not any(v["category"] == "BRAND_BANNED" and "siêu phẩm số 1 châu á" in v["word"] for v in data_ws1["violations"])

    def test_adversarial_anti_tampering_approved_content(self, client: TestClient, auth_headers):
        """Kiểm tra chống gian lận (Anti-Tampering): Nếu sửa nội dung bài đã APPROVED, bài lập tức bị giáng cấp về AI_DRAFT!"""
        # Tạo bài, submit, và approve
        create_resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Bài viết nguyên bản đã duyệt",
            "body": "Nội dung ban đầu hoàn toàn sạch và chuẩn mực.",
            "status": "DRAFT"
        }, headers=auth_headers["marketer"])
        content_id = create_resp.json()["id"]

        client.post(f"/api/v1/contents/{content_id}/submit", headers=auth_headers["marketer"])
        client.post(f"/api/v1/contents/{content_id}/approve", headers=auth_headers["manager"])

        # Xác nhận đã APPROVED
        get_appr = client.get(f"/api/v1/contents/{content_id}", headers=auth_headers["marketer"])
        assert get_appr.json()["status"] == "APPROVED"

        # Kẻ gian cập nhật lén tiêu đề/nội dung
        update_resp = client.put(f"/api/v1/contents/{content_id}", json={
            "title": "Bài viết bị chèn link lừa đảo cam kết 100%",
            "body": "Nội dung đã bị chỉnh sửa sau khi được duyệt."
        }, headers=auth_headers["marketer"])
        assert update_resp.status_code == 200
        updated_data = update_resp.json()
        assert updated_data["status"] == "AI_DRAFT", f"Must be demoted to AI_DRAFT, got {updated_data['status']}"

    def test_adversarial_direct_status_jump_prevented(self, client: TestClient, auth_headers):
        """Cấm nhảy cóc trạng thái: Cố tình PUT /{id} với status='APPROVED' hoặc 'PUBLISHED' -> 400 Bad Request."""
        create_resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Bài viết thử nghiệm nhảy cóc",
            "body": "Nội dung kiểm tra lỗi bypass state machine.",
            "status": "DRAFT"
        }, headers=auth_headers["marketer"])
        content_id = create_resp.json()["id"]

        # Cố gắng chuyển sang APPROVED qua PUT
        jump_appr = client.put(f"/api/v1/contents/{content_id}", json={
            "status": "APPROVED"
        }, headers=auth_headers["marketer"])
        assert jump_appr.status_code == 400, "Direct status transition to APPROVED must be rejected with 400"

        # Cố gắng chuyển sang PUBLISHED qua PUT
        jump_pub = client.put(f"/api/v1/contents/{content_id}", json={
            "status": "PUBLISHED"
        }, headers=auth_headers["marketer"])
        assert jump_pub.status_code == 400, "Direct status transition to PUBLISHED must be rejected with 400"
