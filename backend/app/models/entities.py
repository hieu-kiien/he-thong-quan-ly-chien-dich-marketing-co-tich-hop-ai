import enum
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Numeric, Text, ForeignKey, 
    DateTime, CheckConstraint, UniqueConstraint, Index, Boolean
)
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.services.ai.providers import SUPPORTED_PROVIDER_SLUGS

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
    # Phiên đăng nhập: tăng số này (logout / đổi mật khẩu) để thu hồi MỌI token
    # đã phát hành trước đó. JWT không thể "hạ" từ phía server nên đây là cách
    # revocation duy nhất không cần lưu黑名单 token từng cái.
    token_version = Column(Integer, nullable=False, default=0, server_default="0")
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
    # Job AI bất đồng bộ: xoá workspace thì xoá luôn lịch sử job của tenant đó,
    # nếu không các bản ghi mồ côi sẽ mọc lên và bị tầng phân quyền từ chối
    # (fail-closed) khiến chúng chỉ tốn chỗ vô ích.
    ai_jobs = relationship("AIJob", back_populates="workspace", cascade="all, delete-orphan")


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
        # _accessible_workspace_ids() chạy ở MỌI request có lọc tenant và luôn
        # lọc theo user_id; thiếu index thì mỗi request phải quét bảng thành viên.
        Index("idx_workspace_members_workspace", "workspace_id"),
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
    # NULL van con ton tai trong schema de khong pha migration CSDL cu, nhung KHONG con duoc coi la
    # hop le o tang kiem tra quyen: cac noi dung kiem tra phan quyen (check_campaign_access,
    # check_workspace_boundary, check_content_access) quy tac FAIL-CLOSED, tu choi truy cap
    # khi workspace_id IS NULL. Can migration dan de gan workspace cho du lieu cu.
    # M4: migration idempotent trong app/core/database.py (_backfill_tenant_workspace_ids,
    # chay tu ensure_sqlite_schema_compatibility) da gan workspace_id cho du lieu legacy
    # (content lay tu campaign cha; campaign lay tu workspace ma owner so huu, neu khong
    # thi workspace dau tien owner la thanh vien). Con lai NULL => tieu de muc do chung
    # va van bi fail-closed o moi endpoint.
    workspace_id = Column(Integer, ForeignKey("workspaces.id", onupdate="CASCADE", ondelete="SET NULL"), nullable=True)
    product_id = Column(Integer, ForeignKey("products.id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    name = Column(String(255), nullable=False)
    objective = Column(Text, nullable=False)
    audience = Column(Text, nullable=False)
    start_date = Column(String(50), nullable=False) # YYYY-MM-DD
    end_date = Column(String(50), nullable=False)   # YYYY-MM-DD
    budget = Column(Numeric(12, 2), nullable=False, default=0)
    status = Column(String(50), nullable=False, default="DRAFT")
    key_message = Column(Text, nullable=True)
    primary_cta = Column(String(255), nullable=True)
    target_kpi_name = Column(String(50), nullable=True)
    target_kpi_value = Column(Numeric(12, 2), nullable=True)
    campaign_code = Column(String(100), nullable=True, index=True)
    funnel_stage = Column(String(20), nullable=False, default="BoFU", server_default="BoFU")
    daily_budget_cap = Column(Numeric(12, 2), nullable=True)
    tags_json = Column(Text, nullable=True, default="[]", server_default="[]")
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        CheckConstraint("budget >= 0", name="chk_campaign_budget"),
        CheckConstraint("end_date >= start_date", name="chk_campaign_dates"),
        CheckConstraint("status IN ('DRAFT', 'PLANNED', 'ACTIVE', 'PAUSED', 'COMPLETED', 'ARCHIVED')", name="chk_campaign_status"),
        Index("idx_campaigns_owner_status", "owner_id", "status"),
        Index("idx_campaigns_dates", "start_date", "end_date"),
        # Mỗi request list đều lọc theo `workspace_id IN (...)` qua
        # _apply_tenant_scope. Không có index thì mỗi lần lọc là một full scan
        # trên toàn bộ bảng chiến dịch.
        Index("idx_campaigns_workspace", "workspace_id"),
        Index("idx_campaigns_product", "product_id"),
    )

    workspace = relationship("Workspace", back_populates="campaigns")
    product = relationship("Product", back_populates="campaigns")
    owner = relationship("User", back_populates="campaigns")
    members = relationship("CampaignMember", back_populates="campaign", cascade="all, delete-orphan")
    contents = relationship("MarketingContent", back_populates="campaign", cascade="all, delete-orphan")
    metrics = relationship("CampaignMetric", back_populates="campaign", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="campaign", cascade="all, delete-orphan")
    budget_allocations = relationship("CampaignBudgetAllocation", back_populates="campaign", cascade="all, delete-orphan")
    kpi_targets = relationship("CampaignKPITarget", back_populates="campaign", cascade="all, delete-orphan")
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
    # NULL van con ton tai trong schema de khong pha migration CSDL cu, nhung KHONG con duoc coi la
    # hop le o tang kiem tra quyen: check_content_access / check_workspace_boundary quy tac
    # FAIL-CLOSED, tu choi truy cap khi workspace_id IS NULL. Can migration dan de gan workspace.
    # M4: migration idempotent trong app/core/database.py (_backfill_tenant_workspace_ids,
    # chay tu ensure_sqlite_schema_compatibility) da gan workspace_id cho du lieu legacy tu
    # campaign cha. Con lai NULL => muc do chung va van bi fail-closed o moi endpoint.
    workspace_id = Column(Integer, ForeignKey("workspaces.id", onupdate="CASCADE", ondelete="SET NULL"), nullable=True)
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
    creative_angle = Column(String(50), nullable=True)
    hook_variant = Column(String(50), nullable=True)
    utm_params = Column(String(500), nullable=True)
    ai_metadata_json = Column(Text, nullable=True)
    version_no = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        CheckConstraint("version_no > 0", name="chk_content_version"),
        CheckConstraint("status IN ('DRAFT', 'AI_DRAFT', 'IN_REVIEW', 'APPROVED', 'REJECTED', 'PUBLISHED')", name="chk_content_status"),
        Index("idx_contents_campaign_status", "campaign_id", "status"),
        # Cùng lý do với idx_campaigns_workspace: mọi endpoint list nội dung đều
        # lọc theo workspace trước, rồi mới lọc tiếp theo campaign/status.
        Index("idx_contents_workspace", "workspace_id"),
        Index("idx_contents_channel", "channel_id"),
        Index("idx_contents_status", "status"),
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
    content_id = Column(Integer, ForeignKey("marketing_contents.id", onupdate="CASCADE", ondelete="SET NULL"), nullable=True, index=True)
    metric_date = Column(String(50), nullable=False) # YYYY-MM-DD
    views = Column(Integer, nullable=False, default=0)
    clicks = Column(Integer, nullable=False, default=0)
    conversions = Column(Integer, nullable=False, default=0)
    cost = Column(Numeric(12, 2), nullable=False, default=0)
    revenue = Column(Numeric(12, 2), nullable=False, default=0)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Nguon su that cua dong so lieu. NULL (mac dinh) = nguoi dung hoac ke tich hop
    # nhap vao = DU LIEU THAT. Gia tri 'seed' = dong sinh tu du lieu mau.
    #
    # VI SAO COT NAY: dashboard tong hop views/clicks/ROAS ngay tu bang nay. Neu
    # khong phan biet, mot deployment production chay nham seed se hien "15.700
    # views" nhu la ket qua marketing that, va nguoi mua se hieu sai. Co cot nay
    # thi API bao cao `data_provenance` va UI bat buoc hien thi canh bao, nho do
    # con so lieu mau bao gio duoc nhien nhu la mau chu khong phai so thuc.
    source = Column(String(20), nullable=True, default=None)

    __table_args__ = (
        CheckConstraint("views >= 0", name="chk_views_nonneg"),
        CheckConstraint("clicks >= 0", name="chk_clicks_nonneg"),
        CheckConstraint("conversions >= 0", name="chk_conversions_nonneg"),
        CheckConstraint("cost >= 0", name="chk_cost_nonneg"),
        CheckConstraint("revenue >= 0", name="chk_revenue_nonneg"),
        CheckConstraint("clicks <= views", name="chk_clicks_le_views"),
        UniqueConstraint("campaign_id", "channel_id", "metric_date", name="uq_campaign_channel_date"),
        Index("idx_metrics_campaign_date", "campaign_id", "metric_date"),
        # Tổng hợp theo kênh (dashboard, /campaigns/{id}/attribution) luôn group theo
        # channel_id; index này giúp tránh quét toàn bảng metrics.
        Index("idx_metrics_channel", "channel_id"),
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
    model = Column(String(100), nullable=False, default="gemini-3.8-flash")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        # Phải khớp SUPPORTED_AI_PROVIDERS trong app/core/config.py. Thiếu "opencode"
        # ở đây khiến lưu khóa BYOK cho provider đó chết bằng IntegrityError ở
        # tầng SQLite (HTTP 500), không phải lỗi validation gợi ý được.
        # Phải khớp SUPPORTED_AI_PROVIDERS trong app/core/config.py. Thiếu "opencode"
        # ở đây khiến lưu khóa BYOK cho provider đó bằng IntegrityError từ
        # SQLite (HTTP 500), không phải lỗi validation gợi ý được. Danh sách
        # được sinh từ sổ đăng ký chung `app/services/ai/providers.py` để không
        # thể lệch với validator ở tầng Pydantic.
        CheckConstraint(
            "provider IN (" + ", ".join(f"'{slug}'" for slug in SUPPORTED_PROVIDER_SLUGS) + ")",
            name="chk_api_key_provider",
        ),
        CheckConstraint("user_id IS NOT NULL OR workspace_id IS NOT NULL", name="chk_api_key_owner"),
        Index("idx_custom_keys_user", "user_id", "provider"),
        Index("idx_custom_keys_workspace", "workspace_id", "provider"),
    )

    user = relationship("User", back_populates="custom_api_keys")
    workspace = relationship("Workspace", back_populates="custom_api_keys")


class AIModelChain(Base):
    """Chuỗi model fallback do người dùng đặt tên (kiểu 9Router).

    Một chuỗi là danh sách có thứ tự các bước `(provider, model)`. Khi gọi AI,
    `AIService.execute_task` thử từng bước: bước nào lỗi (timeout, HTTP lỗi,
    sai schema, breaker mở, thiếu API key) thì chuyển bước kế tiếp. Khi hết
    chuỗi mới rơi về Smart Fallback (template) như cũ.

    Không có bảng mới thì không cần migration: `Base.metadata.create_all` tự
    tạo bảng khi khởi động (xem `app/core/database.py:init_db`).
    """

    __tablename__ = "ai_model_chains"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", onupdate="CASCADE", ondelete="CASCADE"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", onupdate="CASCADE", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    # JSON mảng có thứ tự: [{"provider": "openai", "model": "gpt-6.1-sol"}, ...]
    hops_json = Column(Text, nullable=False, default="[]")
    is_active = Column(Boolean, nullable=False, default=True)
    # Chuỗi mặc định được dùng tự động khi request không truyền chain_id.
    is_default = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        # UNIQUE theo (workspace_id, name) KHÔNG khép các hàng workspace_id NULL
        # (chuẩn SQL), nên tên trùng cho chuỗi cá nhân không bị ràng buộc ở DB —
        # tầng API kiểm tra trùng. Cùng lý do với uq_ai_job_user_idempotency.
        CheckConstraint("user_id IS NOT NULL OR workspace_id IS NOT NULL", name="chk_chain_owner"),
        Index("idx_ai_chains_workspace", "workspace_id", "name"),
        Index("idx_ai_chains_user", "user_id", "is_default"),
    )

    user = relationship("User")
    workspace = relationship("Workspace")


class AIJob(Base):
    """Hàng đợi công việc AI bất đồng bộ, LƯU TRONG CHÍNH CSDL (không broker ngoài).

    Vì sao cần bảng này: trước đây mọi endpoint AI là hàm `def` đồng bộ, nên mỗi
    lượt gọi giữ một thread của worker trong suốt thời gian chờ LLM trả lời. Trên
    Render free (512 MB RAM, 0.1 CPU) vài lượt gọi đồng thời là đủ để bộ nhớ cạn
    và bóp chết mọi route API thường; lệnh `/ai/omnichannel` đo được 237 giây.

    Vì sao không Celery/Redis: 512 MB không chịu nổi thêm một tiến trình broker.
    Hàng đợi nằm trong Postgres, worker nền ghi bằng `SELECT ... FOR UPDATE SKIP
    LOCKED` nên nhiều tiến trình có thể dùng chung một hàng đợi mà không chạy trùng.

    Ranh giới tenant: `workspace_id` là BẮT BUỘC cho mọi lần đọc/ghi. Bản ghi có
    `workspace_id IS NULL` bị tầng phân quyền từ chối (fail-closed) — cùng quy tắc
    với `check_workspace_boundary` / `check_content_access` trong
    app/api/v1/contents.py. Không có ngoại lệ "tôi là người tạo nên tôi thấy".
    """

    __tablename__ = "ai_jobs"

    id = Column(Integer, primary_key=True, index=True)
    # Cho phép NULL ở tầng schema (đồng cấu với Campaign/MarketingContent: cột cũ
    # không bị migration phá), nhưng NULL KHÔNG phải là giá trị hợp lệ ở tầng phân
    # quyền — xem app/api/v1/ai_jobs.py (assert_workspace_access).
    workspace_id = Column(Integer, ForeignKey("workspaces.id", onupdate="CASCADE", ondelete="CASCADE"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", onupdate="CASCADE", ondelete="SET NULL"), nullable=True)
    # 'ideas' | 'draft' | 'summary' | 'omnichannel' | 'plan' | 'angle_matrix' | 'prelaunch_critic' | 'deep_doctor' | 'batch_compliance_fix'
    kind = Column(String(30), nullable=False)
    # 'queued' | 'running' | 'succeeded' | 'failed' | 'cancelled'
    status = Column(String(20), nullable=False, default="queued")
    # Payload đã chuẩn hoá (đã bỏ field None) — đây là thứ được đưa vào
    # request model của endpoint đồng bộ khi worker chạy lại tác vụ.
    payload_json = Column(Text, nullable=False, default="{}")
    result_json = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    # Khoá chống gọi trùng (double-click / retry mạng / nút bấm hai lần). Ràng
    # buộc duy nhất đặt theo (user_id, idempotency_key) — KHÔNG theo workspace_id:
    # NULL trong UNIQUE không kẹp nhau ở cả SQLite lẫn Postgres, nên ràng buộc theo
    # workspace sẽ KHÔNG chống được trùng cho job tenant-less.
    idempotency_key = Column(String(200), nullable=True)
    # SHA-256 của (kind + payload chuẩn hoá). Dùng để phát hiện trường hợp tái
    # sử dụng cùng một khoá idempotency với payload KHÁC — lúc đó phải trả 409
    # chứ không được âm thầm trả lại kết quả của lần gọi trước.
    payload_hash = Column(String(64), nullable=True)
    attempts = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=3)
    queued_at = Column(DateTime, nullable=False, default=utc_now)
    # Mốc chờ lần chạy kế tiếp (retry backoff): job 'queued' chỉ được nhặt khi
    # available_at <= now, nên backoff không cần thread ngủ.
    available_at = Column(DateTime, nullable=False, default=utc_now)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        CheckConstraint(
            "kind IN ('ideas', 'draft', 'summary', 'omnichannel', 'plan', 'angle_matrix', 'prelaunch_critic', 'deep_doctor', 'batch_compliance_fix')",
            name="chk_ai_job_kind",
        ),
        CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')",
            name="chk_ai_job_status",
        ),
        CheckConstraint("attempts >= 0", name="chk_ai_job_attempts"),
        CheckConstraint("max_attempts >= 1", name="chk_ai_job_max_attempts"),
        # NULL idempotency_key không kẹp nhau (chuẩn SQL), nên vẫn cho phép enqueue
        # không khoá bao nhiêu lần cũng được.
        UniqueConstraint("user_id", "idempotency_key", name="uq_ai_job_user_idempotency"),
        # Đường quét của worker: status + available_at là điều kiện lọc mỗi vòng.
        Index("idx_ai_jobs_claim", "status", "available_at"),
        Index("idx_ai_jobs_workspace_status", "workspace_id", "status"),
        Index("idx_ai_jobs_user_created", "user_id", "created_at"),
        Index("idx_ai_jobs_kind_status", "kind", "status"),
    )

    workspace = relationship("Workspace", back_populates="ai_jobs")
    user = relationship("User")
    campaign = relationship("Campaign")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", onupdate="CASCADE", ondelete="CASCADE"), nullable=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", onupdate="CASCADE", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(50), nullable=False, default="info") # 'review', 'campaign', 'ai', 'warning', 'info'
    read = Column(Boolean, nullable=False, default=False)
    target_tab = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    __table_args__ = (
        Index("idx_notifications_user_ws", "user_id", "workspace_id", "read"),
        Index("idx_notifications_created", "created_at"),
    )

    user = relationship("User")
    workspace = relationship("Workspace")


class Task(Base):
    __tablename__ = "campaign_tasks"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", onupdate="CASCADE", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", onupdate="CASCADE", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    task_type = Column(String(50), nullable=False, default="OTHER") # CONTENT, DESIGN, VIDEO, ADS, RESEARCH, OTHER
    assignee_id = Column(Integer, ForeignKey("users.id", onupdate="CASCADE", ondelete="SET NULL"), nullable=True, index=True)
    creator_id = Column(Integer, ForeignKey("users.id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    status = Column(String(50), nullable=False, default="TODO") # TODO, IN_PROGRESS, IN_REVIEW, DONE
    priority = Column(String(50), nullable=False, default="MEDIUM") # LOW, MEDIUM, HIGH, URGENT
    due_date = Column(String(50), nullable=True) # YYYY-MM-DD
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        CheckConstraint("task_type IN ('CONTENT', 'DESIGN', 'VIDEO', 'ADS', 'RESEARCH', 'OTHER')", name="chk_task_type"),
        CheckConstraint("status IN ('TODO', 'IN_PROGRESS', 'IN_REVIEW', 'DONE')", name="chk_task_status"),
        CheckConstraint("priority IN ('LOW', 'MEDIUM', 'HIGH', 'URGENT')", name="chk_task_priority"),
        Index("idx_tasks_campaign_status", "campaign_id", "status"),
        Index("idx_tasks_assignee_status", "assignee_id", "status"),
        # Đọc nóng: /tasks/my-tasks lọc theo (assignee, due_date, status) và
        # /tasks/my-tasks/summary quét toàn bộ task của user theo due_date —
        # thiếu composite này thì mỗi lần mở trang "Việc của tôi" là full scan
        # bảng campaign_tasks.
        Index("idx_tasks_assignee_due", "assignee_id", "due_date"),
        Index("idx_tasks_workspace_status", "workspace_id", "status"),
    )

    campaign = relationship("Campaign", back_populates="tasks")
    workspace = relationship("Workspace")
    assignee = relationship("User", foreign_keys=[assignee_id])
    creator = relationship("User", foreign_keys=[creator_id])


class CampaignBudgetAllocation(Base):
    __tablename__ = "campaign_budget_allocations"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", onupdate="CASCADE", ondelete="CASCADE"), nullable=False, index=True)
    channel_id = Column(Integer, ForeignKey("marketing_channels.id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    planned_amount = Column(Numeric(12, 2), nullable=False, default=0)
    # Đánh dấu số AI ước tính: True khi dòng này do AI Campaign Planner sinh ra
    # (POST /campaigns/{id}/plan/apply), False khi người dùng phân bổ tay qua
    # PUT /budget-allocations. Nhờ cột này UI hiện nhãn "Ước tính AI" và người
    # đọc không lẫn số máy đề xuất với số người thật xác nhận.
    is_ai_estimate = Column(Boolean, nullable=False, default=False, server_default="false")
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        CheckConstraint("planned_amount >= 0", name="chk_planned_amount_nonneg"),
        UniqueConstraint("campaign_id", "channel_id", name="uq_campaign_channel_budget"),
        Index("idx_budget_alloc_campaign", "campaign_id"),
    )

    campaign = relationship("Campaign", back_populates="budget_allocations")
    channel = relationship("MarketingChannel")


class CampaignKPITarget(Base):
    __tablename__ = "campaign_kpi_targets"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", onupdate="CASCADE", ondelete="CASCADE"), nullable=False, index=True)
    metric_name = Column(String(50), nullable=False) # 'leads', 'conversions', 'ctr', 'cpl', 'roas', 'revenue'
    target_value = Column(Numeric(12, 2), nullable=False)
    unit = Column(String(20), nullable=True, default="count") # 'count', 'vnd', 'percent', 'ratio'
    # Cùng ý nghĩa với campaign_budget_allocations.is_ai_estimate (xem ở trên).
    is_ai_estimate = Column(Boolean, nullable=False, default=False, server_default="false")
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("campaign_id", "metric_name", name="uq_campaign_metric_target"),
        Index("idx_kpi_target_campaign", "campaign_id"),
    )

    campaign = relationship("Campaign", back_populates="kpi_targets")


class CampaignPlanApplication(Base):
    """Nhật ký áp dụng kế hoạch AI vào chiến dịch (idempotency của plan apply).

    `POST /campaigns/{id}/plan/apply` ghi dòng này TRONG CÙNG transaction với
    phân bổ ngân sách / chỉ tiêu KPI / task mới. Nhờ UNIQUE (campaign_id,
    idempotency_key) ở tầng CSDL, double-click hoặc retry mạng không thể áp
    kế hoạch hai lần dù hai request chạy song song — request thứ hai kẹt ở
    IntegrityError và được xử lý thành `deduplicated=True`.

    `plan_hash` (SHA-256 của payload chuẩn hoá) phân biệt "gửi lại cùng khoá
    với cùng kế hoạch" (200, dedup) khỏi "dùng nhầm khoá của kế hoạch khác"
    (409) — tái sử dụng khoá im lặng sẽ trả kết quả của kế hoạch cũ mà người
    dùng không hề biết.
    """

    __tablename__ = "campaign_plan_applications"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", onupdate="CASCADE", ondelete="CASCADE"), nullable=False, index=True)
    idempotency_key = Column(String(200), nullable=False)
    plan_hash = Column(String(64), nullable=False)
    # Snapshot JSON của kế hoạch đã áp — dùng cho audit ("lúc đó AI đề xuất gì").
    plan_json = Column(Text, nullable=False, default="{}")
    applied_by = Column(Integer, ForeignKey("users.id", onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=utc_now)

    __table_args__ = (
        UniqueConstraint("campaign_id", "idempotency_key", name="uq_campaign_plan_app_key"),
        Index("idx_plan_app_campaign", "campaign_id"),
    )

    campaign = relationship("Campaign")


class AdAccount(Base):
    """Tài khoản quảng cáo (Meta BM / TikTok BC / Google MCC) & nguồn đơn hàng POS (Pancake/Sapo)."""

    __tablename__ = "ad_accounts"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", onupdate="CASCADE", ondelete="CASCADE"), nullable=False, index=True)
    platform = Column(String(50), nullable=False, default="META_ADS")
    account_code = Column(String(100), nullable=False)
    account_name = Column(String(255), nullable=False)
    pixel_id = Column(String(100), nullable=True)
    daily_spend_cap = Column(Numeric(12, 2), nullable=False, default=15000000)
    today_spend = Column(Numeric(12, 2), nullable=False, default=0)
    status = Column(String(50), nullable=False, default="ACTIVE")
    linked_campaign_id = Column(Integer, ForeignKey("campaigns.id", onupdate="CASCADE", ondelete="SET NULL"), nullable=True, index=True)
    access_token_masked = Column(String(255), nullable=True)
    last_synced_at = Column(DateTime, nullable=True, default=utc_now)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        CheckConstraint("platform IN ('META_ADS', 'TIKTOK_ADS', 'GOOGLE_ADS', 'POS_SYSTEM')", name="chk_ad_account_platform"),
        CheckConstraint("status IN ('ACTIVE', 'SPEND_WARNING', 'RESTRICTED')", name="chk_ad_account_status"),
        Index("idx_ad_accounts_workspace", "workspace_id", "platform"),
    )

    workspace = relationship("Workspace")
    linked_campaign = relationship("Campaign")


class KolBooking(Base):
    """Quản lý thuê KOL / KOC / Affiliate bên thứ 3 (TikTok Shop, Facebook Reels, YouTube, Instagram)
    kèm mã theo dõi UTM / Voucher riêng để đo lường chính xác Chi phí cát-xê + Hoa hồng so với Doanh thu ra đơn.
    """

    __tablename__ = "kol_bookings"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", onupdate="CASCADE", ondelete="CASCADE"), nullable=False, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", onupdate="CASCADE", ondelete="CASCADE"), nullable=False, index=True)
    creator_name = Column(String(255), nullable=False)
    handle = Column(String(120), nullable=False)
    platform = Column(String(50), nullable=False, default="TIKTOK")
    followers_tier = Column(String(60), nullable=False, default="Micro KOC (50K - 200K)")
    tracking_code = Column(String(100), nullable=False, index=True)
    booking_cost = Column(Numeric(12, 2), nullable=False, default=0)
    commission_pct = Column(Numeric(5, 2), nullable=False, default=10.0)
    views_count = Column(Integer, nullable=False, default=0)
    clicks_count = Column(Integer, nullable=False, default=0)
    orders_count = Column(Integer, nullable=False, default=0)
    revenue_generated = Column(Numeric(12, 2), nullable=False, default=0)
    video_or_post_url = Column(String(500), nullable=True)
    status = Column(String(50), nullable=False, default="AIRING")
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        CheckConstraint("platform IN ('TIKTOK', 'FACEBOOK', 'INSTAGRAM', 'YOUTUBE')", name="chk_kol_platform"),
        CheckConstraint("status IN ('NEGOTIATING', 'BOOKED', 'AIRING', 'COMPLETED')", name="chk_kol_status"),
        Index("idx_kol_bookings_ws_camp", "workspace_id", "campaign_id"),
    )

    workspace = relationship("Workspace")
    campaign = relationship("Campaign")


class WorkspaceSubscription(Base):
    """Gói cước SaaS của Workspace (FREE / PRO / AGENCY), cấu hình VietQR / SePay,
    khóa bảo mật POS Webhook (webhook_secret_key), cấu hình Zalo ZNS / Email thật
    và chế độ Làm sạch dữ liệu mẫu (clean_demo_mode).
    """

    __tablename__ = "workspace_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(
        Integer,
        ForeignKey("workspaces.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    plan_tier = Column(String(30), nullable=False, default="FREE")
    billing_cycle = Column(String(30), nullable=False, default="MONTHLY")
    amount_vnd = Column(Numeric(12, 2), nullable=False, default=0)
    payment_ref = Column(String(120), nullable=True)
    payment_provider = Column(String(50), nullable=False, default="VIETQR_SEPAY")
    webhook_secret_key = Column(String(120), nullable=False, default="mf_pos_live_vn2026")
    zalo_oa_token = Column(String(255), nullable=True)
    smtp_or_resend_key = Column(String(255), nullable=True)
    alert_email = Column(String(255), nullable=True)
    clean_demo_mode = Column(Boolean, nullable=False, default=False)
    activated_at = Column(DateTime, nullable=True, default=utc_now)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        CheckConstraint("plan_tier IN ('FREE', 'PRO', 'AGENCY')", name="chk_ws_sub_tier"),
        CheckConstraint("billing_cycle IN ('MONTHLY', 'YEARLY')", name="chk_ws_sub_cycle"),
        Index("idx_ws_sub_workspace_tier", "workspace_id", "plan_tier"),
    )

    workspace = relationship("Workspace")


class VnLeadCrm(Base):
    """Phễu khách hàng tiềm năng (Conversational Commerce Việt Nam: Zalo OA / ZNS,
    Facebook Messenger Click-to-Chat, TikTok Bio, Landing Form) giúp chống rớt khách
    trong khung 24h của Meta và tự động nhắc lịch chuyển khoản / lương về 15-25.
    """

    __tablename__ = "vn_lead_crm"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(
        Integer,
        ForeignKey("workspaces.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    campaign_id = Column(
        Integer,
        ForeignKey("campaigns.id", onupdate="CASCADE", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    customer_name = Column(String(255), nullable=False)
    phone = Column(String(40), nullable=False)
    source_channel = Column(String(50), nullable=False, default="FB_MESSENGER")
    lead_stage = Column(String(50), nullable=False, default="NEW_INBOX")
    product_interest = Column(String(255), nullable=False, default="Combo Sản phẩm Chủ lực")
    estimated_value = Column(Numeric(12, 2), nullable=False, default=450000)
    zns_sent_count = Column(Integer, nullable=False, default=0)
    last_message_note = Column(Text, nullable=True)
    assigned_sale = Column(String(120), nullable=True, default="Sale Ca Sáng")
    last_contacted_at = Column(DateTime, nullable=False, default=utc_now)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        CheckConstraint(
            "source_channel IN ('FB_MESSENGER', 'ZALO_OA', 'TIKTOK_BIO', 'LANDING_FORM')",
            name="chk_vn_lead_source",
        ),
        CheckConstraint(
            "lead_stage IN ('NEW_INBOX', 'SILENT_24H', 'WAITING_TRANSFER', 'PAYDAY_15_25', 'CLOSED_POS')",
            name="chk_vn_lead_stage",
        ),
        Index("idx_vn_lead_ws_stage", "workspace_id", "lead_stage"),
    )

    workspace = relationship("Workspace")
    campaign = relationship("Campaign")


