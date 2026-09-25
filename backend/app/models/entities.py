import enum
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Numeric, Text, ForeignKey, 
    DateTime, CheckConstraint, UniqueConstraint, Index, Boolean
)
from sqlalchemy.orm import relationship
from app.core.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class UserRole(str, enum.Enum):
    MANAGER = "MANAGER"
    MARKETER = "MARKETER"
    AGENCY_MANAGER = "AGENCY_MANAGER"
    CLIENT_APPROVER = "CLIENT_APPROVER"
    ADMIN = "ADMIN"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="MARKETER") # 'MANAGER', 'MARKETER', 'AGENCY_MANAGER', 'CLIENT_APPROVER', 'ADMIN'
    status = Column(String(50), nullable=False, default="ACTIVE") # 'ACTIVE', 'DISABLED'
    created_at = Column(DateTime, default=utc_now, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "role IN ('MANAGER', 'MARKETER', 'AGENCY_MANAGER', 'CLIENT_APPROVER', 'ADMIN')", 
            name="chk_user_role"
        ),
        CheckConstraint("status IN ('ACTIVE', 'DISABLED')", name="chk_user_status"),
    )

    campaigns = relationship("Campaign", back_populates="owner")
    contents = relationship("MarketingContent", back_populates="creator")
    reviews = relationship("ContentReview", back_populates="reviewer")
    ai_logs = relationship("AILog", back_populates="user")
    owned_workspaces = relationship("Workspace", back_populates="owner", cascade="all, delete-orphan")
    workspace_memberships = relationship("WorkspaceMember", back_populates="user", cascade="all, delete-orphan")
    custom_api_keys = relationship("CustomApiKey", back_populates="user", cascade="all, delete-orphan")



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


class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id", onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    status = Column(String(50), nullable=False, default="ACTIVE")
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('ACTIVE', 'ARCHIVED')", name="chk_workspace_status"),
    )

    owner = relationship("User", back_populates="owned_workspaces")
    members = relationship("WorkspaceMember", back_populates="workspace", cascade="all, delete-orphan")
    brand_kit = relationship("BrandKit", back_populates="workspace", uselist=False, cascade="all, delete-orphan")
    campaigns = relationship("Campaign", back_populates="workspace")
    contents = relationship("MarketingContent", back_populates="workspace")
    custom_api_keys = relationship("CustomApiKey", back_populates="workspace", cascade="all, delete-orphan")


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    role = Column(String(50), nullable=False, default="MARKETER") # AGENCY_MANAGER, MARKETER, CLIENT_APPROVER, MANAGER
    joined_at = Column(DateTime, default=utc_now, nullable=False)

    __table_args__ = (
        CheckConstraint("role IN ('AGENCY_MANAGER', 'MARKETER', 'CLIENT_APPROVER', 'MANAGER')", name="chk_workspace_member_role"),
        UniqueConstraint("workspace_id", "user_id", name="uq_workspace_user"),
        Index("idx_workspace_members_user", "user_id"),
    )

    workspace = relationship("Workspace", back_populates="members")
    user = relationship("User", back_populates="workspace_memberships")


class BrandKit(Base):
    __tablename__ = "brand_kits"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", onupdate="CASCADE", ondelete="CASCADE"), unique=True, nullable=False)
    brand_name = Column(String(255), nullable=False)
    usp = Column(Text, nullable=True) # Unique Selling Proposition
    tone_of_voice = Column(String(255), nullable=False, default="Chuyên nghiệp, hiện đại, tin cậy")
    banned_keywords_json = Column(Text, nullable=False, default="[]") # JSON list of banned words
    target_audience = Column(Text, nullable=True)
    brand_guidelines = Column(Text, nullable=True)
    logo_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    workspace = relationship("Workspace", back_populates="brand_kit")


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", onupdate="CASCADE", ondelete="SET NULL"), nullable=True, default=1)
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

    workspace = relationship("Workspace", back_populates="campaigns")
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
    workspace_id = Column(Integer, ForeignKey("workspaces.id", onupdate="CASCADE", ondelete="SET NULL"), nullable=True, default=1)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    channel_id = Column(Integer, ForeignKey("marketing_channels.id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    cta = Column(String(255), nullable=True)
    image_url = Column(String(1024), nullable=True, default=None)
    status = Column(String(50), nullable=False, default="DRAFT")
    source_ids_json = Column(Text, nullable=False, default="[]")
    warnings_json = Column(Text, nullable=True, default="[]", server_default="[]")
    version_no = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        CheckConstraint("version_no > 0", name="chk_content_version"),
        CheckConstraint("status IN ('DRAFT', 'AI_DRAFT', 'IN_REVIEW', 'APPROVED', 'REJECTED', 'PUBLISHED')", name="chk_content_status"),
        Index("idx_contents_campaign_status", "campaign_id", "status"),
    )

    workspace = relationship("Workspace", back_populates="contents")
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
        CheckConstraint("task_type IN ('IDEA', 'DRAFT', 'SUMMARY', 'OMNICHANNEL')", name="chk_ai_task_type"),
        CheckConstraint("result_status IN ('SUCCESS', 'SCHEMA_ERROR', 'TIMEOUT', 'RATE_LIMIT', 'PROVIDER_ERROR', 'BLOCKED')", name="chk_ai_result_status"),
        CheckConstraint("latency_ms IS NULL OR latency_ms >= 0", name="chk_ai_latency"),
        Index("idx_ai_logs_campaign_created", "campaign_id", "created_at"),
    )

    user = relationship("User", back_populates="ai_logs")
    campaign = relationship("Campaign", back_populates="ai_logs")


class CustomApiKey(Base):
    __tablename__ = "custom_api_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", onupdate="CASCADE", ondelete="CASCADE"), nullable=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", onupdate="CASCADE", ondelete="CASCADE"), nullable=True, index=True)
    provider = Column(String(50), nullable=False, default="gemini")
    encrypted_key = Column(Text, nullable=False)
    model = Column(String(100), nullable=False, default="gemini-2.5-flash")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        CheckConstraint("provider IN ('gemini', 'openrouter', 'openai')", name="chk_api_key_provider"),
        CheckConstraint("user_id IS NOT NULL OR workspace_id IS NOT NULL", name="chk_api_key_owner"),
        Index("idx_custom_keys_user", "user_id", "provider"),
        Index("idx_custom_keys_workspace", "workspace_id", "provider"),
    )

    user = relationship("User", back_populates="custom_api_keys")
    workspace = relationship("Workspace", back_populates="custom_api_keys")

