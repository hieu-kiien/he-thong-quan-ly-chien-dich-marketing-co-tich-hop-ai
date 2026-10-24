"""Pytest fixtures: in-memory SQLite, test client, users, auth headers (CONTRACT §9)."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import create_access_token, hash_password
from app.core.timeutil import today_vn
from app.main import app
from app.models import (
    Campaign,
    CampaignChannel,
    Channel,
    Content,
    User,
)
from app.models.enums import (
    CampaignGoal,
    CampaignStatus,
    ContentOrigin,
    ContentStatus,
    ContentType,
    UserRole,
)

# SQLite in-memory with StaticPool for cross-thread test isolation
TEST_DB_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def test_engine():
    engine = create_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db(test_engine) -> Iterator[Session]:
    connection = test_engine.connect()
    transaction = connection.begin()
    SessionTest = sessionmaker(bind=connection, autoflush=False, expire_on_commit=False)
    session = SessionTest()

    yield session

    session.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as tc:
        yield tc
    app.dependency_overrides.clear()


@pytest.fixture
def manager_user(db: Session) -> User:
    user = User(
        email="manager.test@marketflow.vn",
        full_name="Nguyễn Văn Quản Lý Test",
        password_hash=hash_password("Manager@123"),
        role=UserRole.MANAGER,
        is_active=True,
        token_version=0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def marketer1_user(db: Session) -> User:
    user = User(
        email="marketer1.test@marketflow.vn",
        full_name="Trần Thị Lan Anh Test",
        password_hash=hash_password("Marketer@123"),
        role=UserRole.MARKETER,
        is_active=True,
        token_version=0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def marketer2_user(db: Session) -> User:
    user = User(
        email="marketer2.test@marketflow.vn",
        full_name="Lê Hoàng Minh Test",
        password_hash=hash_password("Marketer@123"),
        role=UserRole.MARKETER,
        is_active=True,
        token_version=0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def manager_headers(manager_user: User) -> dict[str, str]:
    token = create_access_token(manager_user)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def marketer1_headers(marketer1_user: User) -> dict[str, str]:
    token = create_access_token(marketer1_user)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def marketer2_headers(marketer2_user: User) -> dict[str, str]:
    token = create_access_token(marketer2_user)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_channels(db: Session) -> dict[str, Channel]:
    channels = [
        Channel(code="FACEBOOK", name="Facebook Fanpage", format_rules="Max 2000 chars", is_active=True),
        Channel(code="INSTAGRAM", name="Instagram", format_rules="Max 1000 chars", is_active=True),
        Channel(code="TIKTOK", name="TikTok", format_rules="15-60s video", is_active=True),
        Channel(code="EMAIL", name="Email Marketing", format_rules="Under 60 chars subject", is_active=True),
        Channel(code="WEBSITE", name="Website Blog", format_rules="SEO 800-1500 words", is_active=True),
        Channel(code="ZALO_OA", name="Zalo OA", format_rules="Under 100 chars", is_active=True),
        Channel(code="GOOGLE_ADS", name="Google Ads", format_rules="30 chars headline", is_active=True),
    ]
    db.add_all(channels)
    db.commit()
    return {c.code: c for c in channels}


@pytest.fixture
def sample_campaign(db: Session, marketer1_user: User, test_channels: dict[str, Channel]) -> Campaign:
    today = today_vn()
    camp = Campaign(
        name="Chiến dịch Cold Brew Test",
        goal=CampaignGoal.SALES,
        objective="Tăng trưởng doanh số Cold Brew",
        target_audience="Dân văn phòng 24-35",
        product="Cold Brew Đóng Chai",
        key_message="Mát lạnh tỉnh táo",
        start_date=today - timedelta(days=10),
        end_date=today + timedelta(days=20),
        budget=Decimal(20_000_000),
        status=CampaignStatus.ACTIVE,
        owner_id=marketer1_user.id,
    )
    camp.channel_links = [
        CampaignChannel(channel_id=test_channels["FACEBOOK"].id, planned_budget=Decimal(12_000_000)),
        CampaignChannel(channel_id=test_channels["INSTAGRAM"].id, planned_budget=Decimal(8_000_000)),
    ]
    db.add(camp)
    db.commit()
    db.refresh(camp)
    return camp


@pytest.fixture
def sample_content(db: Session, sample_campaign: Campaign, marketer1_user: User, test_channels: dict[str, Channel]) -> Content:
    content = Content(
        campaign_id=sample_campaign.id,
        channel_id=test_channels["FACEBOOK"].id,
        content_type=ContentType.SOCIAL_POST,
        title="Bài viết giới thiệu Cold Brew",
        body="Hương vị cà phê ủ lạnh đặc biệt...",
        cta="Đặt mua ngay",
        status=ContentStatus.DRAFT,
        origin=ContentOrigin.MANUAL,
        created_by=marketer1_user.id,
    )
    db.add(content)
    db.commit()
    db.refresh(content)
    return content
