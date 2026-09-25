import json
import time
import unicodedata
import pytest
from fastapi.testclient import TestClient

from app.models.entities import MarketingContent, Campaign, BrandKit, ContentReview, User
from app.services.compliance.compliance_service import ComplianceScanner, strip_accents


def get_auth_headers(client: TestClient, email: str, password: str) -> dict:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def get_marketer_headers(client: TestClient) -> dict:
    return get_auth_headers(client, "marketer@ictu.edu.vn", "Marketer@123")


def get_manager_headers(client: TestClient) -> dict:
    return get_auth_headers(client, "manager@ictu.edu.vn", "Manager@123")


def get_approver_headers(client: TestClient) -> dict:
    return get_auth_headers(client, "approver@ictu.edu.vn", "Approver@123")


# ==============================================================================
# SUITE 1: ADVERSARIAL COMPLIANCE CA BIÊN & ROBUSTNESS
# ==============================================================================

class TestAdversarialComplianceBoundary:
    """Thử nghiệm các ca biên dị thường trên module Compliance & Guardrails."""

    @pytest.mark.parametrize("phrase_variant", [
        "BÁN PHÁ GIÁ",
        "ban pha gia",
        "BáN pHá GiÁ",
        "BÁN phá Giá",
        "bÁn PhÁ gIá",
        "BaN PHa GIa",
        unicodedata.normalize("NFD", "Bán phá giá"),  # Decomposed NFD
        unicodedata.normalize("NFC", "Bán phá giá"),  # Composed NFC
    ])
    def test_accent_and_case_variants_ban_pha_gia(self, phrase_variant):
        """1. Không phân biệt hoa thường và dấu tiếng Việt: Biến thể 'bán phá giá'."""
        res = ComplianceScanner.scan(
            title=f"Chương trình {phrase_variant} đặc biệt",
            body="Áp dụng cho tất cả khách hàng mới trong tuần lễ vàng."
        )
        assert res.status in ("WARNING", "VIOLATION"), f"Failed for variant: {phrase_variant}"
        assert any("bán phá giá" in v.word.lower() for v in res.violations)
        assert res.score < 100

    @pytest.mark.parametrize("phrase_variant", [
        "CAM KẾT 100%",
        "cam ket 100%",
        "cAm KếT 100%",
        "CAM KET 100%",
        "Cam Kết 100%",
        unicodedata.normalize("NFD", "Cam kết 100%"),
    ])
    def test_accent_and_case_variants_cam_ket_100(self, phrase_variant):
        """1. Không phân biệt hoa thường và dấu: Biến thể 'cam kết 100%'."""
        res = ComplianceScanner.scan(
            title=f"Khóa học {phrase_variant} có việc làm",
            body="Học viên hoàn toàn yên tâm khi tham gia khóa học này."
        )
        assert res.status == "VIOLATION"
        assert res.can_submit is False
        assert any("cam kết 100%" in v.word.lower() for v in res.violations)

    @pytest.mark.parametrize("phrase_variant", [
        "CHỮA DỨT ĐIỂM",
        "chua dut diem",
        "Chữa Dứt Điểm",
        "chua dut Diem",
        "CHUA DUT DIEM",
        unicodedata.normalize("NFD", "Chữa dứt điểm"),
    ])
    def test_accent_and_case_variants_chua_dut_diem(self, phrase_variant):
        """1. Không phân biệt hoa thường và dấu: Biến thể 'chữa dứt điểm'."""
        res = ComplianceScanner.scan(
            title="Liệu trình y tế",
            body=f"Phương pháp giúp {phrase_variant} bệnh đau dạ dày sau 1 tuần."
        )
        assert res.status == "VIOLATION"
        assert res.can_submit is False
        assert any("chữa dứt điểm" in v.word.lower() for v in res.violations)

    def test_brand_kit_custom_blacklist_accent_and_case(self):
        """1. Từ cấm trong Brand Kit của Workspace không phân biệt hoa thường và dấu."""
        custom_banned = ["RẺ RÁCH", "HÀNG NHÁI"]
        test_cases = [
            "Hàng này re rach không nên mua",
            "Cung cấp hang nhai tràn lan",
            "Sản phẩm Rẻ Rách nhất từng thấy",
            "hÀnG nHái cao cấp",
        ]
        for text in test_cases:
            res = ComplianceScanner.scan(
                title="Quảng cáo",
                body=text,
                custom_banned_keywords=custom_banned
            )
            assert res.status == "VIOLATION", f"Failed for text: {text}"
            assert res.can_submit is False
            assert any(v.category == "BRAND_BANNED" for v in res.violations)

    def test_overlapping_banned_phrases_deduplication(self):
        """2. Gom cụm vi phạm trùng lặp: Câu chứa nhiều từ cấm lồng nhau không bị trùng lặp lỗi."""
        text = (
            "Khóa học cam kết 100% việc làm và cam kết 100% lương cao. "
            "Chữa khỏi dứt điểm và chữa dứt điểm bệnh nan y. "
            "Sản phẩm rẻ nhất thị trường với giá rẻ nhất quả đất và rẻ nhất."
        )
        res = ComplianceScanner.scan(title="Tiêu đề", body=text)
        assert res.status == "VIOLATION"
        assert res.can_submit is False

        words_found = [v.word for v in res.violations]
        assert len(words_found) == len(set(words_found)), f"Duplicate violations detected: {words_found}"

    def test_repeated_identical_banned_phrase_stress(self):
        """2. Lặp lại cùng 1 từ cấm 50 lần -> Không bị treo, không bị 50 lỗi trùng lặp, xử lý < 200ms."""
        repeated_text = "cam kết 100% " * 50
        start_time = time.time()
        res = ComplianceScanner.scan(title="Spam test", body=repeated_text)
        elapsed = time.time() - start_time

        assert elapsed < 0.2, f"Scan took too long: {elapsed:.3f}s"
        assert res.status == "VIOLATION"
        assert res.can_submit is False
        matched_cam_ket = [v for v in res.violations if v.word == "cam kết 100%"]
        assert len(matched_cam_ket) == 1, f"Expected 1 violation, got {len(matched_cam_ket)}"

    def test_large_payload_stress(self):
        """2. Văn bản dài (3,000 từ) chứa từ cấm đan xen -> Quét an toàn trong < 500ms."""
        filler = "MarketFlow AI là nền tảng tiếp thị thông minh hàng đầu. " * 300
        text = filler + " cam kết 100% việc làm " + filler + " bán phá giá " + filler
        start_time = time.time()
        res = ComplianceScanner.scan(title="Stress test", body=text)
        elapsed = time.time() - start_time

        assert elapsed < 0.5, f"Scan took too long: {elapsed:.3f}s"
        assert res.status == "VIOLATION"
        assert res.can_submit is False
        words_found = {v.word for v in res.violations}
        assert "cam kết 100% việc làm" in words_found or "cam kết 100%" in words_found
        assert "bán phá giá" in words_found

    @pytest.mark.parametrize("clean_phrase", [
        "Gặp gỡ các chuyên gia hàng đầu trong ngành trí tuệ nhân tạo",
        "Tư vấn trực tiếp cùng bác sĩ đầu ngành da liễu",
        "Giới thiệu sản phẩm số 10 trong bộ sưu tập mùa hè",
        "Phiên bản số 100 cập nhật tính năng mới",
        "Nằm trong top 10 giải pháp MarTech hiệu quả nhất",
        "Sự kiện ra mắt ngày 10 tháng 10 năm 2026",
        "Chương trình đào tạo khóa số 12 chất lượng cao",
        "Chi phí số 10 trong bảng báo giá chi tiết",
        "Tạo ra hơn 100 việc làm mới cho cộng đồng",
        "Cam kết chất lượng dịch vụ và hỗ trợ khách hàng 24/7",
        "Phân tích chuyên sâu từ các chuyên gia giàu kinh nghiệm",
    ])
    def test_false_positive_shield_verified(self, clean_phrase):
        """3. Chống False-Positive: Các cụm từ hợp pháp ('chuyên gia hàng đầu', 'bác sĩ đầu ngành', 'sản phẩm số 10')
        TUYỆT ĐỐI KHÔNG được coi là vi phạm.
        """
        res = ComplianceScanner.scan(title="Thông tin chuẩn mực", body=clean_phrase)
        assert res.status == "PASSED", f"False positive triggered for: '{clean_phrase}', violations: {res.violations}"
        assert res.score == 100
        assert res.can_submit is True
        assert len(res.violations) == 0

    def test_false_positive_bug_cham_soc_falsely_flagged_as_soc(self):
        """[ADVERSARIAL FINDING BUG 1]: 'chăm sóc' KHÔNG bị bắt nhầm thành vi phạm 'sốc'.
        Đã khắc phục qua cơ chế whitelist/loại trừ cụm từ an toàn.
        """
        res = ComplianceScanner.scan(body="Dịch vụ chăm sóc khách hàng tận tâm và chuyên nghiệp")
        assert res.status == "PASSED"
        assert len(res.violations) == 0
        assert res.score == 100
        assert res.can_submit is True

    test_false_positive_bug_vulnerability_cham_soc = test_false_positive_bug_cham_soc_falsely_flagged_as_soc

    def test_false_positive_bug_da_cap_do_blocks_submission(self):
        """[ADVERSARIAL FINDING BUG 2]: 'đa cấp độ' (multi-level) KHÔNG bị bắt nhầm thành 'đa cấp' (HIGH).
        Hệ thống không còn khóa quyền submit (can_submit=True) của một nội dung hoàn toàn hợp pháp!
        """
        res = ComplianceScanner.scan(body="Khóa đào tạo kỹ năng số với lộ trình đa cấp độ rõ ràng")
        assert res.can_submit is True
        assert len(res.violations) == 0
        assert res.status == "PASSED"
        assert res.score == 100

    test_false_positive_bug_vulnerability_da_cap_do = test_false_positive_bug_da_cap_do_blocks_submission

    def test_false_positive_bug_so_1_with_vietnamese_number_thousands_separator(self):
        """[ADVERSARIAL FINDING BUG 3]: Định dạng số kiểu Việt Nam 'Doanh số 1.000 tỷ' KHÔNG bị bắt nhầm thành 'số 1'.
        Đã khắc phục ranh giới regex không bắt nhầm dấu chấm phân cách hàng nghìn.
        """
        res = ComplianceScanner.scan(body="Doanh số 1.000 tỷ đồng trong năm tài chính 2025")
        assert res.status == "PASSED"
        assert len(res.violations) == 0
        assert res.score == 100

    test_false_positive_bug_vulnerability_number_formatting = test_false_positive_bug_so_1_with_vietnamese_number_thousands_separator

    @pytest.mark.parametrize("empty_title,empty_body,empty_cta", [
        ("", "", ""),
        ("   ", "  \n\t  \r  ", "   "),
        (None, None, None),
        ("!@#$%^&*()_+-=[]{}|;':\",./<>?`~", "", None),
        ("🔥🔥🔥🚀🚀🚀💡💡💡🎉🎉🎉", "✨✨✨💯💯💯", None),
        ("\u200b\u200c\u200d\ufeff   \t\n", "", None),
    ])
    def test_empty_and_whitespace_inputs_safe(self, empty_title, empty_body, empty_cta):
        """4. Xử lý nội dung rỗng/khoảng trắng/ký tự đặc biệt: Trả về PASSED 100 điểm, không lỗi 500."""
        res = ComplianceScanner.scan(title=empty_title, body=empty_body, cta=empty_cta)
        assert res.status == "PASSED"
        assert res.score == 100
        assert res.can_submit is True
        assert len(res.violations) == 0

    def test_extremely_large_whitespace_safe(self):
        """4. Xử lý chuỗi khoảng trắng cực lớn (50,000 ký tự) không gây sập bộ nhớ hay timeout."""
        large_ws = " " * 50000
        res = ComplianceScanner.scan(title=large_ws, body=large_ws)
        assert res.status == "PASSED"
        assert res.score == 100
        assert len(res.violations) == 0

    def test_endpoint_compliance_check_empty_and_whitespace_http(self, client: TestClient):
        """4. Endpoint POST /api/v1/contents/compliance-check với nội dung rỗng trả về HTTP 200 PASSED."""
        mkt_headers = get_marketer_headers(client)

        resp_a = client.post("/api/v1/contents/compliance-check", json={
            "workspace_id": 1,
            "channel": "facebook",
            "title": "",
            "body": ""
        }, headers=mkt_headers)
        assert resp_a.status_code == 200
        assert resp_a.json()["status"] == "PASSED"
        assert resp_a.json()["score"] == 100

        resp_b = client.post("/api/v1/contents/compliance-check", json={
            "workspace_id": 1,
            "channel": "facebook",
            "title": "   ",
            "body": "\n\t  \r\n"
        }, headers=mkt_headers)
        assert resp_b.status_code == 200
        assert resp_b.json()["status"] == "PASSED"
        assert resp_b.json()["score"] == 100

        resp_c = client.post("/api/v1/contents/compliance-check", json={
            "workspace_id": 1,
            "channel": "facebook"
        }, headers=mkt_headers)
        assert resp_c.status_code == 200
        assert resp_c.json()["status"] == "PASSED"
        assert resp_c.json()["score"] == 100


# ==============================================================================
# SUITE 2: STATE MACHINE & RBAC SECURITY CHALLENGES
# ==============================================================================

class TestAdversarialStateMachineAndRBAC:
    """Thử thách đối kháng Máy trạng thái (State Machine) & Phân quyền RBAC."""

    def test_illegal_state_jump_put_approved_rejected(self, client: TestClient):
        """5. Nhảy trạng thái bất hợp pháp: PUT /contents/{id} với status: APPROVED phải bị 400 Bad Request."""
        mkt_headers = get_marketer_headers(client)

        create_resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Bài viết test nhảy trạng thái",
            "body": "Nội dung bài viết",
            "status": "DRAFT"
        }, headers=mkt_headers)
        assert create_resp.status_code == 201
        cid = create_resp.json()["id"]

        put_resp = client.put(f"/api/v1/contents/{cid}", json={"status": "APPROVED"}, headers=mkt_headers)
        assert put_resp.status_code == 400
        assert "APPROVED" in put_resp.json()["detail"]

        get_resp = client.get(f"/api/v1/contents/{cid}", headers=mkt_headers)
        assert get_resp.json()["status"] == "DRAFT"

    def test_illegal_state_jump_put_published_rejected(self, client: TestClient):
        """5. Nhảy trạng thái bất hợp pháp: PUT /contents/{id} với status: PUBLISHED phải bị 400 Bad Request."""
        mkt_headers = get_marketer_headers(client)

        create_resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Bài viết test nhảy trạng thái sang PUBLISHED",
            "body": "Nội dung bài viết",
            "status": "DRAFT"
        }, headers=mkt_headers)
        cid = create_resp.json()["id"]

        put_resp = client.put(f"/api/v1/contents/{cid}", json={"status": "PUBLISHED"}, headers=mkt_headers)
        assert put_resp.status_code == 400
        assert "PUBLISHED" in put_resp.json()["detail"]

    def test_illegal_create_with_approved_or_published_rejected(self, client: TestClient):
        """5. Cố tình POST /contents với status ban đầu là APPROVED hoặc PUBLISHED phải bị từ chối 400."""
        mkt_headers = get_marketer_headers(client)

        resp_app = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Hack APPROVED khi tạo",
            "body": "Nội dung",
            "status": "APPROVED"
        }, headers=mkt_headers)
        assert resp_app.status_code == 400
        assert "APPROVED" in resp_app.json()["detail"]

        resp_pub = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Hack PUBLISHED khi tạo",
            "body": "Nội dung",
            "status": "PUBLISHED"
        }, headers=mkt_headers)
        assert resp_pub.status_code == 400
        assert "PUBLISHED" in resp_pub.json()["detail"]

    def test_illegal_approve_without_submit_rejected(self, client: TestClient):
        """5. Gọi POST /approve khi bài viết chưa gửi duyệt (đang DRAFT) phải bị từ chối 400."""
        mkt_headers = get_marketer_headers(client)
        mgr_headers = get_manager_headers(client)

        create_resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Bài viết DRAFT chưa submit",
            "body": "Nội dung bài viết",
            "status": "DRAFT"
        }, headers=mkt_headers)
        cid = create_resp.json()["id"]

        appr_resp = client.post(f"/api/v1/contents/{cid}/approve", headers=mgr_headers)
        assert appr_resp.status_code == 400
        assert "IN_REVIEW" in appr_resp.json()["detail"]

    def test_illegal_publish_without_approval_rejected(self, client: TestClient):
        """5. Gọi POST /publish khi bài viết chưa APPROVED (đang DRAFT hoặc IN_REVIEW) phải bị 400."""
        mkt_headers = get_marketer_headers(client)
        mgr_headers = get_manager_headers(client)

        create_resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Bài viết chưa duyệt",
            "body": "Nội dung",
            "status": "DRAFT"
        }, headers=mkt_headers)
        cid = create_resp.json()["id"]

        pub_resp_1 = client.post(f"/api/v1/contents/{cid}/publish", headers=mgr_headers)
        assert pub_resp_1.status_code == 400
        assert "APPROVED" in pub_resp_1.json()["detail"]

        client.post(f"/api/v1/contents/{cid}/submit", headers=mkt_headers)
        pub_resp_2 = client.post(f"/api/v1/contents/{cid}/publish", headers=mgr_headers)
        assert pub_resp_2.status_code == 400
        assert "APPROVED" in pub_resp_2.json()["detail"]

    def test_rollback_on_modification_of_approved_content(self, client: TestClient):
        """6. Hoàn trả trạng thái: Khi bài viết đã APPROVED bị sửa nội dung qua PUT -> Tự động hoàn về AI_DRAFT/DRAFT."""
        mkt_headers = get_marketer_headers(client)
        mgr_headers = get_manager_headers(client)

        create_resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Tiêu đề chuẩn đã duyệt",
            "body": "Nội dung chuẩn đã duyệt",
            "cta": "Đăng ký ngay",
            "status": "DRAFT"
        }, headers=mkt_headers)
        cid = create_resp.json()["id"]

        client.post(f"/api/v1/contents/{cid}/submit", headers=mkt_headers)
        app_resp = client.post(f"/api/v1/contents/{cid}/approve", headers=mgr_headers)
        assert app_resp.status_code == 200
        assert app_resp.json()["status"] == "APPROVED"

        # Case 6A: Chỉnh sửa title -> Bị hoàn về AI_DRAFT
        edit_title = client.put(f"/api/v1/contents/{cid}", json={"title": "Tiêu đề bị sửa"}, headers=mkt_headers)
        assert edit_title.status_code == 200
        assert edit_title.json()["status"] in ("AI_DRAFT", "DRAFT")

        # Duyệt lại thành APPROVED
        client.post(f"/api/v1/contents/{cid}/submit", headers=mkt_headers)
        client.post(f"/api/v1/contents/{cid}/approve", headers=mgr_headers)

        # Case 6B: Chỉnh sửa body -> Bị hoàn về AI_DRAFT
        edit_body = client.put(f"/api/v1/contents/{cid}", json={"body": "Nội dung bị sửa"}, headers=mkt_headers)
        assert edit_body.status_code == 200
        assert edit_body.json()["status"] in ("AI_DRAFT", "DRAFT")

        # Duyệt lại thành APPROVED
        client.post(f"/api/v1/contents/{cid}/submit", headers=mkt_headers)
        client.post(f"/api/v1/contents/{cid}/approve", headers=mgr_headers)

        # Case 6C: Chỉnh sửa CTA -> Bị hoàn về AI_DRAFT
        edit_cta = client.put(f"/api/v1/contents/{cid}", json={"cta": "CTA bị sửa"}, headers=mkt_headers)
        assert edit_cta.status_code == 200
        assert edit_cta.json()["status"] in ("AI_DRAFT", "DRAFT")

    def test_state_machine_vulnerability_tampering_published_content(self, client: TestClient):
        """[ADVERSARIAL FINDING BUG 4]: Sửa nội dung của bài viết ĐÃ PUBLISHED phải bị hoàn trạng thái về AI_DRAFT!
        Đã khắc phục: Ngăn chặn triệt để lỗ hổng bypass Review Gate trên bài đã xuất bản.
        """
        mkt_headers = get_marketer_headers(client)
        mgr_headers = get_manager_headers(client)

        create_resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Bài viết chuẩn bị publish",
            "body": "Nội dung đã được duyệt kỹ càng",
            "status": "DRAFT"
        }, headers=mkt_headers)
        cid = create_resp.json()["id"]

        client.post(f"/api/v1/contents/{cid}/submit", headers=mkt_headers)
        client.post(f"/api/v1/contents/{cid}/approve", headers=mgr_headers)
        client.post(f"/api/v1/contents/{cid}/publish", headers=mgr_headers)

        # Kiểm tra bài đã PUBLISHED
        check_pub = client.get(f"/api/v1/contents/{cid}", headers=mkt_headers)
        assert check_pub.json()["status"] == "PUBLISHED"

        # Marketer PUT chỉnh sửa tiêu đề bài viết ĐÃ PUBLISHED
        edit_resp = client.put(f"/api/v1/contents/{cid}", json={
            "title": "NỘI DUNG ĐÃ BỊ THAY ĐỔI SAU XUẤT BẢN"
        }, headers=mkt_headers)
        assert edit_resp.status_code == 200
        # Ghi nhận: Trạng thái bắt buộc bị giáng về AI_DRAFT để yêu cầu duyệt lại!
        status_after_edit = edit_resp.json()["status"]
        assert status_after_edit == "AI_DRAFT", f"Đã khắc phục: Trạng thái chuyển về {status_after_edit}"

    def test_rejection_without_feedback_rejected(self, client: TestClient):
        """7. Từ chối không có lý do: Gọi POST /{id}/reject mà không gửi kèm feedback -> Bị từ chối với HTTP 400 hoặc 422."""
        mkt_headers = get_marketer_headers(client)
        mgr_headers = get_manager_headers(client)

        create_resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Bài viết chờ duyệt",
            "body": "Nội dung bài viết",
            "status": "DRAFT"
        }, headers=mkt_headers)
        cid = create_resp.json()["id"]

        client.post(f"/api/v1/contents/{cid}/submit", headers=mkt_headers)

        # Case 7A: Gửi body rỗng {}
        resp_empty = client.post(f"/api/v1/contents/{cid}/reject", json={}, headers=mgr_headers)
        assert resp_empty.status_code in (400, 422), f"Expected 400 or 422, got {resp_empty.status_code}"

        # Case 7B: Gửi thiếu field reason
        resp_no_reason = client.post(f"/api/v1/contents/{cid}/reject", json={"decision": "REJECTED"}, headers=mgr_headers)
        assert resp_no_reason.status_code in (400, 422), f"Expected 400 or 422, got {resp_no_reason.status_code}"

        # Case 7C: Gửi reason là chuỗi rỗng ""
        resp_blank = client.post(f"/api/v1/contents/{cid}/reject", json={"decision": "REJECTED", "reason": ""}, headers=mgr_headers)
        assert resp_blank.status_code in (400, 422), f"Expected 400 or 422, got {resp_blank.status_code}"

        # Case 7D: Gửi reason có độ dài < 3 ký tự
        resp_short = client.post(f"/api/v1/contents/{cid}/reject", json={"decision": "REJECTED", "reason": "No"}, headers=mgr_headers)
        assert resp_short.status_code in (400, 422), f"Expected 400 or 422, got {resp_short.status_code}"

        # Đảm bảo bài viết VẪN ở trạng thái IN_REVIEW, chưa bị reject trái phép
        check_resp = client.get(f"/api/v1/contents/{cid}", headers=mkt_headers)
        assert check_resp.json()["status"] == "IN_REVIEW"

        # Case 7E: Gửi kèm reason hợp lệ -> Thành công
        resp_valid = client.post(f"/api/v1/contents/{cid}/reject", json={
            "decision": "REJECTED",
            "reason": "Nội dung cần điều chỉnh lại văn phong phù hợp với thương hiệu."
        }, headers=mgr_headers)
        assert resp_valid.status_code == 200
        assert resp_valid.json()["status"] == "REJECTED"

    def test_rejection_whitespace_only_bypass_vulnerability(self, client: TestClient):
        """[ADVERSARIAL FINDING BUG 5]: Lý do từ chối CHỈ gồm khoảng trắng '   ' BỊ TỪ CHỐI (HTTP 400 hoặc 422)!
        Đã khắc phục: ReviewCreate và reject_content bắt buộc lý do từ chối phải có nội dung thực chất (>= 3 ký tự).
        """
        mkt_headers = get_marketer_headers(client)
        mgr_headers = get_manager_headers(client)

        create_resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Bài viết test whitespace reject",
            "body": "Nội dung bài viết",
            "status": "DRAFT"
        }, headers=mkt_headers)
        cid = create_resp.json()["id"]

        client.post(f"/api/v1/contents/{cid}/submit", headers=mkt_headers)

        # Gửi lý do chỉ gồm 3 khoảng trắng
        resp_spaces = client.post(f"/api/v1/contents/{cid}/reject", json={
            "decision": "REJECTED",
            "reason": "   "
        }, headers=mgr_headers)
        # Ghi nhận: Bị từ chối với HTTP 400 Bad Request
        assert resp_spaces.status_code == 400, f"Đã khắc phục: Whitespace-only reason bị từ chối với HTTP 400 (got {resp_spaces.status_code})"
        check_content = client.get(f"/api/v1/contents/{cid}", headers=mkt_headers)
        assert check_content.json()["status"] == "IN_REVIEW"

    def test_rbac_marketer_blocked_from_approval(self, client: TestClient):
        """8. Chặn Marketer phê duyệt: Tài khoản MARKETER gửi POST /approve -> Phải nhận HTTP 403 Forbidden!"""
        mkt_headers = get_marketer_headers(client)

        create_resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Bài viết test RBAC Marketer Approve",
            "body": "Nội dung",
            "status": "DRAFT"
        }, headers=mkt_headers)
        cid = create_resp.json()["id"]

        client.post(f"/api/v1/contents/{cid}/submit", headers=mkt_headers)

        appr_resp = client.post(f"/api/v1/contents/{cid}/approve", headers=mkt_headers)
        assert appr_resp.status_code == 403, f"Expected 403 Forbidden, got {appr_resp.status_code}"

    def test_rbac_marketer_blocked_from_rejection(self, client: TestClient):
        """8. Chặn Marketer từ chối: Tài khoản MARKETER gửi POST /reject -> Phải nhận HTTP 403 Forbidden!"""
        mkt_headers = get_marketer_headers(client)

        create_resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Bài viết test RBAC Marketer Reject",
            "body": "Nội dung",
            "status": "DRAFT"
        }, headers=mkt_headers)
        cid = create_resp.json()["id"]

        client.post(f"/api/v1/contents/{cid}/submit", headers=mkt_headers)

        rej_resp = client.post(f"/api/v1/contents/{cid}/reject", json={
            "decision": "REJECTED",
            "reason": "Marketer tự reject bài của mình"
        }, headers=mkt_headers)
        assert rej_resp.status_code == 403, f"Expected 403 Forbidden, got {rej_resp.status_code}"

    def test_rbac_marketer_blocked_from_publish(self, client: TestClient):
        """8. Chặn Marketer xuất bản: Tài khoản MARKETER gửi POST /publish -> Phải nhận HTTP 403 Forbidden!"""
        mkt_headers = get_marketer_headers(client)
        mgr_headers = get_manager_headers(client)

        create_resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Bài viết test RBAC Publish",
            "body": "Nội dung",
            "status": "DRAFT"
        }, headers=mkt_headers)
        cid = create_resp.json()["id"]

        client.post(f"/api/v1/contents/{cid}/submit", headers=mkt_headers)
        client.post(f"/api/v1/contents/{cid}/approve", headers=mgr_headers)

        pub_resp = client.post(f"/api/v1/contents/{cid}/publish", headers=mkt_headers)
        assert pub_resp.status_code == 403, f"Expected 403 Forbidden, got {pub_resp.status_code}"

    def test_rbac_client_approver_blocked_from_publish(self, client: TestClient):
        """8. Client Approver chỉ có quyền duyệt/từ chối, KHÔNG có quyền publish (chỉ dành cho Manager)."""
        mkt_headers = get_marketer_headers(client)
        app_headers = get_approver_headers(client)

        create_resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Bài viết test Client Approver Publish",
            "body": "Nội dung",
            "status": "DRAFT"
        }, headers=mkt_headers)
        cid = create_resp.json()["id"]

        client.post(f"/api/v1/contents/{cid}/submit", headers=mkt_headers)
        client.post(f"/api/v1/contents/{cid}/approve", headers=app_headers)

        pub_resp = client.post(f"/api/v1/contents/{cid}/publish", headers=app_headers)
        assert pub_resp.status_code == 403, f"Expected 403 Forbidden, got {pub_resp.status_code}"
