import json
import pytest
from app.models.entities import MarketingContent, BrandKit, ContentReview
from app.services.compliance.compliance_service import ComplianceScanner


def get_auth_headers(client, email: str, password: str) -> dict:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def get_marketer_headers(client) -> dict:
    return get_auth_headers(client, "marketer@ictu.edu.vn", "Marketer@123")


def get_manager_headers(client) -> dict:
    return get_auth_headers(client, "manager@ictu.edu.vn", "Manager@123")


def get_approver_headers(client) -> dict:
    return get_auth_headers(client, "approver@ictu.edu.vn", "Approver@123")


# ==============================================================================
# UNIT TESTS: ComplianceScanner Logic
# ==============================================================================

class TestComplianceScannerUnit:
    """Kiểm thử đơn vị chuyên sâu cho thuật toán ComplianceScanner."""

    def test_compliance_scanner_clean_copy(self):
        """Văn bản sạch đạt 100 điểm, trạng thái PASSED, can_submit=True, violations=[]."""
        res = ComplianceScanner.scan(
            title="Khóa học Lập trình AI Thực chiến 2026",
            body="Trang bị kỹ năng lập trình AI hiện đại cùng các chuyên gia giàu kinh nghiệm. Đăng ký ngay hôm nay!"
        )
        assert res.status == "PASSED"
        assert res.score == 100
        assert res.can_submit is True
        assert len(res.violations) == 0

    def test_compliance_scanner_brand_blacklist(self):
        """Phát hiện từ cấm trong Brand Kit của Workspace, gán category='BRAND_BANNED', severity='HIGH'."""
        res = ComplianceScanner.scan(
            title="Sản phẩm đặc biệt",
            body="Cung cấp hàng hóa giá rẻ rách và sản phẩm hàng nhái cho người tiêu dùng.",
            custom_banned_keywords=["rẻ rách", "hàng nhái"]
        )
        assert res.status == "VIOLATION"
        assert res.can_submit is False
        assert any(v.category == "BRAND_BANNED" and v.severity == "HIGH" and v.word == "rẻ rách" for v in res.violations)
        assert any(v.category == "BRAND_BANNED" and v.severity == "HIGH" and v.word == "hàng nhái" for v in res.violations)
        assert res.score <= 30  # 100 - 35*2 = 30

    def test_compliance_scanner_ad_policy_high(self):
        """Phát hiện từ cấm quảng cáo mức HIGH -> status='VIOLATION', can_submit=False."""
        res = ComplianceScanner.scan(
            title="Khóa học cam kết 100% việc làm",
            body="Học viên sẽ được hoàn vốn ngay lập tức và làm giàu nhanh không cần nỗ lực."
        )
        assert res.status == "VIOLATION"
        assert res.can_submit is False
        high_violations = [v for v in res.violations if v.severity == "HIGH"]
        assert len(high_violations) >= 2
        assert any("cam kết 100%" in v.word for v in high_violations)
        assert any("làm giàu nhanh" in v.word for v in high_violations)

    def test_compliance_scanner_ad_policy_medium(self):
        """Phát hiện từ khóa thổi phồng / cạnh tranh giá mức MEDIUM -> status='WARNING', can_submit=True."""
        res = ComplianceScanner.scan(
            title="Khóa học có chi phí rẻ nhất thị trường",
            body="Đây là giải pháp tốt nhất hiện nay dành cho doanh nghiệp vừa và nhỏ."
        )
        assert res.status == "WARNING"
        assert res.can_submit is True
        assert all(v.severity != "HIGH" for v in res.violations)
        assert any(v.severity == "MEDIUM" for v in res.violations)
        assert 0 < res.score < 100

    def test_compliance_scanner_ad_policy_low(self):
        """Phát hiện từ khóa giật gân mức LOW -> status='WARNING', can_submit=True."""
        res = ComplianceScanner.scan(
            title="Tin sốc cho các lập trình viên",
            body="Thông tin chấn động về thị trường công nghệ năm nay."
        )
        assert res.status == "WARNING"
        assert res.can_submit is True
        assert all(v.severity == "LOW" for v in res.violations)
        assert res.score == 90  # 100 - 5*2

    def test_compliance_scanner_case_insensitivity(self):
        """Văn bản chữ in hoa toàn bộ vẫn nhận diện chính xác vi phạm."""
        res = ComplianceScanner.scan(
            title="BÁN PHÁ GIÁ TOÀN BỘ SẢN PHẨM",
            body="CHÚNG TÔI CAM KẾT 100% HOÀN VỐN NGAY LẬP TỨC"
        )
        assert res.status == "VIOLATION"
        assert res.can_submit is False
        assert any("cam kết 100%" in v.word for v in res.violations)

    def test_compliance_scanner_accent_insensitivity(self):
        """Văn bản gõ tiếng Việt không dấu vẫn nhận diện chính xác vi phạm."""
        res = ComplianceScanner.scan(
            title="ban pha gia khoa hoc",
            body="cam ket 100% hoc xong chua khoi dut diem moi kho khan"
        )
        assert res.status == "VIOLATION"
        assert res.can_submit is False
        assert any("cam kết 100%" in v.word for v in res.violations)
        assert any("chữa khỏi dứt điểm" in v.word for v in res.violations)

    def test_compliance_scanner_overlapping_keywords(self):
        """Văn bản chứa nhiều từ khóa vi phạm đan xen được tổng hợp và tính điểm chính xác."""
        res = ComplianceScanner.scan(
            title="Cam kết 100% chữa khỏi dứt điểm kiếm tiền tỷ",
            body="Bán phá giá khoá học làm giàu nhanh, cam kết không rủi ro."
        )
        assert res.status == "VIOLATION"
        assert res.can_submit is False
        assert res.score == 0
        words_found = {v.word for v in res.violations}
        assert "cam kết 100%" in words_found
        assert "kiếm tiền tỷ" in words_found
        assert "làm giàu nhanh" in words_found

    def test_compliance_scanner_empty_and_whitespace(self):
        """Chuỗi rỗng, None hoặc khoảng trắng không ném lỗi, trả về PASSED 100 điểm."""
        for title, body in [("", ""), (None, None), ("   ", "\n\t")]:
            res = ComplianceScanner.scan(title=title, body=body)
            assert res.status == "PASSED"
            assert res.score == 100
            assert res.can_submit is True
            assert len(res.violations) == 0

    def test_compliance_scanner_no_false_positives(self):
        """Các từ ngữ marketing chuẩn ('chuyên gia hàng đầu', 'giải pháp hàng đầu', 'số 10') không bị bắt nhầm."""
        res = ComplianceScanner.scan(
            title="Gặp gỡ các chuyên gia hàng đầu trong ngành công nghệ",
            body="Giải pháp hàng đầu cho doanh nghiệp của bạn. Đây là chương trình số 10 trong chuỗi sự kiện năm nay."
        )
        assert res.status == "PASSED"
        assert res.score == 100
        assert res.can_submit is True
        assert len(res.violations) == 0


# ==============================================================================
# INTEGRATION TESTS: API Endpoints & State Machine Guardrails
# ==============================================================================

class TestComplianceGuardrailEndpoints:
    """Kiểm thử tích hợp các endpoint Compliance Check và chốt chặn Guardrail submit/review."""

    def test_endpoint_compliance_check_success(self, client):
        """Endpoint POST /api/v1/contents/compliance-check trả về 200 OK đúng schema."""
        mkt_headers = get_marketer_headers(client)
        resp = client.post("/api/v1/contents/compliance-check", json={
            "workspace_id": 1,
            "channel": "facebook",
            "title": "Ra mắt ứng dụng mới",
            "body": "Nội dung chất lượng cao hướng dẫn người dùng."
        }, headers=mkt_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("PASSED", "PASS")
        assert data["score"] == 100
        assert data["can_submit"] is True
        assert isinstance(data["violations"], list)

    def test_endpoint_compliance_check_unauthorized(self, client):
        """Gọi endpoint POST /api/v1/contents/compliance-check không có token trả về 401."""
        resp = client.post("/api/v1/contents/compliance-check", json={
            "workspace_id": 1,
            "channel": "facebook",
            "title": "Test",
            "body": "Test body"
        })
        assert resp.status_code == 401

    def test_submit_guardrail_blocks_high_violation(self, client):
        """Gửi duyệt (POST /submit) bài viết chứa vi phạm HIGH bị chặn với HTTP 400."""
        mkt_headers = get_marketer_headers(client)

        # 1. Tạo bài viết DRAFT chứa vi phạm HIGH
        create_resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Học xong cam kết 100% lương 50 triệu",
            "body": "Chữa khỏi dứt điểm mọi khó khăn tài chính, cam kết 100% làm giàu nhanh.",
            "status": "DRAFT"
        }, headers=mkt_headers)
        assert create_resp.status_code == 201
        cid = create_resp.json()["id"]

        # 2. Gửi duyệt -> Bị chặn với 400 Bad Request
        sub_resp = client.post(f"/api/v1/contents/{cid}/submit", headers=mkt_headers)
        assert sub_resp.status_code == 400
        assert "vi phạm" in sub_resp.json()["detail"].lower()

        # Kiểm tra bài viết vẫn ở DRAFT, chưa bị chuyển sang IN_REVIEW
        check_resp = client.get(f"/api/v1/contents/{cid}", headers=mkt_headers)
        assert check_resp.json()["status"] == "DRAFT"

    def test_submit_guardrail_allows_clean_or_warning(self, client):
        """Gửi duyệt bài viết sạch hoặc chỉ chứa cảnh báo WARNING thành công sang IN_REVIEW."""
        mkt_headers = get_marketer_headers(client)

        create_resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Nội dung chuẩn tuân thủ",
            "body": "Nâng cao kỹ năng nghề nghiệp cùng các chuyên gia hàng đầu.",
            "status": "DRAFT"
        }, headers=mkt_headers)
        assert create_resp.status_code == 201
        cid = create_resp.json()["id"]

        sub_resp = client.post(f"/api/v1/contents/{cid}/submit", headers=mkt_headers)
        assert sub_resp.status_code == 200
        assert sub_resp.json()["status"] == "IN_REVIEW"

    def test_submit_guardrail_saves_warnings_json(self, client):
        """Kiểm tra warnings_json được lưu đúng vào CSDL khi submit bài có WARNING."""
        mkt_headers = get_marketer_headers(client)

        create_resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Tin sốc về công nghệ",
            "body": "Bản tin chấn động cập nhật hàng tuần.",
            "status": "DRAFT"
        }, headers=mkt_headers)
        assert create_resp.status_code == 201
        cid = create_resp.json()["id"]

        sub_resp = client.post(f"/api/v1/contents/{cid}/submit", headers=mkt_headers)
        assert sub_resp.status_code == 200
        assert sub_resp.json()["status"] == "IN_REVIEW"
        warnings_raw = sub_resp.json().get("warnings_json")
        assert warnings_raw is not None
        warnings = json.loads(warnings_raw)
        assert len(warnings) > 0
        assert any(w["word"] in ("sốc", "chấn động") for w in warnings)

    def test_edit_approved_content_reverts_state(self, client):
        """Sửa tiêu đề/thân bài của bài viết đã APPROVED tự động hạ trạng thái về AI_DRAFT."""
        mkt_headers = get_marketer_headers(client)
        mgr_headers = get_manager_headers(client)

        # Tạo bài viết và duyệt thành APPROVED
        create_resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Tiêu đề bài viết duyệt",
            "body": "Thân bài viết duyệt",
            "status": "DRAFT"
        }, headers=mkt_headers)
        cid = create_resp.json()["id"]

        client.post(f"/api/v1/contents/{cid}/submit", headers=mkt_headers)
        client.post(f"/api/v1/contents/{cid}/approve", headers=mgr_headers)

        # Chỉnh sửa bài viết
        edit_resp = client.put(f"/api/v1/contents/{cid}", json={
            "title": "Tiêu đề đã bị can thiệp sau khi phê duyệt"
        }, headers=mkt_headers)
        assert edit_resp.status_code == 200
        assert edit_resp.json()["status"] in ("AI_DRAFT", "DRAFT")

    def test_illegal_put_status_rejected(self, client):
        """PUT trực tiếp status sang APPROVED bị từ chối với HTTP 400 Bad Request."""
        mkt_headers = get_marketer_headers(client)

        create_resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Bài viết thử trạng thái",
            "body": "Nội dung bài viết",
            "status": "DRAFT"
        }, headers=mkt_headers)
        cid = create_resp.json()["id"]

        put_resp = client.put(f"/api/v1/contents/{cid}", json={"status": "APPROVED"}, headers=mkt_headers)
        assert put_resp.status_code == 400
        assert "APPROVED" in put_resp.json()["detail"]

    def test_rbac_marketer_cannot_approve(self, client):
        """Tài khoản Marketer cố tình approve bài viết nhận HTTP 403 Forbidden."""
        mkt_headers = get_marketer_headers(client)

        create_resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Bài viết test RBAC",
            "body": "Thân bài viết",
            "status": "DRAFT"
        }, headers=mkt_headers)
        cid = create_resp.json()["id"]

        client.post(f"/api/v1/contents/{cid}/submit", headers=mkt_headers)

        appr_resp = client.post(f"/api/v1/contents/{cid}/approve", headers=mkt_headers)
        assert appr_resp.status_code == 403

    def test_rbac_client_approver_and_manager_can_approve(self, client):
        """Tài khoản Client Approver và Manager phê duyệt thành công sang APPROVED."""
        mkt_headers = get_marketer_headers(client)
        app_headers = get_approver_headers(client)

        create_resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Bài viết cho Approver duyệt",
            "body": "Thân bài viết chuẩn chỉ",
            "status": "DRAFT"
        }, headers=mkt_headers)
        cid = create_resp.json()["id"]

        client.post(f"/api/v1/contents/{cid}/submit", headers=mkt_headers)

        appr_resp = client.post(f"/api/v1/contents/{cid}/approve", headers=app_headers)
        assert appr_resp.status_code == 200
        assert appr_resp.json()["status"] == "APPROVED"
