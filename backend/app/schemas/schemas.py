from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, model_validator, field_validator, ConfigDict

# --- AUTH & USER ---
class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    role: str = Field(..., pattern="^(MANAGER|MARKETER)$")

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class UserResponse(UserBase):
    id: int
    status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# --- PRODUCT & CHANNEL ---
class ProductCategoryResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class ProductResponse(BaseModel):
    id: int
    category_id: int
    name: str
    description: Optional[str] = None
    usp: Optional[str] = None
    status: str
    model_config = ConfigDict(from_attributes=True)

class ChannelResponse(BaseModel):
    id: int
    code: str
    name: str
    format_rules: Optional[str] = None
    status: str
    model_config = ConfigDict(from_attributes=True)

# --- CAMPAIGN ---
class CampaignBase(BaseModel):
    product_id: int
    name: str = Field(..., min_length=3, max_length=255)
    objective: str
    audience: str
    start_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$") # YYYY-MM-DD
    end_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")   # YYYY-MM-DD
    budget: float = Field(0.0, ge=0.0)

    @field_validator("start_date", "end_date")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"Ngày không hợp lệ: '{v}'. Định dạng yêu cầu là YYYY-MM-DD.")
        return v

    @model_validator(mode="after")
    def validate_dates(self):
        if self.end_date < self.start_date:
            raise ValueError("Ngày kết thúc (end_date) không được nhỏ hơn ngày bắt đầu (start_date)")
        return self

class CampaignCreate(CampaignBase):
    pass

class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    objective: Optional[str] = None
    audience: Optional[str] = None
    start_date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    end_date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    budget: Optional[float] = Field(None, ge=0.0)
    status: Optional[str] = Field(None, pattern="^(DRAFT|PLANNED|ACTIVE|PAUSED|COMPLETED|ARCHIVED)$")

    @field_validator("start_date", "end_date")
    @classmethod
    def validate_date_format(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            try:
                datetime.strptime(v, "%Y-%m-%d")
            except ValueError:
                raise ValueError(f"Ngày không hợp lệ: '{v}'. Định dạng yêu cầu là YYYY-MM-DD.")
        return v

    @model_validator(mode="after")
    def validate_dates(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("Ngày kết thúc (end_date) không được nhỏ hơn ngày bắt đầu (start_date)")
        return self

class CampaignResponse(CampaignBase):
    id: int
    owner_id: int
    status: str
    created_at: datetime
    updated_at: datetime
    owner: Optional[UserResponse] = None
    product: Optional[ProductResponse] = None
    model_config = ConfigDict(from_attributes=True)

# --- MARKETING CONTENT ---
class ContentCreate(BaseModel):
    campaign_id: int
    channel_id: int
    title: str = Field(..., min_length=1, max_length=255)
    body: str = Field(..., min_length=1)
    cta: Optional[str] = None
    status: Optional[str] = Field("DRAFT", pattern="^(DRAFT|AI_DRAFT|IN_REVIEW|APPROVED|REJECTED|PUBLISHED)$")

class ContentUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    cta: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(DRAFT|AI_DRAFT|IN_REVIEW|APPROVED|REJECTED|PUBLISHED)$")

class ContentResponse(BaseModel):
    id: int
    campaign_id: int
    channel_id: int
    created_by: int
    title: str
    body: str
    cta: Optional[str] = None
    status: str
    version_no: int
    source_ids_json: str
    warnings_json: str
    created_at: datetime
    updated_at: datetime
    creator: Optional[UserResponse] = None
    channel: Optional[ChannelResponse] = None
    model_config = ConfigDict(from_attributes=True)

# --- CONTENT REVIEW ---
class ReviewCreate(BaseModel):
    decision: str = Field(..., pattern="^(APPROVED|REJECTED|REQUEST_CHANGES)$")
    reason: str = Field(..., min_length=3)

class ReviewResponse(BaseModel):
    id: int
    content_id: int
    reviewer_id: int
    decision: str
    reason: str
    created_at: datetime
    reviewer: Optional[UserResponse] = None
    model_config = ConfigDict(from_attributes=True)

# --- MARKETING SCHEDULE ---
class ScheduleCreate(BaseModel):
    content_id: int
    scheduled_at: str # YYYY-MM-DD HH:MM
    timezone: str = "Asia/Ho_Chi_Minh"

class ScheduleResponse(BaseModel):
    id: int
    content_id: int
    scheduled_at: str
    timezone: str
    status: str
    created_by: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# --- METRICS & KPI ---
class MetricCreate(BaseModel):
    campaign_id: int
    channel_id: int
    metric_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$") # YYYY-MM-DD
    views: int = Field(0, ge=0)
    clicks: int = Field(0, ge=0)
    conversions: int = Field(0, ge=0)
    cost: float = Field(0.0, ge=0.0)
    revenue: float = Field(0.0, ge=0.0)

    @field_validator("metric_date")
    @classmethod
    def validate_metric_date(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"Ngày không hợp lệ: '{v}'. Định dạng yêu cầu là YYYY-MM-DD.")
        return v

    @model_validator(mode="after")
    def validate_clicks_views(self):
        if self.clicks > self.views:
            raise ValueError(f"Lượt click ({self.clicks}) không được lớn hơn lượt view ({self.views})")
        return self

class MetricResponse(MetricCreate):
    id: int
    created_at: datetime
    channel: Optional[ChannelResponse] = None
    model_config = ConfigDict(from_attributes=True)

class KPISummaryResponse(BaseModel):
    total_views: int
    total_clicks: int
    total_conversions: int
    total_cost: float
    total_revenue: float
    ctr_percent: float # (clicks / views) * 100
    cpc_avg: float     # cost / clicks
    cvr_percent: float # (conversions / clicks) * 100
    roi_percent: float # ((revenue - cost) / cost) * 100

# --- AI CONTRACTS ---
class AIIdeaRequest(BaseModel):
    campaign_id: Optional[int] = None
    custom_topic: Optional[str] = None
    custom_product: Optional[str] = None
    custom_usp: Optional[str] = None
    channel_code: str = "facebook"
    tone: str = "trẻ trung, năng động"
    prompt_version: str = "v3"

class AIIdeaItem(BaseModel):
    id: int
    angle: str
    headline: str
    concept: str
    target_emotion: str

class AIIdeaResponse(BaseModel):
    task_type: str = "IDEA"
    ideas: List[AIIdeaItem]
    warnings: List[str] = []
    assumptions: List[str] = []
    model_used: str
    prompt_version: str

class AIDraftRequest(BaseModel):
    campaign_id: Optional[int] = None
    custom_product: Optional[str] = None
    custom_usp: Optional[str] = None
    channel_code: str = "facebook"
    selected_idea: str
    prompt_version: str = "v3"

class AIDraftResponse(BaseModel):
    task_type: str = "DRAFT"
    title: str
    body: str
    cta: str
    warnings: List[str] = []
    assumptions: List[str] = []
    model_used: str
    prompt_version: str

class AISummaryRequest(BaseModel):
    campaign_id: int
    prompt_version: str = "v3"

class AISummaryResponse(BaseModel):
    task_type: str = "SUMMARY"
    executive_summary: str
    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[str]
    warnings: List[str] = []
    model_used: str
    prompt_version: str
