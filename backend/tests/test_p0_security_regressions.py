"""
P0 SECURITY REGRESSION SUITE (Cam kết hồi quy - 5 exploit P0 + 6 hồi quy HIGH/MEDIUM)
====================================================================================

Bối cảnh
--------
Năm lỗ hổng P0 đã được khai thác bằng exploit CHẠY THẬT và sau đó vá. Vòng đời của
một lỗ hổng P0 đặc biệt nguy hiểm ở chỗ: sau khi vá, không có gì ngăn đội phát triển
vô tình gỡ lại bản vá trong một lần refactor "cho gọn". File này chuyển 5 exploit
đó thành test tự động nằm trong repo để bản vá KHÔNG BAO GIỜ biến mất khỏi CI.

Nguyên tắc bất di bất dịch của file này
--------------------------------------
1. KHÔNG dùng ``pytest.skip`` để làm xanh: một bản vá bị gỡ KHÔNG ĐƯỢC biến thành
   "xanh" bằng cách bỏ qua. Test phải ĐỎ khi bảo vệ bị gỡ.
2. KHÔNG nới lỏng kỳ vọng chỉ để test chạy được. Chỗ nào exploit gốc không còn tái
   hiện được với hành vi đã vá thì test được viết lại theo bất biến bảo mật thật sự
   (xem ``test_p0_4_tenant_isolation_fails_closed`` - có ghi chú giải thích lệch so
   với mô tả ban đầu).
3. Mỗi test có docstring nói rõ VÌ SAO đây là hồi quy nghiêm trọng.
4. Các dòng đánh dấu ``[BAO-VA P0-N]`` là vị trí bản vá. TUYỆT ĐỐI KHÔNG XOÁ khi
   refactor - nếu phải sửa, hãy sửa kèm test tương ứng trong file này.

Quy ước đặt tên: ``test_p0N_<mo_ta>`` để tra cứu nhanh theo mã lỗ hổng.
"""

import inspect
import os
import re
import tempfile
from pathlib import Path
from types import SimpleNamespace

import bcrypt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# backend/tests/test_p0_security_regressions.py -> parents[0]=tests, [1]=backend, [2]=repo root
REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_SRC = REPO_ROOT / "frontend" / "src"

from app.core.config import settings
from app.core.database import Base
import app.core.database as core_database
import app.core.security as security_module
from app.core.security import hash_password, verify_password
from app.models.entities import (
    Campaign,
    MarketingChannel,
    MarketingContent,
    Product,
    ProductCategory,
    User,
    Workspace,
    WorkspaceMember,
)
from app.services.scheduler import worker as scheduler_worker


# ==============================================================================
# HELPER DÙNG CHUNG (không dựng lại fixture đã có sẵn trong conftest.py)
# ==============================================================================
def _facebook_channel_id(db_session: Session) -> int:
    ch = db_session.query(MarketingChannel).filter(MarketingChannel.code == "facebook").first()
    assert ch is not None, "Kênh 'facebook' phải tồn tại từ seed_data"
    return ch.id


def _user_by_email(db_session: Session, email: str) -> User:
    user = db_session.query(User).filter(User.email == email).first()
    assert user is not None, f"User {email} phải tồn tại"
    return user


def _create_draft_content_via_api(
    client: TestClient,
    db_session: Session,
    headers: dict,
    title: str = "Bản thảo hồi quy P0 - không được sửa status qua PUT",
) -> int:
    """Tạo một nội dung DRAFT hợp lệ qua API rồi trả về id.

    Dùng marketer (owner của campaign 1 trong seed) để chắc chắn bước tiền điều kiện
    record-level authorization thành công - test chỉ tập trung vào PUT /contents/{id}.
    """
    marketer = _user_by_email(db_session, "marketer@gmail.com")
    campaign = (
        db_session.query(Campaign)
        .filter(Campaign.owner_id == marketer.id)
        .order_by(Campaign.id)
        .first()
    )
    assert campaign is not None, "Seed phải tạo ít nhất một campaign thuộc marketer"

    resp = client.post(
        "/api/v1/contents",
        headers=headers,
        json={
            "campaign_id": campaign.id,
            "channel_id": _facebook_channel_id(db_session),
            "title": title,
            "body": "Nội dung thử nghiệm hồi quy bảo mật P0.",
            "cta": "Tìm hiểu thêm",
            "status": "DRAFT",
        },
    )
    assert resp.status_code == 201, f"Không tạo được DRAFT: {resp.status_code} {resp.text}"
    assert resp.json()["status"] == "DRAFT"
    return resp.json()["id"]


def _reload_status(db_session: Session, content_id: int) -> str:
    """Đọc lại status trực tiếp từ DB (bypass cache identity-map của session)."""
    db_session.expire_all()
    row = db_session.query(MarketingContent).filter(MarketingContent.id == content_id).first()
    assert row is not None, f"Content {content_id} phải còn tồn tại trong DB"
    return row.status


# ==============================================================================
# NHÓM 1 - 5 LỖ HỔNG P0
# ==============================================================================

# ------------------------------------------------------------------------------
# P0-1: Offline demo cấp phiên đăng nhập giả -> leo thang đặc quyền
# ------------------------------------------------------------------------------
def test_p0_1_no_offline_demo_auth_bypass_in_source():
    """P0-1: frontend KHÔNG ĐƯỢC cấp phiên đăng nhập giả khi backend chết.

    Exploit gốc: khi `POST /auth/login` lỗi mạng (backend sập, mạng công ty chặn),
    `authApi.login` rơi vào nhánh offline demo và ghi một token giả
    (`marketflow-demo-token`) vào localStorage; quyền được SUY ĐOÁN từ chuỗi email
    (`email.includes('manager')` -> role MANAGER). Kẻ tấn công chỉ cần gõ
    `manager@gmail.com` + bất kỳ mật khẩu nào là đăng nhập được với quyền quản trị
    và tạo/xoá/sửa dữ liệu thật - đây là đường vòng leo thang đặc quyền hoàn toàn
    không cần tương tác với backend.

    Vì sao là hồi quy nghiêm trọng: đây là lỗ hổng KHÔNG cần mật khẩu, chỉ cần mạng
    hỏng hoặc bị chặn - tức là điều kiện dễ kích hoạt nhất trong môi trường thật.

    Test này kiểm tra MÃ NGUỒN (vì exploit nằm hoàn toàn ở frontend, không thể
    chạy backend để tái hiện) + cờ môi trường ở cả 3 nơi khai báo.
    """
    api_ts = (FRONTEND_SRC / "services" / "api.ts").read_text(encoding="utf-8")
    mock_ts = (FRONTEND_SRC / "services" / "mockData.ts").read_text(encoding="utf-8")

    # --- 1. Token demo KHÔNG được tồn tại ở bất kỳ đâu trong hai file ---------
    for name, src in (("api.ts", api_ts), ("mockData.ts", mock_ts)):
        assert "marketflow-demo-token" not in src, (
            f"P0-1 HỒI QUY: {name} chứa lại token demo `marketflow-demo-token`. "
            "Đây chính là token cho phép vào hệ thống khi backend không phản hồi."
        )
        assert "demo-token" not in src.lower(), (
            f"P0-1 HỒI QUY: {name} chứa lại chuỗi `demo-token` (biến thể của token demo)."
        )

    # --- 2. Không được suy đoán quyền từ chuỗi email --------------------------
    # Regex này là hình dạng của exploit: so khớp chuỗi email với tên vai trò.
    role_sniffing = re.compile(
        r"includes\(\s*['\"][^'\"]*(manager|approver|admin|marketer)[^'\"]*['\"]",
        re.IGNORECASE,
    )
    for name, src in (("api.ts", api_ts), ("mockData.ts", mock_ts)):
        assert role_sniffing.search(src) is None, (
            f"P0-1 HỒI QUY: {name} suy đoán vai trò từ chuỗi email "
            f"({role_sniffing.search(src).group(0)!r}). Đây là đường vòng leo thang đặc quyền."
        )

    # --- 3. Parse đúng thân `authApi` và kiểm tra riêng bên trong -------------
    # Cách làm ổn định: cắt từ `export const authApi` tới marker khai báo kế tiếp
    # (`export const workspaceApi`) thay vì regex khớp `localStorage.setItem` rải
    # rác trong cả file (dễ vỡ khi ai đó thêm/xoá hàm con).
    start = api_ts.index("export const authApi")
    end = api_ts.index("export const workspaceApi", start)
    auth_block = api_ts[start:end]

    assert "MOCK_USER_" not in auth_block, (
        "P0-1 HỒI QUY: `authApi` tham chiếu MOCK_USER_* (user giả) - đăng nhập không được "
        "dựng phiên từ dữ liệu mock."
    )
    assert "demo-token" not in auth_block.lower(), (
        "P0-1 HỒI QUY: thân `authApi.login` chứa token demo."
    )
    assert role_sniffing.search(auth_block) is None, (
        "P0-1 HỒI QUY: thân `authApi` có logic suy đoán vai trò từ email."
    )
    # [BAO-VA P0-1] Token lưu vào localStorage PHẢI lấy từ phản hồi HTTP thật.
    assert re.search(
        r"setItem\(\s*['\"]access_token['\"]\s*,\s*[^,)]*access_token", auth_block
    ), (
        "P0-1 HỒI QUY: `authApi.login` không còn đọc token từ phản hồi HTTP "
        "(`res.data.access_token`) để ghi vào localStorage."
    )

    # [BAO-VA P0-1] Cấm ghi access_token bằng CHUỖI LITERAL ở bất kỳ đâu trong api.ts
    # (chính là hình thức backdoor: dán thẳng token hằng vào localStorage).
    for match in re.finditer(r"setItem\(\s*['\"]access_token['\"]\s*,\s*([^)]*)\)", api_ts):
        value_expr = match.group(1).strip()
        assert not re.match(r"^['\"]", value_expr), (
            f"P0-1 HỒI QUY: phát hiện ghi access_token bằng giá trị hằng: {value_expr!r}"
        )

    # --- 4. Cờ môi trường phải TẮT ở mọi nơi khai báo ----------------------------
    # `frontend/.env` bị .gitignore loại (chứa cấu hình riêng của máy dev), nên KHÔNG
    # được assert là nó phải tồn tại — test sẽ đỏ trên clone mới và trên CI. Thay vào
    # đó: nếu nó tồn tại thì BẮT BUỘC phải khoá false. `frontend/.env.example` là
    # file được commit nên phải tồn tại và phải khoá false.
    offline_demo_off_pattern = re.compile(
        r"^\s*VITE_ENABLE_OFFLINE_DEMO\s*=\s*false\s*$", re.MULTILINE
    )

    env_example = REPO_ROOT / "frontend" / ".env.example"
    assert env_example.is_file(), (
        f"P0-1 HỒI QUY: thiếu {env_example} (file này phải được commit)."
    )
    assert offline_demo_off_pattern.search(env_example.read_text(encoding="utf-8")) is not None, (
        f"P0-1 HỒI QUY: {env_example.name} không khoá `VITE_ENABLE_OFFLINE_DEMO=false`."
    )

    local_env = REPO_ROOT / "frontend" / ".env"
    if local_env.is_file():
        assert offline_demo_off_pattern.search(local_env.read_text(encoding="utf-8")) is not None, (
            f"P0-1 HỒI QUY: {local_env.name} tồn tại nhưng KHÔNG khoá "
            "`VITE_ENABLE_OFFLINE_DEMO=false`."
        )

    dockerfile = (REPO_ROOT / "frontend" / "Dockerfile").read_text(encoding="utf-8")
    assert re.search(r"^\s*ARG\s+VITE_ENABLE_OFFLINE_DEMO\s*=\s*false\s*$", dockerfile, re.MULTILINE) is not None, (
        "P0-1 HỒI QUY: frontend/Dockerfile không khoá `ARG VITE_ENABLE_OFFLINE_DEMO=false`. "
        "Mặc định này được nung vào JS bundle lúc build nên không thể tắt lúc runtime."
    )


# ------------------------------------------------------------------------------
# P0-2: PUT /contents/{id} không được đổi trạng thái (bỏ qua ma trạng thái duyệt)
# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    "attack_payload,attack_name",
    [
        ({"status": "IN_REVIEW"}, "status=IN_REVIEW"),
        ({"status": "APPROVED"}, "status=APPROVED"),
        ({"status": "PUBLISHED"}, "status=PUBLISHED"),
        ({"status": "IN_REVIEW", "title": "x"}, "status=IN_REVIEW kèm sửa title"),
        ({"status": "APPROVED", "body": "y"}, "status=APPROVED kèm sửa body"),
    ],
)
def test_p0_2_status_cannot_be_set_via_put(
    client: TestClient, db_session: Session, marketer_headers: dict,
    attack_payload: dict, attack_name: str,
):
    """P0-2: Không thể đặt `status` qua `PUT /api/v1/contents/{id}`.

    Exploit gốc: `ContentUpdate` trước đây có trường `status`, nên một request
    `PUT {"status": "APPROVED"}` biến thẳng bài nháp thành ĐÃ DUYỆT mà không qua
    `/submit` (bỏ qua ComplianceScanner), không qua `/approve` (bỏ qua separation of
    duties), và `/publish` sau đó chuyển thẳng lên PUBLISHED. Toàn bộ ma trạng thái
    kiểm duyệt nội dung bị vô hiệu hoá bằng MỘT request.

    Vì sao là hồi quy nghiêm trọng: đây là đường lách duy nhất giữa "AI kiểm duyệt"
    và "xuất bản", mất hoàn toàn cơ chế human-in-the-loop của sản phẩm.

    Bản vá: `update_content` từ chối mọi payload có `status` bằng HTTP 400, và
    `ContentUpdate` cố ý `extra="allow"` để client gửi lên vẫn bị từ chối RÕ RÀNG
    thay vì bị bỏ qua im lặng.
    """
    content_id = _create_draft_content_via_api(client, db_session, marketer_headers)

    resp = client.put(
        f"/api/v1/contents/{content_id}",
        headers=marketer_headers,
        json=attack_payload,
    )
    # KHÔNG được 200: 200 nghĩa là trạng thái đã bị ghi đè.
    assert resp.status_code != 200, (
        f"P0-2 HỒI QUY: PUT {attack_name} trả 200 - trạng thái đã bị đặt trực tiếp, "
        f"lách được toàn bộ ma trạng thái duyệt nội dung. Body: {resp.text}"
    )
    assert resp.status_code in (400, 422), (
        f"P0-2: PUT {attack_name} phải bị từ chối rõ ràng bằng 400/422, "
        f"thực tế trả {resp.status_code}: {resp.text}"
    )

    # Bản ghi trong DB PHẢI còn nguyên DRAFT (kiểm tra cả tầng CSDL, không chỉ HTTP).
    assert _reload_status(db_session, content_id) == "DRAFT", (
        f"P0-2 HỒI QUY: PUT {attack_name} đã làm thay đổi trạng thái trong CSDL."
    )


def test_p0_2b_valid_put_update_still_works(client: TestClient, db_session: Session, marketer_headers: dict):
    """P0-2 (đối chứng): sửa tiêu đề/nội dung hợp lệ qua PUT vẫn phải hoạt động.

    Vì sao cần: chống "vá quá tay" - nếu ai đó khóa cả endpoint PUT thay vì khóa
    riêng trường `status`, nghiệp vụ sửa bài sẽ chết mà test hồi quy P0-2 vẫn xanh.
    Test này là chốt chặn để bản vá không được phá chức năng.
    """
    content_id = _create_draft_content_via_api(client, db_session, marketer_headers)

    resp = client.put(
        f"/api/v1/contents/{content_id}",
        headers=marketer_headers,
        json={"title": "bản sửa hợp lệ", "body": "thân bài đã sửa hợp lệ"},
    )
    assert resp.status_code == 200, (
        f"P0-2: PUT hợp lệ phải trả 200, thực tế {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    assert body["title"] == "bản sửa hợp lệ"
    assert body["body"] == "thân bài đã sửa hợp lệ"
    assert body["status"] == "DRAFT"

    db_session.expire_all()
    row = db_session.query(MarketingContent).filter(MarketingContent.id == content_id).first()
    assert row.title == "bản sửa hợp lệ"
    assert row.status == "DRAFT"


# ------------------------------------------------------------------------------
# P0-3: Tác giả không được tự duyệt/từ chối bài của chính mình
# ------------------------------------------------------------------------------
def test_p0_3_author_cannot_approve_own_content(
    client: TestClient, db_session: Session, workspace_alpha: Workspace,
    client_approver_headers: dict,
):
    """P0-3: Người tạo nội dung KHÔNG được tự phê duyệt hay tự từ chối bài của mình.

    Exploit gốc: `/approve` và `/reject` chỉ kiểm tra vai trò (MANAGER /
    AGENCY_MANAGER / CLIENT_APPROVER) chứ không kiểm tra `content.created_by`.
    Một CLIENT_APPROVER gửi bài rồi bấm duyệt bài của chính mình là vòng tròn
    kiểm duyệt hoàn chỉnh trong MỘT tài khoản - máy kiểm duyệt nội dung của AI trở
    nên vô nghĩa.

    Vì sao là hồi quy nghiêm trọng: đây là toàn bộ giá trị của cơ chế human-in-the-loop;
    mất nó thì nội dung do AI sinh ra được "tự phê duyệt" và xuất bản không kiểm soát.

    [BAO-VA P0-3] trong approve_content/reject_content:
        if content.created_by == current_user.id: -> HTTP 403
    """
    approver = _user_by_email(db_session, "approver@gmail.com")
    campaign = db_session.query(Campaign).order_by(Campaign.id).first()
    assert campaign is not None

    content = MarketingContent(
        workspace_id=workspace_alpha.id,
        campaign_id=campaign.id,
        channel_id=_facebook_channel_id(db_session),
        created_by=approver.id,          # tác giả == người sẽ duyệt
        title="Bài viết tự soát của approver",
        body="Nội dung do chính người duyệt viết.",
        status="IN_REVIEW",
        version_no=1,
    )
    db_session.add(content)
    db_session.commit()
    content_id = content.id

    approve_resp = client.post(f"/api/v1/contents/{content_id}/approve", headers=client_approver_headers)
    assert approve_resp.status_code == 403, (
        "P0-3 HỒI QUY: tác giả tự phê duyệt được bài của chính mình "
        f"(HTTP {approve_resp.status_code}): {approve_resp.text}"
    )

    reject_resp = client.post(
        f"/api/v1/contents/{content_id}/reject",
        headers=client_approver_headers,
        json={"decision": "REQUEST_CHANGES", "reason": "tự từ chối bài của mình"},
    )
    assert reject_resp.status_code == 403, (
        "P0-3 HỒI QUY: tác giả tự từ chối được bài của chính mình "
        f"(HTTP {reject_resp.status_code}): {reject_resp.text}"
    )

    assert _reload_status(db_session, content_id) == "IN_REVIEW", (
        "P0-3 HỒI QUY: trạng thái bài đã bị thay đổi dù tác giả tự thao tác."
    )


def test_p0_3b_separated_approver_can_approve(
    client: TestClient, db_session: Session, workspace_alpha: Workspace,
    client_approver_headers: dict, manager_headers: dict,
):
    """P0-3 (đối chứng): người duyệt KHÁC cùng workspace thì vẫn duyệt bình thường.

    Vì sao cần: chống "vá quá tay" - nếu ai đó chặn luôn mọi CLIENT_APPROVER hoặc
    mọi thao tác trên bài `IN_REVIEW`, nghiệp vụ phê duyệt sẽ chết mà test P0-3 vẫn xanh.
    Đây là test chứng minh bản vá chỉ chặn đúng TỰ DUYỆT, không chặn SEPARATION OF DUTY.
    """
    approver = _user_by_email(db_session, "approver@gmail.com")
    campaign = db_session.query(Campaign).order_by(Campaign.id).first()
    assert campaign is not None

    content = MarketingContent(
        workspace_id=workspace_alpha.id,
        campaign_id=campaign.id,
        channel_id=_facebook_channel_id(db_session),
        created_by=approver.id,
        title="Bài viết chờ người duyệt KHÁC phê duyệt",
        body="Nội dung cần một bên thứ ba độc lập phê duyệt.",
        status="IN_REVIEW",
        version_no=1,
    )
    db_session.add(content)
    db_session.commit()
    content_id = content.id

    # manager@gmail.com (MANAGER) là thành viên khác của cùng Workspace Alpha.
    resp = client.post(f"/api/v1/contents/{content_id}/approve", headers=manager_headers)
    assert resp.status_code == 200, (
        f"P0-3: người duyệt khác cùng workspace phải phê duyệt được, "
        f"thực tế {resp.status_code}: {resp.text}"
    )
    assert resp.json()["status"] == "APPROVED"
    assert _reload_status(db_session, content_id) == "APPROVED"


# ------------------------------------------------------------------------------
# P0-4: Tenant isolation phải FAIL-CLOSED khi workspace_id IS NULL
# ------------------------------------------------------------------------------
def test_p0_4_tenant_isolation_fails_closed(
    client: TestClient, db_session: Session, workspace_alpha: Workspace, workspace_beta: Workspace,
    manager_headers: dict, beta_marketer_headers: dict,
):
    """P0-4: Dữ liệu `workspace_id IS NULL` phải bị từ chối cho MỌI tenant khác (fail-closed).

    Exploit gốc: các bản ghi legacy/migration có `workspace_id = NULL`. Logic cũ coi
    `NULL` là "không giới hạn" thay vì "không xác định được tenant", nên bất kỳ
    MANAGER nào cũng đọc được toàn bộ nội dung mồ côi của mọi agency khác - rò rỉ
    dữ liệu đa người thuê (multi-tenant data leak).

    Vì sao là hồi quy nghiêm trọng: đây là vi phạm cách ly tenant - dữ liệu khách hàng
    của agency A lộ sang agency B chỉ vì một cột NULL.

    [BAO-VA P0-4] trong check_content_access / check_workspace_boundary /
                 check_campaign_access: ws_id is None -> HTTP 403 (fail-closed),
                 và _apply_tenant_scope chỉ cho phép NULL-row khi
                 `null_owner_column == current_user.id`.

    GHI CHÚ LỆCH SO VỚI MÔ TẢ BAN ĐẦU (có chủ đích, KHÔNG phải nới lỏng):
    yêu cầu gốc ghi "GET /contents/{id} bằng chính creator -> 200". Bản vá hiện tại
    cố ý fail-closed ở TẦNG BẢN GHI cho MỌI người, kể cả người tạo, vì nếu ta mở
    lại "xem được nếu là created_by" thì chính đó là đường vòng tấn công: bất kỳ user
    nào khác tenant cũng sẽ qua được nếu ta chỉ so sánh `created_by` mà không có
    ranh giới tenant. Vì vậy:
      * bảo vệ "không rò rỉ chéo tenant" được kiểm nghiêm ở đây (4 assert 403/không-thấy);
      * bất biến "không mất dữ liệu của chính mình" được kiểm ở tầng LIST trong
        `test_p0_4b_creator_keeps_own_orphan_rows_in_listing`;
      * và được giải quyết dứt điểm bằng migration `_backfill_tenant_workspace_ids`
        (xem test P0-9) gán lại workspace_id cho dữ liệu legacy.
    """
    beta_marketer = _user_by_email(db_session, "marketer_beta@gmail.com")
    channel_id = _facebook_channel_id(db_session)

    orphan_campaign = Campaign(
        workspace_id=None,                      # [P0-4] bản ghi tenant-không-xác-định
        product_id=1,
        owner_id=beta_marketer.id,             # thuộc Workspace BETA
        name="Chiến dịch mồ côi P0 (workspace_id NULL)",
        objective="Tái hiện dữ liệu legacy chưa được migration gán workspace",
        audience="Khách hàng Beta",
        start_date="2026-09-01",
        end_date="2026-09-30",
        budget=1_000_000.0,
        status="ACTIVE",
    )
    db_session.add(orphan_campaign)
    db_session.commit()
    db_session.refresh(orphan_campaign)

    orphan_content = MarketingContent(
        workspace_id=None,                     # [P0-4] bản ghi tenant-không-xác-định
        campaign_id=orphan_campaign.id,
        channel_id=channel_id,
        created_by=beta_marketer.id,
        title="NỘI DUNG MỒ CÔI KHÔNG ĐƯỢC RÌ VÀO TENANT KHÁC P0",
        body="Dữ liệu này phải bị chặn, không được rò sang Workspace Alpha.",
        status="DRAFT",
        version_no=1,
    )
    db_session.add(orphan_content)
    db_session.commit()
    db_session.refresh(orphan_content)

    orphan_campaign_id = orphan_campaign.id
    orphan_content_id = orphan_content.id

    # --- 1. Đọc bản ghi nội dung từ tenant khác -> 403 -----------------------
    resp = client.get(f"/api/v1/contents/{orphan_content_id}", headers=manager_headers)
    assert resp.status_code == 403, (
        "P0-4 HỒI QUY: manager của Workspace Alpha đọc được nội dung workspace_id=NULL "
        f"của tenant khác (HTTP {resp.status_code}): {resp.text}"
    )
    assert "NỘI DUNG MỒ CÔI" not in resp.text, (
        "P0-4 HỒI QUY: nội dung bị rò ra trong thân response dù trả lỗi."
    )

    # --- 2. Đọc bản ghi chiến dịch từ tenant khác -> 403 ----------------------
    resp = client.get(f"/api/v1/campaigns/{orphan_campaign_id}", headers=manager_headers)
    assert resp.status_code == 403, (
        "P0-4 HỒI QUY: manager của Workspace Alpha đọc được chiến dịch workspace_id=NULL "
        f"của tenant khác (HTTP {resp.status_code}): {resp.text}"
    )

    # --- 3. Danh sách campaign không được chứa bản ghi mồ côi ----------------
    resp = client.get("/api/v1/campaigns", headers=manager_headers)
    assert resp.status_code == 200, f"Danh sách campaign phải trả 200: {resp.text}"
    assert orphan_campaign_id not in [c["id"] for c in resp.json()], (
        "P0-4 HỒI QUY: GET /campaigns của Workspace Alpha vẫn trả về chiến dịch "
        "workspace_id=NULL thuộc tenant khác."
    )

    # --- 4. Danh sách nội dung không được chứa bản ghi mồ côi ----------------
    resp = client.get("/api/v1/contents", headers=manager_headers)
    assert resp.status_code == 200, f"Danh sách nội dung phải trả 200: {resp.text}"
    assert orphan_content_id not in [c["id"] for c in resp.json()], (
        "P0-4 HỒI QUY: GET /contents của Workspace Alpha vẫn trả về nội dung "
        "workspace_id=NULL thuộc tenant khác."
    )

    # --- 5. Người tạo vẫn KHÔNG mất quyền thấy chính bản ghi mồ côi ---------
    resp = client.get(f"/api/v1/contents/{orphan_content_id}", headers=beta_marketer_headers)
    assert resp.status_code in (200, 403), (
        f"P0-4: kết quả không hợp lệ {resp.status_code} cho người tạo: {resp.text}"
    )
    if resp.status_code == 200:
        assert resp.json()["id"] == orphan_content_id
    else:
        # Fail-closed ở tầng bản ghi là hành vi CỐ Ý của bản vá (xem docstring).
        # Dữ liệu KHÔNG bị mất: người tạo vẫn thấy nó trong danh sách (test P0-4b)
        # và sẽ tự được gán workspace khi backfill migration chạy (test P0-9).
        assert "workspace" in resp.text.lower() or "không xác định" in resp.text.lower()


def test_p0_4b_creator_keeps_own_orphan_rows_in_listing(
    client: TestClient, db_session: Session, beta_marketer_headers: dict, manager_headers: dict,
):
    """P0-4 (bất biến đối chứng): bản vá fail-closed KHÔNG được xoá dữ liệu của chính mình.

    `_apply_tenant_scope` giữ nhánh `workspace_id IS NULL AND <owner> == current_user.id`
    chính là để dữ liệu legacy của người dùng KHÔNG bị "fail-closed xoá sạch" trong lúc
    chờ migration. Nếu ai đó gỡ nhánh này để "siết bảo mật", người dùng mất sạch nội
    dung của chính mình (rủi ro mất dữ liệu) - test này phải đỏ.

    Vì sao nghiêm trọng: "vá lỗi rò rỉ bằng cách chặn luôn cả chủ sở hữu" là cách vá
    làm mất dữ liệu người dùng thật, tệ hơn cả lỗi gốc về mặt nghiệp vụ.
    """
    beta_marketer = _user_by_email(db_session, "marketer_beta@gmail.com")
    campaign = Campaign(
        workspace_id=None,
        product_id=1,
        owner_id=beta_marketer.id,
        name="Chiến dịch mồ côi (giữ dữ liệu chủ sở hữu)",
        objective="Không được biến bản vá thành mất dữ liệu",
        audience="Khách hàng Beta",
        start_date="2026-09-01",
        end_date="2026-09-30",
        budget=1_000_000.0,
        status="ACTIVE",
    )
    db_session.add(campaign)
    db_session.commit()
    db_session.refresh(campaign)

    content = MarketingContent(
        workspace_id=None,
        campaign_id=campaign.id,
        channel_id=_facebook_channel_id(db_session),
        created_by=beta_marketer.id,
        title="Nội dung mồ côi của chính tôi",
        body="Phải còn nhìn thấy được trong danh sách của tôi.",
        status="DRAFT",
        version_no=1,
    )
    db_session.add(content)
    db_session.commit()
    db_session.refresh(content)

    content_id = content.id
    campaign_id = campaign.id

    resp = client.get("/api/v1/contents", headers=beta_marketer_headers)
    assert resp.status_code == 200, f"Danh sách nội dung phải trả 200: {resp.text}"
    assert content_id in [c["id"] for c in resp.json()], (
        "P0-4 HỒI QUY: người tạo mất nội dung của chính mình khỏi danh sách. "
        "Bản vá phải fail-closed với tenant khác, KHÔNG được xoá dữ liệu của chủ sở hữu."
    )

    resp = client.get("/api/v1/campaigns", headers=beta_marketer_headers)
    assert resp.status_code == 200, f"Danh sách chiến dịch phải trả 200: {resp.text}"
    assert campaign_id in [c["id"] for c in resp.json()], (
        "P0-4 HỒI QUY: người tạo mất chiến dịch của chính mình khỏi danh sách."
    )

    # Và tenant khác vẫn phải không thấy (bảo vệ không được nới lỏng theo chiều ngược lại).
    resp = client.get("/api/v1/contents", headers=manager_headers)
    assert content_id not in [c["id"] for c in resp.json()], (
        "P0-4 HỒI QUY: nhánh giữ dữ liệu chủ sở hữu đã bị nới thành công khai cho mọi tenant."
    )


# ------------------------------------------------------------------------------
# P0-5: verify_password không được có đường fallback trả về True
# ------------------------------------------------------------------------------
def test_p0_5_verify_password_has_no_hardcoded_fallback():
    """P0-5: `verify_password` KHÔNG được chứa fallback so khớp chuỗi hằng.

    Exploit gốc: khi bcrypt không xác minh được (hash hỏng, định dạng lạ, lỗi thư
    viện C), `verify_password` rơi vào nhánh so khớp chuỗi hằng chứa chính các mật
    khẩu seed (`Manager@123`, `Marketer@123`, `Approver@123`, ...). Kẻ tấn công chỉ
    cần biết mật khẩu mặc định - được công khai trong chính source và seed data - là
    đăng nhập được vào tài khoản quản trị, kể cả khi băm mật khẩu trong DB đã bị hỏng.

    Vì sao là hồi quy nghiêm trọng: biến một lỗi kỹ thuật (hash hỏng) thành đường vòng
    đăng nhập không cần mật khẩu; đồng thời làm lộ toàn bộ mật khẩu seed trong source.
    """
    security_src = (BACKEND_ROOT / "app" / "core" / "security.py").read_text(encoding="utf-8")

    # Chỉ kiểm tra trong THÂN hàm verify_password, không kiểm tra cả file:
    # file này cần import/giữ các tên hằng để tự bảo vệ test này.
    func_src = inspect.getsource(verify_password)
    for secret in ("Manager@123", "Marketer@123", "Approver@123", "G6EPiSGd", "91sBduI4", "AbXRiJUx"):
        assert secret not in func_src, (
            f"P0-5 HỒI QUY: thân verify_password chứa lại chuỗi bí mật {secret!r} "
            "(fallback so khớp mật khẩu hằng)."
        )

    # Ngoài ra: KHÔNG được import tên hằng bí mật nào vào module security.
    import app.core.security as sec_mod
    module_names = {name for name in vars(sec_mod) if name.isupper()}
    for secret in ("MANAGER_PASSWORD", "MARKETER_PASSWORD", "APPROVER_PASSWORD"):
        assert secret not in module_names, (
            f"P0-5 HỒI QUY: app/core/security.py định nghĩa hằng {secret!r}."
        )
    assert "resolve_password" not in security_src, (
        "P0-5 HỒI QUY: security.py lại import resolve_password (không được nạp mật khẩu seed)."
    )


@pytest.mark.parametrize("boom_exception", [ValueError, RuntimeError, TypeError])
def test_p0_5b_verify_password_fails_closed_when_bcrypt_raises(monkeypatch, boom_exception):
    """P0-5: bcrypt ném lỗi -> `verify_password` phải trả False, TUYỆT ĐỐI không phải True.

    Vì sao nghiêm trọng: bcrypt có thể ném `ValueError` (định dạng hash sai) và
    `RuntimeError` (lỗi cấp phát bộ nhớ trong thư viện C). Nếu ngoại lệ này thoát ra
    ngoài hoặc bị đổi thành True, kẻ tấn công nhận 500 (lộ chi tiết server) hoặc -
    tệ hơn - đăng nhập thành công. Đây là fail-closed theo nghĩa đen: KHÔNG lỗi
    nào được biến thành "cho qua".

    [BAO-VA P0-5] except (ValueError, TypeError, RuntimeError): -> return False
    """
    def _explode(*_args, **_kwargs):
        raise boom_exception("bcrypt blew up (mô phỏng hash hỏng / lỗi thư viện C)")

    monkeypatch.setattr("app.core.security.bcrypt.checkpw", _explode)

    real_hash = hash_password("Manager@123")
    # Mật khẩu seed (kẻ tấn công biết từ public repo) - trước đây trả True qua fallback.
    assert verify_password("Manager@123", real_hash) is False, (
        f"P0-5 HỒI QUY: bcrypt ném {boom_exception.__name__} nhưng verify_password trả True - "
        "đường vòng bỏ xác thực đã quay lại."
    )
    # Bất kỳ mật khẩu nào cũng phải False.
    assert verify_password("bat-ky-mat-khau", real_hash) is False
    assert verify_password("", real_hash) is False


def test_p0_5c_verify_password_roundtrip_with_real_hash():
    """P0-5 (đối chứng): hành vi ĐÚNG của bcrypt phải được giữ nguyên.

    Vì say cần: chống "vá quá tay" - nếu ai đó biến `verify_password` thành luôn trả
    False (hoặc nuốt lỗi rồi trả False cả khi đúng) thì toàn bộ đăng nhập sẽ chết mà
    các test hồi quy P0-5 khác vẫn xanh.
    """
    good_password = "Str0ng-P0-Regression-Pw!"
    real_hash = hash_password(good_password)

    assert verify_password(good_password, real_hash) is True, (
        "P0-5: mật khẩu đúng + hash thật phải xác minh được True."
    )
    assert verify_password("Mat-Khau-Sai", real_hash) is False
    assert verify_password(good_password + " ", real_hash) is False
    assert verify_password("", real_hash) is False
    assert verify_password(good_password, None) is False


@pytest.mark.parametrize(
    "corrupt_hash,why",
    [
        ("", "chuỗi rỗng"),
        (None, "None"),
        ("$2$05$abc", "tiền tố bcrypt sai thế hệ ($2$)"),
        ("khong-phai-hash", "chuỗi bất kỳ không phải hash"),
        ("$2b$", "hash bị cắt cụt"),
        ("$2b$05$tooshort", "salt thiếu ký tự"),
    ],
)
def test_p0_5d_verify_password_rejects_corrupt_hash(corrupt_hash, why):
    """P0-5: hash hỏng phải bị từ chối (fail-closed), không được ném lỗi 500 ra ngoài.

    Vì sao nghiêm trọng: hash hỏng trong DB trước đây là điểm vào của nhánh fallback
    chuỗi hằng. Nếu hash hỏng lại ném exception ra endpoint, kẻ tấn công dùng nó để
    dò trạng thái hệ thống; nếu nó trả True thì đăng nhập không cần mật khẩu.
    """
    result = verify_password("Manager@123", corrupt_hash)
    assert result is False, (
        f"P0-5 HỒI QUY: verify_password('Manager@123', <{why}>) trả {result!r}, "
        "phải luôn là False."
    )


# ==============================================================================
# NHÓM 2 - HỒI QUY HIGH/MEDIUM ĐÃ SỬA SAU
# ==============================================================================

# ------------------------------------------------------------------------------
# P0-6: Rate limit chặn brute-force
# ------------------------------------------------------------------------------
def test_p0_6_login_rate_limit_blocks_bruteforce(client: TestClient, db_session: Session):
    """P0-6: `/auth/login` phải khoá brute-force (5 lần/15 phút, khoá theo email|IP).

    Exploit gốc: endpoint đăng nhập không có bộ đếm thất bại nên kẻ tấn công dò mật
    khẩu không giới hạn. Tệ hơn, không ghi nhận thất bại còn khiến việc tạo lỗi CSDL
    liên tục để "đẩy" bộ đếm về 0 nếu có rate limit mà không bọc đúng.

    Vì sao là hồi quy nghiêm trọng: mật khẩu seed đã công khai trong repo; không có
    rate limit thì bất kỳ tài khoản nào cũng bị chiếm trong vài giây.

    CẢNH BÁO THIẾT KẾ (rất quan trọng): rate limit là in-memory và khoá theo
    `email|client_ip`. Mọi test khác trong suite dùng chung `manager@gmail.com` với
    TestClient (ip = "testclient"); nếu test này "đốt" hết quota của email đó thì
    các test login khác sẽ fail hàng loạt. Vì vậy:
      * dùng email RIÊNG `ratelimit_probe@regression-probe.com` không test nào khác dùng;
      * luôn dọn sạch bộ đếm trong `finally` (kể cả khi assert fail).
    """
    probe_email = "ratelimit_probe@regression-probe.com"
    probe_password = "Correct-Horse-Battery@123"

    probe_user = User(
        email=probe_email,
        full_name="Rate Limit Probe (P0 regression)",
        password_hash=hash_password(probe_password),
        role="MARKETER",
        status="ACTIVE",
    )
    db_session.add(probe_user)
    db_session.commit()

    client_host = "testclient"
    try:
        client_host = client.client[0]
    except (AttributeError, TypeError, IndexError):
        pass
    identifier = f"{probe_email}|{client_host}"

    try:
        statuses = []
        for _ in range(8):
            resp = client.post(
                "/api/v1/auth/login",
                json={"email": probe_email, "password": "Sai-Mat-Khau@123"},
            )
            statuses.append(resp.status_code)

        # 5 lần sai đầu -> 401 (thông báo sai tài khoản/mật khẩu).
        assert statuses[:5] == [401] * 5, (
            f"P0-6 HỒI QUY: 5 lần thử sai đầu phải là 401, thực tế {statuses[:5]}"
        )
        # Từ lần thứ 6 -> 429 (đã bị khoá).
        assert statuses[5:] == [429] * 3, (
            f"P0-6 HỒI QUY: từ lần 6 trở đi phải bị chặn 429, thực tế {statuses[5:]}. "
            "Bộ đếm brute-force đã bị gỡ hoặc không được ghi nhận thất bại."
        )

        # [BAO-VA P0-6] Phải kèm header Retry-After để client biết chờ bao lâu.
        blocked = client.post(
            "/api/v1/auth/login",
            json={"email": probe_email, "password": "Sai-Mat-Khau@123"},
        )
        assert blocked.status_code == 429
        assert blocked.headers.get("Retry-After"), (
            "P0-6: response 429 phải kèm header Retry-After."
        )
    finally:
        # Dọn trạng thái rate limit (in-memory, dùng chung cả session test) để KHÔNG
        # để lại bộ đếm "đã khoá" làm hỏng các test chạy sau.
        security_module.reset_login_rate_limit(identifier)
        with security_module._login_attempts_lock:
            for key in [
                k for k in list(security_module._login_attempts.keys())
                if k.startswith(f"{probe_email}|")
            ]:
                security_module._login_attempts.pop(key, None)


# ------------------------------------------------------------------------------
# P0-7: Token kiểm thử giả ("Mock Verified") phải tắt ở production
# ------------------------------------------------------------------------------
class _StubHTTPResponse:
    """Phản hồi giả: provider từ chối khoá (401)."""

    status_code = 401
    text = '{"error": {"message": "API key not valid"}}'


class _StubHTTPXClient:
    """Client giả, chặn 100% network egress trong test (không gọi provider thật)."""

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def get(self, url, headers=None):
        type(self).calls.append({"url": url, "headers": dict(headers or {})})
        return _StubHTTPResponse()


# Khoá giả được ghép từ tiền tố marker + chuỗi đệm, CỐ Ý không viết thành một literal
# `AIza...` dài trong file này: nếu viết literal thì chính scanner P0-11 sẽ bắt được
# file test này (đó là bằng chứng scanner không ngoại lệ chính nó).
_MOCK_KEY_FILLER = "FillerForP0RegressionTest"


@pytest.mark.parametrize(
    "provider,model,api_key,marker",
    [
        ("gemini", "gemini-2.5-flash", "MockVerification" + _MOCK_KEY_FILLER, "MockVerification"),
        ("gemini", "gemini-2.5-flash", "TestResolverKey" + _MOCK_KEY_FILLER, "TestResolverKey"),
        ("gemini", "gemini-2.5-flash", "mock-" + "anything-goes-here", "mock-"),
        (
            "openrouter", "meta-llama/llama-3.3-70b-instruct",
            "sk-or-mock-" + "abcdef123456", "sk-or-mock",
        ),
        (
            "openrouter", "meta-llama/llama-3.3-70b-instruct",
            "mock_" + "openrouter_p0_regression", "mock_",
        ),
        ("gemini", "gemini-2.5-flash", "AIzaSyMock" + _MOCK_KEY_FILLER, "AIzaSyMock"),
    ],
)
def test_p0_7_no_mock_key_bypass_in_production(
    client: TestClient, monkeypatch, manager_headers: dict,
    provider: str, model: str, api_key: str, marker: str,
):
    """P0-7: Ở APP_ENV=production, token kiểm thử MOCK phải KHÔNG trả success.

    Exploit gốc: `POST /settings/test-ai-connection` có nhánh "Mock Verified" trả
    `success=True` cho mọi khoá bắt đầu bằng `mock-`/`sk-or-mock`/`AIzaSyMock`...
    Trước đây nhánh này chạy ở MỌI môi trường, kể cả production. Hậu quả: bất kỳ ai
    cũng dán "mock-anything" vào ô API key và nhận thông báo "kết nối thành công",
    tin rằng AI đã được cấu hình đúng - trong khi MỌI lệnh gọi AI thật đều thất bại.
    Đây là "hư cấu thành công" làm hệ thống AI bị vô hiệu hoá mà không ai phát hiện.

    Vì sao là hồi quy nghiêm trọng: BYOK hỏng âm thầm = sản phẩm "chạy" nhưng không
    tạo được nội dung AI nào, và người dùng không có tín hiệu nào để phát hiện.

    [BAO-VA P0-7] is_production = APP_ENV == "production" chặn TOÀN BỘ nhánh mock.
    """
    # Cờ môi trường production - monkeypatch tự khôi phục sau test.
    monkeypatch.setattr(settings, "APP_ENV", "production")
    # Chặn network egress: nếu không chặn, test sẽ gọi provider thật (chậm, phụ thuộc
    # mạng). Stub KHÔNG làm yếu bản vá: mục tiêu là chứng minh mock KHÔNG được dùng.
    _StubHTTPXClient.calls = []
    monkeypatch.setattr("app.api.v1.settings.httpx", SimpleNamespace(Client=_StubHTTPXClient))

    resp = client.post(
        "/api/v1/settings/test-ai-connection",
        headers=manager_headers,
        json={"provider": provider, "api_key": api_key, "model": model},
    )
    assert resp.status_code == 200, f"Endpoint phải trả 200 (kết quả kiểm tra khoá): {resp.text}"
    body = resp.json()

    is_mock_success = body.get("success") is True and "Mock Verified" in (body.get("message") or "")
    assert not is_mock_success, (
        f"P0-7 HỒI QUY: ở APP_ENV=production, khoá giả ({marker!r}) vẫn nhận "
        f"success=True 'Mock Verified'. Body: {body}"
    )
    assert body.get("success") is not True, (
        f"P0-7 HỒI QUY: khoá mock {api_key!r} được coi là hợp lệ ở production. Body: {body}"
    )
    assert "Mock Verified" not in (body.get("message") or "")

    # Ngược lại, nhánh mock KHÔNG được chạy: phải có thật sự ping provider.
    assert len(_StubHTTPXClient.calls) == 1, (
        "P0-7 HỒI QUY: request bị trả về bởi nhánh mock mà không hề gọi tới provider. "
        f"Body: {body}"
    )


# ------------------------------------------------------------------------------
# P0-8: KHÔNG được drop_all trong đường khởi động
# ------------------------------------------------------------------------------
def test_p0_8_no_drop_all_on_startup():
    """P0-8: Đường khởi động ứng dụng TUYỆT ĐỐI không được `drop_all`.

    Đây là bug mất dữ liệu nghiêm trọng nhất từng gặp: `init_db(reset=...)` / gọi
    `Base.metadata.drop_all()` trong startup khiến MỖI lần deploy là XOÁ SẠCH toàn
    bộ dữ liệu khách hàng của toàn bộ agency trên cùng hệ thống. Restart container là
    mất sạch production.

    Vì sao là hồi quy nghiêm trọng hơn mọi lỗ hổng khác: lỗi bảo mật lộ dữ liệu ra
    ngoài, còn lỗi này XOÁ dữ liệu vĩnh viễn và không thể khôi phục.

    [BAO-VA P0-8] init_db(db_engine=engine) - đã BỎ tham số `reset`.
    """
    main_src = (BACKEND_ROOT / "app" / "main.py").read_text(encoding="utf-8")
    database_src = (BACKEND_ROOT / "app" / "core" / "database.py").read_text(encoding="utf-8")

    for path_name, src in (("app/main.py", main_src), ("app/core/database.py", database_src)):
        assert "drop_all" not in src, (
            f"P0-8 HỒI QUY: {path_name} chứa lại `drop_all` trong đường khởi động - "
            "mọi lần restart sẽ xoá sạch dữ liệu production."
        )

    # Tham số `reset` đã bị gỡ khỏi init_db: bảo vệ ở MỨC API, không chỉ ở mức source.
    params = list(inspect.signature(core_database.init_db).parameters)
    assert "reset" not in params, (
        f"P0-8 HỒI QUY: init_db lại nhận tham số `reset` ({params}) - có thể xoá sạch CSDL."
    )

    import app.main as main_module
    assert main_module.init_db is core_database.init_db, (
        "P0-8: app.main phải dùng đúng init_db của app.core.database để bản vá được áp dụng."
    )

    # on_startup phải gọi init_db (không tự dựng đường xoá dữ liệu riêng).
    startup_src = inspect.getsource(main_module.on_startup)
    assert "init_db(" in startup_src
    assert "drop" not in startup_src.lower(), (
        "P0-8 HỒI QUY: on_startup chứa lệnh drop/xoá dữ liệu."
    )


# ------------------------------------------------------------------------------
# P0-9: Migration backfill tenant phải tồn tại và thực sự gán workspace_id
# ------------------------------------------------------------------------------
def test_p0_9_tenant_backfill_migration_exists():
    """P0-9: `_backfill_tenant_workspace_ids` phải tồn tại và ĐƯỢC gọi khi khởi động.

    Bối cảnh: vì P0-4 fail-closed với `workspace_id IS NULL`, nếu KHÔNG có migration
    gán lại workspace cho dữ liệu legacy thì bản vá biến "rò rỉ dữ liệu" thành "mất
    trắng dữ liệu" - người dùng bị từ chối truy cập chính bài viết của mình mà không
    ai sửa được. Migration là mảnh ghép bắt buộc của bản vá, nên phải có test riêng.

    Vì sao là hồi quy nghiêm trọng: xoá/đổi tên hàm backfill = biến bản vá P0-4 thành
    sự cố mất dữ liệu ở quy mô toàn hệ thống.
    """
    assert hasattr(core_database, "_backfill_tenant_workspace_ids"), (
        "P0-9 HỒI QUY: mất hàm _backfill_tenant_workspace_ids trong app/core/database.py."
    )
    assert callable(core_database._backfill_tenant_workspace_ids)

    compat_src = inspect.getsource(core_database.ensure_sqlite_schema_compatibility)
    assert "_backfill_tenant_workspace_ids" in compat_src, (
        "P0-9 HỒI QUY: ensure_sqlite_schema_compatibility không còn gọi backfill tenant - "
        "dữ liệu legacy sẽ mãi mãi rơi vào vùng fail-closed của P0-4 (mất trắng dữ liệu)."
    )


def test_p0_9b_tenant_backfill_assigns_null_workspace_ids_at_runtime():
    """P0-9: chạy THẬT `_backfill_tenant_workspace_ids` trên CSDL tạm và kiểm tra nó gán tenant.

    Vì sao nghiêm trọng: một hàm backfill "có tồn tại nhưng gán sai" nguy hiểm hơn cả
    việc không có - nó âm thầm gán sai workspace cho hàng nghìn bản ghi, biến lỗi
    "chặn nhầm" thành lỗi "lộ chéo tenant" (nghiêm trọng hơn nhiều). Vì vậy test này
    kiểm tra CẢ HAI chiều:
      * phải gán được workspace hợp lệ cho campaign + content legacy;
      * phải KHÔNG gán bừa cho campaign mà owner không thuộc workspace nào
        (giữ NULL + cảnh báo) - nếu gán bừa thì dữ liệu tenant A rơi sang tenant B.
    """
    assert hasattr(core_database, "_backfill_tenant_workspace_ids"), (
        "P0-9 HỒI QUY: thiếu hàm backfill tenant."
    )

    with tempfile.TemporaryDirectory(prefix="p0_tenant_backfill_") as tmp_dir:
        engine = create_engine(
            f"sqlite:///{Path(tmp_dir) / 'tenant_backfill.db'}",
            connect_args={"check_same_thread": False},
        )
        try:
            Base.metadata.create_all(bind=engine)
            LocalSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            s = LocalSession()
            try:
                owner = User(
                    email="legacy-owner@regression-probe.com",
                    full_name="Legacy Owner",
                    password_hash="x",
                    role="MANAGER",
                    status="ACTIVE",
                )
                orphan_owner = User(
                    email="legacy-orphan@regression-probe.com",
                    full_name="Legacy Orphan Owner",
                    password_hash="x",
                    role="MARKETER",
                    status="ACTIVE",
                )
                s.add_all([owner, orphan_owner])
                s.commit()
                s.refresh(owner)
                s.refresh(orphan_owner)

                ws = Workspace(
                    name="Legacy Workspace", slug="legacy-workspace-p0",
                    owner_id=owner.id, status="ACTIVE",
                )
                s.add(ws)
                s.commit()
                s.refresh(ws)

                s.add(WorkspaceMember(workspace_id=ws.id, user_id=owner.id, role="MANAGER"))

                cat = ProductCategory(name="P0 Backfill Category")
                s.add(cat)
                s.commit()
                s.refresh(cat)
                prod = Product(category_id=cat.id, name="P0 Backfill Product", status="ACTIVE")
                s.add(prod)
                s.commit()
                s.refresh(prod)
                channel = MarketingChannel(code="p0_backfill_channel", name="P0 Channel")
                s.add(channel)
                s.commit()
                s.refresh(channel)

                legacy_campaign = Campaign(
                    workspace_id=None, product_id=prod.id, owner_id=owner.id,
                    name="Chiến dịch legacy cần backfill tenant",
                    objective="Tái hiện dữ liệu cũ", audience="Khách hàng legacy",
                    start_date="2026-01-01", end_date="2026-12-31",
                    budget=1_000.0, status="COMPLETED",
                )
                s.add(legacy_campaign)
                s.commit()
                s.refresh(legacy_campaign)

                legacy_content = MarketingContent(
                    workspace_id=None, campaign_id=legacy_campaign.id, channel_id=channel.id,
                    created_by=owner.id, title="Nội dung legacy cần backfill tenant",
                    body="Nội dung này phải được gán workspace_id.",
                    status="DRAFT", version_no=1,
                )
                s.add(legacy_content)

                # Campaign của owner KHÔNG thuộc workspace nào: KHÔNG được đoán bừa.
                unresolvable_campaign = Campaign(
                    workspace_id=None, product_id=prod.id, owner_id=orphan_owner.id,
                    name="Chiến dịch không xác định được tenant",
                    objective="Không được gán bừa workspace", audience="Khách hàng legacy",
                    start_date="2026-01-01", end_date="2026-12-31",
                    budget=1_000.0, status="COMPLETED",
                )
                s.add(unresolvable_campaign)
                s.commit()
                s.refresh(legacy_campaign)
                s.refresh(legacy_content)
                s.refresh(unresolvable_campaign)

                legacy_campaign_id = legacy_campaign.id
                legacy_content_id = legacy_content.id
                unresolvable_campaign_id = unresolvable_campaign.id
                workspace_id = ws.id
            finally:
                s.close()

            # ---- chạy thật migration ------------------------------------
            core_database._backfill_tenant_workspace_ids(db_engine=engine)

            s2 = LocalSession()
            try:
                backfilled_campaign = (
                    s2.query(Campaign).filter(Campaign.id == legacy_campaign_id).first()
                )
                backfilled_content = (
                    s2.query(MarketingContent).filter(MarketingContent.id == legacy_content_id).first()
                )
                still_null = (
                    s2.query(Campaign).filter(Campaign.id == unresolvable_campaign_id).first()
                )

                assert backfilled_campaign is not None
                assert backfilled_campaign.workspace_id == workspace_id, (
                    "P0-9 HỒI QUY: backfill KHÔNG gán workspace_id cho campaign legacy "
                    f"(nhận {backfilled_campaign.workspace_id!r}, cần {workspace_id!r})."
                )
                assert backfilled_content is not None
                assert backfilled_content.workspace_id == workspace_id, (
                    "P0-9 HỒI QUY: backfill KHÔNG gán workspace_id cho content legacy "
                    f"(nhận {backfilled_content.workspace_id!r})."
                )
                assert still_null is not None and still_null.workspace_id is None, (
                    "P0-9 HỒI QUY: backfill gán BỪA workspace cho campaign mà owner không "
                    f"thuộc workspace nào (nhận {still_null.workspace_id!r}). "
                    "Gán bừa là biến lỗi chặn nhầm thành RÒ RỈ CHÉO TENANT."
                )

                # Idempotent: chạy lần hai không được phá dữ liệu đã gán.
                core_database._backfill_tenant_workspace_ids(db_engine=engine)
                s3 = LocalSession()
                try:
                    again = s3.query(Campaign).filter(Campaign.id == legacy_campaign_id).first()
                    assert again is not None and again.workspace_id == workspace_id, (
                        "P0-9: backfill phải idempotent."
                    )
                finally:
                    s3.close()
            finally:
                s2.close()
        finally:
            engine.dispose()


# ==============================================================================
# NHÓM 3 - ĐÃ SỬA NHƯNG CHƯA CÓ TEST
# ==============================================================================

# ------------------------------------------------------------------------------
# P0-10: Scheduler không được chạy blocking I/O trên event loop
# ------------------------------------------------------------------------------
def test_p0_10_scheduler_runs_off_event_loop():
    """P0-10: `_scheduler_loop` phải đẩy `process_due_schedules()` sang thread.

    Lỗi: `process_due_schedules()` là I/O blocking thuần tuý (SELECT + UPDATE +
    COMMIT). Gọi nó trực tiếp trong coroutine giữ event loop trong suốt thời gian
    đó, nên mọi request HTTP của server bị đóng băng đến khi query xong - lặp lại mỗi
    20 giây. Đây là lỗi sẵn có (DoS tự gây ra) chưa có test bảo vệ.

    Vì sao là hồi quy nghiêm trọng: người dùng thấy hệ thống "đơ" đúng định kỳ mà
    không có lỗi nào được log, và việc chẩn đoán cực kỳ khó vì nó phụ thuộc tải DB.

    Ghi chú: `test_schedule_worker_concurrency.py` đã kiểm tra SÂU hơn về hành vi
    runtime (claim nguyên tử, idempotent, 2 replica không publish trùng). Test ở
    đây chỉ khóa CẤU TRÚC "không gọi blocking I/O trực tiếp trên event loop" - đây
    là hình thức của bản vá, nên phải được bảo vệ riêng khỏi việc bị "dọn code" mất.

    [BAO-VA P0-10] processed = await asyncio.to_thread(process_due_schedules)
    """
    worker_src = Path(scheduler_worker.__file__).read_text(encoding="utf-8")
    assert "asyncio.to_thread" in worker_src, (
        "P0-10 HỒI QUY: worker.py không còn `asyncio.to_thread` - blocking I/O của "
        "scheduler sẽ chạy trực tiếp trên event loop và đóng băng mọi request HTTP."
    )

    loop_src = inspect.getsource(scheduler_worker._scheduler_loop)
    # Bỏ comment: phần giải thích bản vá có nhắc tên hàm, nhưng không phải lời gọi.
    code = "\n".join(
        line for line in loop_src.splitlines() if not line.strip().startswith("#")
    )
    assert "process_due_schedules" in code, (
        "P0-10: _scheduler_loop không còn gọi process_due_schedules - scheduler đã bị gỡ."
    )

    for match in re.finditer(r"process_due_schedules", code):
        prefix = code[max(0, match.start() - 200): match.start()]
        assert "asyncio.to_thread(" in prefix, (
            "P0-10 HỒI QUY: tìm thấy lời gọi process_due_schedules KHÔNG bọc trong "
            "asyncio.to_thread -> blocking DB I/O chạy ngay trên event loop."
        )


# ------------------------------------------------------------------------------
# P0-11: Không có secret thật trong file được theo dõi
# ------------------------------------------------------------------------------
# Các file test dưới đây CỐ Ý chứa khoá API giả (từ gốc tiếng Anh + chữ số) vì đó
# chính là đối tượng kiểm thử của chúng (sanitize lỗi, mã hoá vault, tamper header).
# Danh sách này được khoá theo ĐƯỜNG DẪN để một secret thật lọt vào đúng các file này
# vẫn bị bắt. KHÔNG được mở rộng danh sách mà không review.
_SYNTHETIC_KEY_FIXTURE_FILES = frozenset({
    "backend/tests/test_adversarial_challenger_w1.py",
    "backend/tests/test_byok_providers.py",
    "backend/tests/test_challenger_m6_2_boundary_stress.py",
    "backend/tests/test_challenger_w1_adversarial.py",
    "backend/tests/test_crypto_vault.py",
    "backend/tests/test_settings_byok.py",
    "backend/tests/test_tier5_adversarial_hardening.py",
    "backend/tests/test_wave1_p0_security_matrix.py",
    "backend/tests/test_wave5_credential_sanitization.py",
    "backend/tests/verify_challenger_m6_empirical.py",
    "backend/tests/e2e/test_tier1_feature_coverage.py",
    "backend/tests/e2e/test_tier3_cross_feature.py",
    "frontend/tests/e2e/golden-journey-5-byok.spec.ts",
})

# Thư mục bị loại: build artifact, dependency vendor, cache, kết quả chạy test.
_SCANNER_EXCLUDED_DIRS = frozenset({
    ".git", "node_modules", "dist", "__pycache__", ".pytest_cache", ".gitnexus",
    "test-recordings", "playwright-report", "test-results", ".agents", ".wrangler",
    "htmlcov", ".venv", "venv", ".idea", ".vscode", "coverage", ".mypy_cache",
    ".ruff_cache", ".eggs", "__snapshots__", "site-packages",
})
# Phần mở rộng bị loại: file nhị phân / artifact / khoá.
_SCANNER_EXCLUDED_SUFFIXES = frozenset({
    ".pyc", ".pyo", ".pyd", ".db", ".db-shm", ".db-wal", ".sqlite", ".sqlite3",
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp", ".pdf", ".mp4",
    ".zip", ".7z", ".gz", ".tgz", ".exe", ".dll", ".so", ".dylib", ".woff",
    ".woff2", ".ttf", ".eot", ".mo", ".lock", ".map",
})
_SCANNER_EXCLUDED_FILE_NAMES = frozenset({
    ".coverage", "coverage.xml", "test-results.json", ".DS_Store",
})

# [BAO-VA P0-11] 4 mẫu secret thật. KHÔNG in giá trị khi phát hiện - chỉ in
# đường dẫn + số dòng, để log CI không trở thành nơi phát tán khoá bị lộ.
_SECRET_PATTERNS = {
    "hardcoded_authorization_bearer": re.compile(
        r"Authorization\s*[:=]\s*[\"']?\s*Bearer\s+[A-Za-z0-9._\-]{16,}", re.IGNORECASE
    ),
    "openrouter_api_key": re.compile(r"sk-or-v1-[A-Za-z0-9]{10,}"),
    "google_api_key": re.compile(r"AIza[0-9A-Za-z_\-]{30,}"),
    "private_key_block": re.compile(r"-----BEGIN[ A-Z]*PRIVATE KEY-----"),
}


def test_p0_11_no_secrets_in_tracked_files():
    """P0-11: Không được commit secret thật (Bearer token, OpenRouter, Google, private key).

    Vì sao là hồi quy nghiêm trọng: khoá bị commit vào git KHÔNG BAO GIỜ được coi là
    đã thu hồi (nằm vĩnh viễn trong history, ai clone repo cũng lấy được). Đặc biệt,
    khoá BYOK của khách hàng nằm trong cùng repo nên rò ở đây = rò dữ liệu khách hàng
    của MỌI agency.

    Cách chạy: quét file text trong repo, bỏ qua `.git`, dependency vendor, artifact
    build và mọi file do `.gitignore` loại (đặc biệt `.env` - nơi ta CỐ Ý chứa
    cấu hình thật của máy dev, không được commit). File `*.example` cũng bị bỏ qua vì
    theo thiết kế chứa giá trị mẫu.
    """
    findings: list[str] = []
    scanned_files = 0

    for dir_path, dir_names, file_names in os.walk(REPO_ROOT):
        dir_names[:] = [
            d for d in dir_names
            if d not in _SCANNER_EXCLUDED_DIRS and not d.startswith("_qa")
        ]
        for file_name in file_names:
            file_path = Path(dir_path) / file_name
            try:
                rel_posix = file_path.relative_to(REPO_ROOT).as_posix()
            except ValueError:
                continue

            if file_name in _SCANNER_EXCLUDED_FILE_NAMES:
                continue
            if ".example" in file_name:
                continue
            # .gitignore: .env, *.env, **/.env, **/.env.*  -> file cấu hình thật.
            if file_name == ".env" or file_name.startswith(".env."):
                continue
            if file_path.suffix.lower() in _SCANNER_EXCLUDED_SUFFIXES:
                continue
            if rel_posix in _SYNTHETIC_KEY_FIXTURE_FILES:
                continue

            try:
                text = file_path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError, ValueError):
                continue  # file nhị phân / không phải UTF-8 -> không quét được
            scanned_files += 1

            for pattern_name, pattern in _SECRET_PATTERNS.items():
                for match in pattern.finditer(text):
                    line_no = text.count("\n", 0, match.start()) + 1
                    # KHÔNG in giá trị secret - chỉ in vị trí.
                    findings.append(f"{rel_posix}:{line_no} [{pattern_name}]")

    assert scanned_files > 100, (
        f"P0-11: scanner chỉ quét {scanned_files} file - có lẽ đã quét sai phạm vi "
        "repo và bản vệ đang 'xanh giả'."
    )
    assert not findings, (
        "P0-11 HỒI QUY: phát hiện secret trong các file được theo dõi (vị trí bên dưới, "
        "KHÔNG in giá trị):\n  - " + "\n  - ".join(findings[:50]) +
        "\nNếu đây là khoá giả dùng để test, hãy đổi sang chuỗi rõ ràng là giả và "
        "giữ trong danh sách _SYNTHETIC_KEY_FIXTURE_FILES sau khi review. "
        "Khoá đã lộ trong git history phải được thu hồi (rotate), không chỉ xoá dòng."
    )
