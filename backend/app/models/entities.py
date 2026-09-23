from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Numeric, Text, ForeignKey, 
    DateTime, CheckConstraint, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from app.core.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False) # 'MANAGER', 'MARKETER'
    status = Column(String(50), nullable=False, default="ACTIVE") # 'ACTIVE', 'DISABLED'
    created_at = Column(DateTime, default=utc_now, nullable=False)

    __table_args__ = (
        CheckConstraint("role IN ('MANAGER', 'MARKETER')", name="chk_user_role"),
        CheckConstraint("status IN ('ACTIVE', 'DISABLED')", name="chk_user_status"),
    )

    campaigns = relationship("Campaign", back_populates="owner")
    contents = relationship("MarketingContent", back_populates="creator")
    reviews = relationship("ContentReview", back_populates="reviewer")
    ai_logs = relationship("AILog", back_populates="user")


class ProductCategory(Base):
    __tablename__ = "product_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    products = relationship("Product", back_populates="category")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("product_categories.id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    usp = Column(Text, nullable=True) # Unique Selling Proposition
    status = Column(String(50), nullable=False, default="ACTIVE")

    __table_args__ = (
        CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name="chk_product_status"),
    )

    category = relationship("ProductCategory", back_populates="products")
    campaigns = relationship("Campaign", back_populates="product")


class MarketingChannel(Base):
    __tablename__ = "marketing_channels"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False) # 'facebook', 'email', 'blog', 'google_ads'
    name = Column(String(255), nullable=False)
    format_rules = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="ACTIVE")

    __table_args__ = (
        CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name="chk_channel_status"),
    )

    contents = relationship("MarketingContent", back_populates="channel")
    metrics = relationship("CampaignMetric", back_populates="channel")


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    name = Column(String(255), nullable=False)
    objective = Column(Text, nullable=False)
    audience = Column(Text, nullable=False)
    start_date = Column(String(50), nullable=False) # YYYY-MM-DD
    end_date = Column(String(50), nullable=False)   # YYYY-MM-DD
    budget = Column(Numeric(12, 2), nullable=False, default=0)
    status = Column(String(50), nullable=False, default="DRAFT")
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        CheckConstraint("budget >= 0", name="chk_campaign_budget"),
        CheckConstraint("end_date >= start_date", name="chk_campaign_dates"),
        CheckConstraint("status IN ('DRAFT', 'PLANNED', 'ACTIVE', 'PAUSED', 'COMPLETED', 'ARCHIVED')", name="chk_campaign_status"),
        Index("idx_campaigns_owner_status", "owner_id", "status"),
        Index("idx_campaigns_dates", "start_date", "end_date"),
    )

    product = relationship("Product", back_populates="campaigns")
    owner = relationship("User", back_populates="campaigns")
    members = relationship("CampaignMember", back_populates="campaign", cascade="all, delete-orphan")
    contents = relationship("MarketingContent", back_populates="campaign", cascade="all, delete-orphan")
    metrics = relationship("CampaignMetric", back_populates="campaign", cascade="all, delete-orphan")
    ai_logs = relationship("AILog", back_populates="campaign")


class CampaignMember(Base):
    __tablename__ = "campaign_members"

    campaign_id = Column(Integer, ForeignKey("campaigns.id", onupdate="CASCADE", ondelete="CASCADE"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", onupdate="CASCADE", ondelete="RESTRICT"), primary_key=True)
    member_role = Column(String(50), nullable=False, default="CONTRIBUTOR")
    assigned_at = Column(DateTime, default=utc_now, nullable=False)

    __table_args__ = (
        CheckConstraint("member_role IN ('OWNER', 'CONTRIBUTOR')", name="chk_member_role"),
    )

    campaign = relationship("Campaign", back_populates="members")
    user = relationship("User")


class MarketingContent(Base):
    __tablename__ = "marketing_contents"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    channel_id = Column(Integer, ForeignKey("marketing_channels.id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    cta = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False, default="DRAFT")
    source_ids_json = Column(Text, nullable=False, default="[]")
    warnings_json = Column(Text, nullable=False, default="[]")
    version_no = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        CheckConstraint("version_no > 0", name="chk_content_version"),
        CheckConstraint("status IN ('DRAFT', 'AI_DRAFT', 'IN_REVIEW', 'APPROVED', 'REJECTED', 'PUBLISHED')", name="chk_content_status"),
        Index("idx_contents_campaign_status", "campaign_id", "status"),
    )

    campaign = relationship("Campaign", back_populates="contents")
    channel = relationship("MarketingChannel", back_populates="contents")
    creator = relationship("User", back_populates="contents")
    reviews = relationship("ContentReview", back_populates="content", cascade="all, delete-orphan")
    schedules = relationship("MarketingSchedule", back_populates="content", cascade="all, delete-orphan")


class ContentReview(Base):
    __tablename__ = "content_reviews"

    id = Column(Integer, primary_key=True, index=True)
    content_id = Column(Integer, ForeignKey("marketing_contents.id", onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    reviewer_id = Column(Integer, ForeignKey("users.id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    decision = Column(String(50), nullable=False) # 'APPROVED', 'REJECTED', 'REQUEST_CHANGES'
    reason = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    __table_args__ = (
        CheckConstraint("decision IN ('APPROVED', 'REJECTED', 'REQUEST_CHANGES')", name="chk_review_decision"),
        Index("idx_reviews_content_created", "content_id", "created_at"),
    )

    content = relationship("MarketingContent", back_populates="reviews")
    reviewer = relationship("User", back_populates="reviews")


class MarketingSchedule(Base):
    __tablename__ = "marketing_schedules"

    id = Column(Integer, primary_key=True, index=True)
    content_id = Column(Integer, ForeignKey("marketing_contents.id", onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    scheduled_at = Column(String(50), nullable=False) # ISO String or YYYY-MM-DD HH:MM
    timezone = Column(String(50), nullable=False, default="Asia/Ho_Chi_Minh")
    status = Column(String(50), nullable=False, default="PLANNED") # 'PLANNED', 'CANCELLED', 'EXECUTED'
    created_by = Column(Integer, ForeignKey("users.id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('PLANNED', 'CANCELLED', 'EXECUTED')", name="chk_schedule_status"),
        Index("idx_schedules_time_status", "scheduled_at", "status"),
    )

    content = relationship("MarketingContent", back_populates="schedules")
    creator = relationship("User")


class CampaignMetric(Base):
    __tablename__ = "campaign_metrics"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    channel_id = Column(Integer, ForeignKey("marketing_channels.id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    metric_date = Column(String(50), nullable=False) # YYYY-MM-DD
    views = Column(Integer, nullable=False, default=0)
    clicks = Column(Integer, nullable=False, default=0)
    conversions = Column(Integer, nullable=False, default=0)
    cost = Column(Numeric(12, 2), nullable=False, default=0)
    revenue = Column(Numeric(12, 2), nullable=False, default=0)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    __table_args__ = (
        CheckConstraint("views >= 0", name="chk_views_nonneg"),
        CheckConstraint("clicks >= 0", name="chk_clicks_nonneg"),
        CheckConstraint("conversions >= 0", name="chk_conversions_nonneg"),
        CheckConstraint("cost >= 0", name="chk_cost_nonneg"),
        CheckConstraint("revenue >= 0", name="chk_revenue_nonneg"),
        CheckConstraint("clicks <= views", name="chk_clicks_le_views"),
        UniqueConstraint("campaign_id", "channel_id", "metric_date", name="uq_campaign_channel_date"),
        Index("idx_metrics_campaign_date", "campaign_id", "metric_date"),
    )

    campaign = relationship("Campaign", back_populates="metrics")
    channel = relationship("MarketingChannel", back_populates="metrics")


class AILog(Base):
    __tablename__ = "ai_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", onupdate="CASCADE", ondelete="SET NULL"), nullable=True)
    task_type = Column(String(50), nullable=False) # 'IDEA', 'DRAFT', 'SUMMARY'
    provider = Column(String(100), nullable=False)
    model = Column(String(100), nullable=False)
    prompt_version = Column(String(50), nullable=False)
    input_hash = Column(String(64), nullable=False)
    source_ids_json = Column(Text, nullable=False, default="[]")
    output_json = Column(Text, nullable=True)
    result_status = Column(String(50), nullable=False) # 'SUCCESS', 'SCHEMA_ERROR', 'TIMEOUT', 'RATE_LIMIT', 'PROVIDER_ERROR', 'BLOCKED'
    error_code = Column(String(50), nullable=True)
    latency_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    __table_args__ = (
        CheckConstraint("task_type IN ('IDEA', 'DRAFT', 'SUMMARY')", name="chk_ai_task_type"),
        CheckConstraint("result_status IN ('SUCCESS', 'SCHEMA_ERROR', 'TIMEOUT', 'RATE_LIMIT', 'PROVIDER_ERROR', 'BLOCKED')", name="chk_ai_result_status"),
        CheckConstraint("latency_ms IS NULL OR latency_ms >= 0", name="chk_ai_latency"),
        Index("idx_ai_logs_campaign_created", "campaign_id", "created_at"),
    )

    user = relationship("User", back_populates="ai_logs")
    campaign = relationship("Campaign", back_populates="ai_logs")
