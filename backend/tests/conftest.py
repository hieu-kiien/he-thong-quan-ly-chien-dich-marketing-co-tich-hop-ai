import sys
from pathlib import Path
import os
import sqlite3
import tempfile
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Generator, Optional
from unittest.mock import patch

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import pytest
import bcrypt
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base, get_db
import app.core.database as core_database
from app.main import app
from seed.seed_data import seed_data
from app.core.security import hash_password, create_access_token
from app.models.entities import (
    User, Workspace, WorkspaceMember, BrandKit,
    Campaign, CampaignMember, MarketingContent, CampaignMetric
)

# ==============================================================================
# 1. LIVE DATABASE GUARD & CONFIGURATION SAFETY
# ==============================================================================
TEST_DB_URL = "sqlite:///:memory:"
LIVE_DB_PATH = BASE_DIR / "marketing_campaigns.db"

# Redirect global settings and database.SessionLocal to memory engine
settings.DATABASE_URL = TEST_DB_URL

test_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Kích hoạt bắt buộc kiểm tra ràng buộc khóa ngoại trên SQLite cho môi trường test (BUG-BE-10)
@event.listens_for(test_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
core_database.SessionLocal = TestingSessionLocal
core_database.engine = test_engine
import seed.seed_data as seed_data_module
seed_data_module.engine = test_engine
seed_data_module.SessionLocal = TestingSessionLocal


# ==============================================================================
# 0. FAST BCRYPT FOR TESTS (không ảnh hưởng code production)
# ==============================================================================
# hash_password() trong app/core/security.py gọi bcrypt.gensalt() (cost mặc định 12).
# Mỗi lần ~0.34s. Fixture db_session + startup event gọi hash_password tới 6-9 lần
# mỗi test => ~2.4s setup/test. Ta chỉ hạ cost của bcrypt.gensalt TRONG PHIÊN TEST,
# không sửa app/core/security.py nên production vẫn dùng cost 12.
# Lưu ý: phải giữ tham chiếu tới hàm gốc, nếu gọi bcrypt.gensalt bên trong wrapper
# thì wrapper sẽ tự gọi chính nó -> RecursionError.
_BCRYPT_ORIGINAL_GENSALT = bcrypt.gensalt
TEST_BCRYPT_ROUNDS = 4


@pytest.fixture(autouse=True, scope="session")
def _fast_bcrypt_for_tests():
    """Giảm bcrypt cost trong test để chạy nhanh; KHÔNG ảnh hưởng code production.

    verify_password() vẫn hoạt động bình thường vì bcrypt.checkpw đọc cost từ chính
    chuỗi hash được lưu, và hash sinh ra vẫn có tiền tố "$2b$" (giữ nguyên giả định
    của test_challenger_m1_security.py).
    """
    def fast_gensalt(rounds: int = TEST_BCRYPT_ROUNDS, prefix: bytes = b"2b"):
        return _BCRYPT_ORIGINAL_GENSALT(rounds=TEST_BCRYPT_ROUNDS, prefix=prefix)

    bcrypt.gensalt = fast_gensalt
    try:
        yield
    finally:
        bcrypt.gensalt = _BCRYPT_ORIGINAL_GENSALT


@pytest.fixture(autouse=True)
def live_db_guard():
    """Autouse fixture verifying that live marketing_campaigns.db is NEVER modified during tests."""
    stat_before = None
    if LIVE_DB_PATH.exists():
        stat_before = (LIVE_DB_PATH.stat().st_size, LIVE_DB_PATH.stat().st_mtime_ns)
    yield
    if LIVE_DB_PATH.exists():
        stat_after = (LIVE_DB_PATH.stat().st_size, LIVE_DB_PATH.stat().st_mtime_ns)
        assert stat_before is not None, "Live database marketing_campaigns.db was created during test execution!"
        assert stat_before == stat_after, (
            f"Live database marketing_campaigns.db was modified during test execution! "
            f"Before: {stat_before}, After: {stat_after}"
        )
    else:
        assert stat_before is None, "Live database marketing_campaigns.db was deleted during test execution!"


# ==============================================================================
# 2. DETERMINISTIC VIETNAM TIMEZONE & CLOCK FREEZING FIXTURE
# ==============================================================================
# 2026-09-26 12:00:00+07:00 (Vietnam Standard Time) == 2026-09-26 05:00:00 UTC
VIETNAM_TZ = timezone(timedelta(hours=7))
FROZEN_TIME_VN = datetime(2026, 9, 26, 12, 0, 0, tzinfo=VIETNAM_TZ)
FROZEN_TIME_UTC = datetime(2026, 9, 26, 5, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def freeze_vietnam_time():
    """Fixture freezing UTC and Vietnam local clock to deterministic timestamp:
    2026-09-26 12:00:00+07:00 (2026-09-26 05:00:00 UTC).
    """
    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return FROZEN_TIME_VN.replace(tzinfo=None)
            if tz == timezone.utc or tz == getattr(timezone, "utc", None):
                return FROZEN_TIME_UTC
            return FROZEN_TIME_VN.astimezone(tz)

        @classmethod
        def utcnow(cls):
            return FROZEN_TIME_UTC.replace(tzinfo=None)

    def mock_utc_now():
        return FROZEN_TIME_UTC

    with patch("app.models.entities.utc_now", side_effect=mock_utc_now), \
         patch("app.models.entities.datetime", FrozenDateTime), \
         patch("app.core.security.datetime", FrozenDateTime):
        yield {
            "frozen_datetime_vn": FROZEN_TIME_VN,
            "frozen_datetime_utc": FROZEN_TIME_UTC,
            "timezone": VIETNAM_TZ,
            "date_iso": "2026-09-26",
            "time_iso": "12:00:00",
            "date_display": "26/09/2026",
            "datetime_display": "26/09/2026 12:00",
            "currency_symbol": "₫",
            "now": lambda tz=None: FrozenDateTime.now(tz),
            "utc_now": mock_utc_now,
        }


# ==============================================================================
# 3. BASE DATABASE & TEST CLIENT FIXTURES
# ==============================================================================
# Nguyên nhân suite chậm (~2.45s setup/test): mỗi test chạy lại
# drop_all + create_all + seed_data() (3 lần bcrypt cost 12 ~0.34s) + 3 user bổ sung
# (3 lần bcrypt nữa), RỒI startup event của TestClient lại chạy init_db + seed_data
# lần nữa. Tổng 6-9 lần bcrypt => ~2.4s chỉ để setup.
#
# Chiến lược mới (giữ nguyên bất biến "mỗi test bắt đầu từ DB sạch đã seed"):
#   1. _seeded_template (scope=session): seed_data() + user bổ sung CHẠY ĐÚNG 1 LẦN
#      vào một file SQLite tạm, tạo snapshot "khuôn mẫu".
#   2. db_session (scope=function): dùng SQLite backup API (sqlite3.Connection.backup)
#      để chép nguyên nội dung template vào in-memory engine. Đây là phép copy ở mức
#      trang (page-level), đo được ~0.6ms, thay cho ~2.4s seed lại từ đầu.
#   3. client: bỏ "with TestClient(app)" để không kích hoạt startup event (init_db +
#      seed_data + scheduler) - dữ liệu đã được _seeded_template cung cấp sẵn.
#
# Vì sao chọn phương án template + backup thay vì INSERT ... SELECT:
#   - SQLite KHÔNG cho phép INSERT INTO ... SELECT ... FROM <db khác> nếu không
#     ATTACH, nên phương án (b) nguyên bản phải ATTACH rồi copy từng bảng qua SQL
#     thủ công: chậm hơn nhiều và phải hard-code danh sách bảng/thứ tự khóa ngoại.
#   - backup() là 1 lệnh nguyên bản của SQLite, copy cả schema lẫn dữ liệu, không
#     cần biết trước danh sách bảng, và BẢO TOÀN ĐÚNG dữ liệu mà seed_data tạo ra
#     (campaigns, channels, metrics, brand kit, members...) nên không test nào mất data.
#   - create_all/drop_all thực ra chỉ ~0.04ms (đo thật), nên DDL không phải nút thắt;
#     nút thắt là bcrypt. Phương án (a) "bỏ seed_data, tự tạo nhóm dữ liệu tối thiểu"
#     sẽ phải liệt kê thủ công hàng chục bản ghi mà ~hàng trăm test đang dựa vào -> rủi ro
#     regression cao hơn nhiều so với lợi ích (phần DDL vốn đã rẻ).


def _seed_test_only_users(db) -> None:
    """User & membership chỉ phục vụ test (trước đây chạy lại ở mọi test).

    Gộp vào template để chạy đúng 1 lần cho cả session thay vì mỗi test.
    """
    # Seed additional agency manager user for Workspace Alpha if missing
    alpha_agency_mgr = db.query(User).filter(User.email.in_(["agency_mgr@gmail.com", "agency_mgr@gmail.com"])).first()
    if not alpha_agency_mgr:
        alpha_agency_mgr = User(
            email="agency_mgr@gmail.com",
            full_name="Nguyễn Văn Quản Lý Agency",
            password_hash=hash_password("AgencyMgr@123"),
            role="AGENCY_MANAGER",
            status="ACTIVE"
        )
        db.add(alpha_agency_mgr)
        db.commit()
        db.refresh(alpha_agency_mgr)

    ws1 = db.query(Workspace).filter(Workspace.id == 1).first()
    if ws1:
        mgr = db.query(User).filter(User.email.in_(["manager@gmail.com", "manager@gmail.com"])).first()
        mkt = db.query(User).filter(User.email.in_(["marketer@gmail.com", "marketer@gmail.com"])).first()
        appr = db.query(User).filter(User.email.in_(["approver@gmail.com", "approver@gmail.com"])).first()
        for u_obj, role_name in [
            (mgr, "AGENCY_MANAGER"),
            (mkt, "MARKETER"),
            (appr, "CLIENT_APPROVER"),
            (alpha_agency_mgr, "AGENCY_MANAGER")
        ]:
            if u_obj:
                mem = db.query(WorkspaceMember).filter(
                    WorkspaceMember.workspace_id == ws1.id,
                    WorkspaceMember.user_id == u_obj.id
                ).first()
                if not mem:
                    db.add(WorkspaceMember(
                        workspace_id=ws1.id,
                        user_id=u_obj.id,
                        role=role_name
                    ))
        db.commit()

    # Seed pre-existing users for test_adversarial_m1 compatibility
    for adv_email, adv_name in [
        ("agency_x_mgr@test.com", "Agency X Manager"),
        ("agency_y_mgr@test.com", "Agency Y Manager"),
    ]:
        u = db.query(User).filter(User.email == adv_email).first()
        if not u:
            db.add(User(
                email=adv_email,
                full_name=adv_name,
                password_hash=hash_password("Password123!"),
                role="AGENCY_MANAGER",
                status="ACTIVE"
            ))
    db.commit()


@pytest.fixture(scope="session")
def _seeded_template(_fast_bcrypt_for_tests):
    """Seed dữ liệu mẫu đúng 1 lần cho toàn bộ session, snapshot vào DB tạm.

    Trả về đường dẫn file SQLite chứa "khuôn mẫu" đã seed. File nằm trong thư mục
    tạm của hệ điều hành (không phải marketing_campaigns.db thật) nên live_db_guard
    không bị ảnh hưởng, và được xoá khi session kết thúc.
    """
    fd, template_path = tempfile.mkstemp(prefix="marketflow_seed_template_", suffix=".sqlite")
    os.close(fd)

    template_engine = create_engine(
        f"sqlite:///{template_path}",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(template_engine, "connect")
    def set_template_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    TemplateSession = sessionmaker(autocommit=False, autoflush=False, bind=template_engine)
    try:
        Base.metadata.create_all(bind=template_engine)
        s = TemplateSession()
        try:
            seed_data(session=s)
            _seed_test_only_users(s)
        finally:
            s.close()
        yield template_path
    finally:
        template_engine.dispose()
        try:
            os.unlink(template_path)
        except OSError:
            pass


def _restore_seeded_template(template_path: str) -> None:
    """Ghi đè toàn bộ in-memory DB bằng bản snapshot đã seed (SQLite backup API).

    sqlite3.Connection.backup() yêu cầu connection đích KHÔNG nằm trong
    transaction đang mở, nên phải rollback trước khi copy.
    """
    raw = test_engine.raw_connection()
    try:
        dest = raw.driver_connection
        if dest.in_transaction:
            dest.rollback()
        src = sqlite3.connect(template_path)
        try:
            src.backup(dest)
        finally:
            src.close()
    finally:
        raw.close()


def _seed_test_db_legacy_way() -> None:
    """Fallback: tạo lại DB từ đầu nếu backup API không khả dụng trên nền tảng này."""
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    s = TestingSessionLocal()
    try:
        seed_data(session=s)
        _seed_test_only_users(s)
    finally:
        s.close()


@pytest.fixture(scope="function")
def db_session(_seeded_template):
    # Khôi phục "khuôn mẫu" đã seed cho mỗi test: nhanh (~0.6ms) và sạch hoàn toàn
    try:
        _restore_seeded_template(_seeded_template)
    except sqlite3.Error:
        _seed_test_db_legacy_way()

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Giữ nguyên hành vi cũ: sau mỗi test DB trả về trạng thái rỗng, để các test
        # tự tạo session riêng không vô tình đọc dữ liệu của test trước.
        # drop_all chỉ ~0.04ms nên không ảnh hưởng tổng thời gian.
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    # KHÔNG dùng "with TestClient(app)": context manager sẽ chạy startup event của
    # app/main.py, gọi init_db() + seed_data() lần nữa (và start_scheduler_task).
    # Dữ liệu đã có sẵn từ _seeded_template nên không cần startup event.
    c = TestClient(app)
    try:
        yield c
    finally:
        c.close()
        app.dependency_overrides.clear()


# ==============================================================================
# 4. MULTI-TENANT WORKSPACE FIXTURES
# ==============================================================================
@pytest.fixture
def workspace_alpha(db_session) -> Workspace:
    """Workspace Alpha (id=1, slug='default-agency') with 4 RBAC roles."""
    ws = db_session.query(Workspace).filter(Workspace.id == 1).first()
    if not ws:
        ws = db_session.query(Workspace).filter(Workspace.slug == "default-agency").first()
    assert ws is not None, "Workspace Alpha (id=1) must exist from seed_data"
    return ws


@pytest.fixture
def workspace_beta(db_session, workspace_alpha) -> Workspace:
    """Workspace Beta (id=2, slug='beta-workspace') with dedicated Agency Manager and Marketer."""
    # 1. Users
    agency_mgr_beta = db_session.query(User).filter(User.email.in_(["agency_mgr_beta@gmail.com", "agency_mgr_beta@gmail.com"])).first()
    if not agency_mgr_beta:
        agency_mgr_beta = User(
            email="agency_mgr_beta@gmail.com",
            full_name="Trần Agency Beta",
            password_hash=hash_password("BetaAgencyMgr@123"),
            role="AGENCY_MANAGER",
            status="ACTIVE"
        )
        db_session.add(agency_mgr_beta)
        db_session.commit()
        db_session.refresh(agency_mgr_beta)

    marketer_beta = db_session.query(User).filter(User.email.in_(["marketer_beta@gmail.com", "marketer_beta@gmail.com"])).first()
    if not marketer_beta:
        marketer_beta = User(
            email="marketer_beta@gmail.com",
            full_name="Lê Marketer Beta",
            password_hash=hash_password("BetaMarketer@123"),
            role="MARKETER",
            status="ACTIVE"
        )
        db_session.add(marketer_beta)
        db_session.commit()
        db_session.refresh(marketer_beta)

    # 2. Workspace Beta
    ws_beta = db_session.query(Workspace).filter(Workspace.id == 2).first()
    if not ws_beta:
        ws_beta = db_session.query(Workspace).filter(Workspace.slug == "beta-workspace").first()
    if not ws_beta:
        ws_beta = Workspace(
            id=2,
            name="Beta Agency Workspace",
            slug="beta-workspace",
            description="Không gian làm việc thứ hai thử nghiệm cách ly bảo mật",
            owner_id=agency_mgr_beta.id,
            status="ACTIVE"
        )
        db_session.add(ws_beta)
        db_session.commit()
        db_session.refresh(ws_beta)

    # 3. Workspace Members
    for user_obj, role_name in [(agency_mgr_beta, "AGENCY_MANAGER"), (marketer_beta, "MARKETER")]:
        mem = db_session.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == ws_beta.id,
            WorkspaceMember.user_id == user_obj.id
        ).first()
        if not mem:
            db_session.add(WorkspaceMember(
                workspace_id=ws_beta.id,
                user_id=user_obj.id,
                role=role_name
            ))

    # 4. Brand Kit
    brand_kit = db_session.query(BrandKit).filter(BrandKit.workspace_id == ws_beta.id).first()
    if not brand_kit:
        brand_kit = BrandKit(
            workspace_id=ws_beta.id,
            brand_name="Beta Agency Co.",
            usp="Dịch vụ tiếp thị đột phá độc quyền cho Workspace Beta",
            tone_of_voice="Sáng tạo, táo bạo, đột phá, năng động",
            banned_keywords_json='["cam kết 100%", "làm giàu nhanh"]'
        )
        db_session.add(brand_kit)

    # 5. Dedicated Beta Campaign and Content for cross-workspace tests
    beta_campaign = db_session.query(Campaign).filter(Campaign.workspace_id == ws_beta.id).first()
    if not beta_campaign:
        beta_campaign = Campaign(
            workspace_id=ws_beta.id,
            product_id=1,
            owner_id=marketer_beta.id,
            name="Chiến dịch Beta Độc Quyền",
            objective="Thử nghiệm cách ly tài nguyên giữa hai workspace",
            audience="Khách hàng mục tiêu của Beta",
            start_date="2026-09-01",
            end_date="2026-09-30",
            budget=8000000.0,
            status="ACTIVE"
        )
        db_session.add(beta_campaign)
        db_session.commit()
        db_session.refresh(beta_campaign)

        db_session.add(CampaignMember(
            campaign_id=beta_campaign.id,
            user_id=marketer_beta.id,
            member_role="OWNER"
        ))

    beta_content = db_session.query(MarketingContent).filter(MarketingContent.workspace_id == ws_beta.id).first()
    if not beta_content:
        beta_content = MarketingContent(
            workspace_id=ws_beta.id,
            campaign_id=beta_campaign.id,
            channel_id=1,
            created_by=marketer_beta.id,
            title="Bài viết tiếp thị thuộc Không gian Beta",
            body="Nội dung mật chỉ dành riêng cho Workspace Beta",
            cta="Tìm hiểu ngay",
            status="DRAFT",
            version_no=1
        )
        db_session.add(beta_content)

    db_session.commit()
    db_session.refresh(ws_beta)
    return ws_beta


# ==============================================================================
# 5. ROLE AUTHORIZATION HEADERS FIXTURES
# ==============================================================================
def _token_for_user(user: User) -> Dict[str, str]:
    token = create_access_token(data={
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "full_name": user.full_name
    })
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def manager_headers(db_session, workspace_alpha) -> Dict[str, str]:
    u = db_session.query(User).filter(User.email.in_(["manager@gmail.com", "manager@gmail.com"])).first()
    assert u is not None, "Manager user must exist"
    return _token_for_user(u)


@pytest.fixture
def marketer_headers(db_session, workspace_alpha) -> Dict[str, str]:
    u = db_session.query(User).filter(User.email.in_(["marketer@gmail.com", "marketer@gmail.com"])).first()
    assert u is not None, "Marketer user must exist"
    return _token_for_user(u)


@pytest.fixture
def client_approver_headers(db_session, workspace_alpha) -> Dict[str, str]:
    u = db_session.query(User).filter(User.email.in_(["approver@gmail.com", "approver@gmail.com"])).first()
    assert u is not None, "Client approver user must exist"
    return _token_for_user(u)


@pytest.fixture
def approver_headers(client_approver_headers) -> Dict[str, str]:
    """Alias for client_approver_headers."""
    return client_approver_headers


@pytest.fixture
def agency_manager_headers(db_session, workspace_alpha) -> Dict[str, str]:
    u = db_session.query(User).filter(User.email.in_(["agency_mgr@gmail.com", "agency_mgr@gmail.com"])).first()
    assert u is not None, "Agency manager user must exist"
    return _token_for_user(u)


@pytest.fixture
def beta_agency_manager_headers(db_session, workspace_beta) -> Dict[str, str]:
    u = db_session.query(User).filter(User.email.in_(["agency_mgr_beta@gmail.com", "agency_mgr_beta@gmail.com"])).first()
    assert u is not None, "Beta agency manager user must exist"
    return _token_for_user(u)


@pytest.fixture
def beta_marketer_headers(db_session, workspace_beta) -> Dict[str, str]:
    u = db_session.query(User).filter(User.email.in_(["marketer_beta@gmail.com", "marketer_beta@gmail.com"])).first()
    assert u is not None, "Beta marketer user must exist"
    return _token_for_user(u)


@pytest.fixture
def rbac_headers(
    manager_headers,
    marketer_headers,
    client_approver_headers,
    agency_manager_headers,
    beta_agency_manager_headers,
    beta_marketer_headers
) -> Dict[str, Dict[str, str]]:
    """Composite authorization dictionary providing headers for all roles across both workspaces."""
    return {
        "manager": manager_headers,
        "marketer": marketer_headers,
        "client_approver": client_approver_headers,
        "agency_manager": agency_manager_headers,
        "beta_agency_manager": beta_agency_manager_headers,
        "beta_marketer": beta_marketer_headers,
    }


# ==============================================================================
# 6. TEST METRICS FIXTURES (Rich, Empty, 0 Metrics)
# ==============================================================================
@pytest.fixture
def rich_metrics_campaign(db_session, workspace_alpha) -> Campaign:
    """Campaign with rich positive performance metrics (views, clicks, conversions, cost, revenue)."""
    camp = db_session.query(Campaign).filter(Campaign.id == 1).first()
    assert camp is not None, "Campaign 1 must exist from seed_data"
    count = db_session.query(CampaignMetric).filter(CampaignMetric.campaign_id == camp.id).count()
    assert count >= 2, "Rich metrics campaign must have at least 2 metrics rows"
    return camp


@pytest.fixture
def empty_metrics_campaign(db_session, workspace_alpha) -> Campaign:
    """Campaign with empty metrics (0 rows of CampaignMetric)."""
    camp = db_session.query(Campaign).filter(Campaign.id == 2).first()
    if not camp:
        camp = Campaign(
            workspace_id=1,
            product_id=1,
            owner_id=1,
            name="Empty Metrics Dedicated Campaign",
            objective="Testing empty metrics",
            audience="Audience",
            start_date="2026-10-01",
            end_date="2026-10-31",
            budget=10000000.0,
            status="PLANNED"
        )
        db_session.add(camp)
        db_session.commit()
        db_session.refresh(camp)
    return camp


@pytest.fixture
def zero_metrics_campaign(db_session, workspace_alpha) -> Campaign:
    """Campaign with metric rows where all counters are strictly 0."""
    camp = Campaign(
        workspace_id=1,
        product_id=1,
        owner_id=1,
        name="Zero Metrics Dedicated Campaign",
        objective="Testing zero values for views/clicks/conversions/cost/revenue",
        audience="Audience Zero",
        start_date="2026-10-01",
        end_date="2026-10-31",
        budget=10000000.0,
        status="ACTIVE"
    )
    db_session.add(camp)
    db_session.commit()
    db_session.refresh(camp)

    zero_metric = CampaignMetric(
        campaign_id=camp.id,
        channel_id=1,
        metric_date="2026-09-25",
        views=0,
        clicks=0,
        conversions=0,
        cost=0.0,
        revenue=0.0
    )
    db_session.add(zero_metric)
    db_session.commit()
    db_session.refresh(camp)
    return camp


@pytest.fixture
def test_metrics_matrix():
    """Reference data dictionary for metrics test scenarios."""
    return {
        "rich": {
            "views": 15000,
            "clicks": 850,
            "conversions": 45,
            "cost": 1500000.0,
            "revenue": 7500000.0,
            "metric_date": "2026-09-20"
        },
        "empty": [],
        "zero": {
            "views": 0,
            "clicks": 0,
            "conversions": 0,
            "cost": 0.0,
            "revenue": 0.0,
            "metric_date": "2026-09-25"
        }
    }
