import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, model_validator, field_validator, ConfigDict, ValidationInfo

# --- AUTH & USER ---
class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    role: str = Field(..., pattern="^(MANAGER|MARKETER|AGENCY_MANAGER|CLIENT_APPROVER|ADMIN)$")

class UserRegister(BaseModel):
    email: EmailStr = Field(..., description="Email đăng ký duy nhất")
    password: str = Field(..., min_length=6, max_length=128, description="Mật khẩu tối thiểu 6 ký tự")
    full_name: str = Field(..., min_length=2, max_length=255, description="Họ và tên người dùng")
    role: Optional[str] = Field(
        "MARKETER", 
        pattern="^(MARKETER|AGENCY_MANAGER|CLIENT_APPROVER|ADMIN|MANAGER)$",
        description="Vai trò công khai mặc định là MARKETER (các vai trò đặc quyền bị từ chối 403 tại endpoint)"
    )

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.lower().strip()

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

# --- WORKSPACE & MEMBERSHIP ---
class WorkspaceBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255, description="Tên không gian làm việc hoặc thương hiệu khách hàng")
    description: Optional[str] = Field(None, max_length=1000, description="Mô tả mục tiêu của không gian làm việc")

    @field_validator("name")
    @classmethod
    def validate_name_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Tên Workspace không được để trống hoặc chỉ chứa khoảng trắng")
        return v.strip()

class WorkspaceCreate(WorkspaceBase):
    slug: Optional[str] = Field(
        None, 
        max_length=255, 
        pattern=r"^[a-z0-9-]+$", 
        description="Slug định danh URL duy nhất. Nếu bỏ trống sẽ tự sinh từ name."
    )

class WorkspaceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)

    @field_validator("name")
    @classmethod
    def validate_name_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v.strip():
                raise ValueError("Tên Workspace không được để trống hoặc chỉ chứa khoảng trắng")
            return v.strip()
        return v

class WorkspaceMemberAdd(BaseModel):
    email: EmailStr = Field(..., description="Email người dùng cần thêm vào Workspace")
    role: str = Field(
        "MARKETER", 
        pattern="^(AGENCY_MANAGER|MARKETER|CLIENT_APPROVER|MANAGER)$",
        description="Vai trò trong workspace"
    )

class WorkspaceMemberResponse(BaseModel):
    id: Optional[int] = None
    workspace_id: int
    user_id: int
    role: str
    joined_at: datetime
    user: Optional[UserResponse] = None
    model_config = ConfigDict(from_attributes=True)

class WorkspaceResponse(WorkspaceBase):
    id: int
    slug: str
    owner_id: int
    status: str = "ACTIVE"
    created_at: datetime
    updated_at: datetime
    owner: Optional[UserResponse] = None
    model_config = ConfigDict(from_attributes=True)

# --- BRAND KIT ---
class BrandKitBase(BaseModel):
    brand_name: str = Field(..., min_length=2, max_length=255, description="Tên thương hiệu")
    usp: Optional[str] = Field(None, description="Lợi thế bán hàng độc nhất / Định vị sản phẩm")
    tone_of_voice: Optional[str] = Field("Chuyên nghiệp, hiện đại", max_length=255, description="Giọng văn nhận diện thương hiệu")
    banned_keywords: List[str] = Field(
        default_factory=list, 
        description="Danh sách từ khóa cấm kỵ, vi phạm chính sách quảng cáo"
    )

class BrandKitCreate(BrandKitBase):
    workspace_id: int = Field(..., description="ID Workspace sở hữu Brand Kit")

class BrandKitUpdate(BaseModel):
    workspace_id: Optional[int] = None
    brand_name: Optional[str] = Field(None, min_length=2, max_length=255)
    usp: Optional[str] = None
    tone_of_voice: Optional[str] = Field(None, max_length=255)
    banned_keywords: Optional[List[str]] = None

class BrandKitResponse(BrandKitBase):
    id: int
    workspace_id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def resolve_banned_keywords(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "banned_keywords" not in data and "banned_keywords_json" in data:
                raw = data.get("banned_keywords_json") or "[]"
                try:
                    data["banned_keywords"] = json.loads(raw) if isinstance(raw, str) else (raw or [])
                except Exception:
                    data["banned_keywords"] = []
            return data
        if hasattr(data, "banned_keywords_json"):
            raw = getattr(data, "banned_keywords_json", "[]")
            try:
                banned_list = json.loads(raw) if isinstance(raw, str) else (raw or [])
            except Exception:
                banned_list = []
            return {
                "id": getattr(data, "id"),
                "workspace_id": getattr(data, "workspace_id"),
                "brand_name": getattr(data, "brand_name"),
                "usp": getattr(data, "usp"),
                "tone_of_voice": getattr(data, "tone_of_voice"),
                "banned_keywords": banned_list,
                "created_at": getattr(data, "created_at"),
                "updated_at": getattr(data, "updated_at"),
            }
        return data



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
    workspace_id: Optional[int] = None
    name: str = Field(..., min_length=3, max_length=255)
    objective: str
    audience: str
    start_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$") # YYYY-MM-DD
    end_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")   # YYYY-MM-DD
    budget: float = Field(0.0, ge=0.0)
    key_message: Optional[str] = None
    primary_cta: Optional[str] = None
    target_kpi_name: Optional[str] = None
    target_kpi_value: Optional[float] = None

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
    key_message: Optional[str] = None
    primary_cta: Optional[str] = None
    target_kpi_name: Optional[str] = None
    target_kpi_value: Optional[float] = None

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

# --- BUDGET ALLOCATION ---
class BudgetAllocationBase(BaseModel):
    channel_id: int
    planned_amount: float = Field(..., ge=0.0)

class BudgetAllocationCreate(BudgetAllocationBase):
    pass

class BudgetAllocationResponse(BudgetAllocationBase):
    id: int
    campaign_id: int
    channel: Optional[ChannelResponse] = None
    model_config = ConfigDict(from_attributes=True)

# --- KPI TARGET ---
class KPITargetBase(BaseModel):
    metric_name: str = Field(..., min_length=1, max_length=100)
    target_value: float = Field(..., ge=0.0)
    unit: str = Field("%", max_length=50)

class KPITargetCreate(KPITargetBase):
    pass

class KPITargetResponse(KPITargetBase):
    id: int
    campaign_id: int
    model_config = ConfigDict(from_attributes=True)

class CampaignResponse(CampaignBase):
    id: int
    owner_id: int
    status: str
    created_at: datetime
    updated_at: datetime
    owner: Optional[UserResponse] = None
    product: Optional[ProductResponse] = None
    budget_allocations: Optional[List[BudgetAllocationResponse]] = None
    kpi_targets: Optional[List[KPITargetResponse]] = None
    model_config = ConfigDict(from_attributes=True)

# --- CAMPAIGN TASKS ---
class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    task_type: str = Field("OTHER", pattern="^(CONTENT|DESIGN|VIDEO|ADS|RESEARCH|OTHER)$")
    assignee_id: Optional[int] = None
    status: str = Field("TODO", pattern="^(TODO|IN_PROGRESS|IN_REVIEW|DONE)$")
    priority: str = Field("MEDIUM", pattern="^(LOW|MEDIUM|HIGH|URGENT)$")
    due_date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")

    @field_validator("due_date")
    @classmethod
    def validate_date(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            try:
                datetime.strptime(v, "%Y-%m-%d")
            except ValueError:
                raise ValueError(f"Ngày không hợp lệ: '{v}'. Định dạng yêu cầu là YYYY-MM-DD.")
        return v

class TaskCreate(TaskBase):
    campaign_id: int
    workspace_id: Optional[int] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    task_type: Optional[str] = Field(None, pattern="^(CONTENT|DESIGN|VIDEO|ADS|RESEARCH|OTHER)$")
    assignee_id: Optional[int] = None
    status: Optional[str] = Field(None, pattern="^(TODO|IN_PROGRESS|IN_REVIEW|DONE)$")
    priority: Optional[str] = Field(None, pattern="^(LOW|MEDIUM|HIGH|URGENT)$")
    due_date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")


    @field_validator("due_date")
    @classmethod
    def validate_date(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            try:
                datetime.strptime(v, "%Y-%m-%d")
            except ValueError:
                raise ValueError(f"Ngày không hợp lệ: '{v}'. Định dạng yêu cầu là YYYY-MM-DD.")
        return v

class TaskResponse(TaskBase):
    id: int
    campaign_id: int
    workspace_id: int
    creator_id: int
    created_at: datetime
    updated_at: datetime
    assignee: Optional[UserResponse] = None
    creator: Optional[UserResponse] = None
    campaign: Optional[CampaignResponse] = None
    model_config = ConfigDict(from_attributes=True)

class CampaignDetailResponse(CampaignResponse):
    tasks: Optional[List[TaskResponse]] = None

# --- MARKETING CONTENT ---
class ContentCreate(BaseModel):
    campaign_id: int
    channel_id: int
    workspace_id: Optional[int] = None
    title: str = Field(..., min_length=1, max_length=255)
    body: str = Field(..., min_length=1)
    cta: Optional[str] = None
    image_url: Optional[str] = Field(None, max_length=1024, description="URL ảnh sản phẩm hoặc banner chiến dịch")
    status: Optional[str] = Field("DRAFT", pattern="^(DRAFT|AI_DRAFT|IN_REVIEW|APPROVED|REJECTED|PUBLISHED)$")
    warnings_json: Optional[str] = None

    @field_validator("image_url")
    @classmethod
    def validate_image_url(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        lower_v = v.lower()
        if lower_v.startswith(("javascript:", "vbscript:", "data:text/html")):
            raise ValueError("URL hình ảnh không an toàn hoặc chứa giao thức nguy hiểm")
        return v

class ContentUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    cta: Optional[str] = None
    image_url: Optional[str] = Field(None, max_length=1024, description="URL hình ảnh sản phẩm/banner mới (hoặc chuỗi rỗng để gỡ ảnh)")
    # status KHONG duoc cap nhat qua PUT. Moi chuyen trang thai phai qua cac endpoint chuyen trang thai: /submit, /approve, /reject, /publish.
    warnings_json: Optional[str] = None

    # extra="allow": giu lai truong "status" do client gui len de endpoint PUT co the
    # tu choi ro rang bang HTTP 400 thay vi bo qua im lang. Endpoint chi doc cac
    # thuoc tinh khai bao o tren, truong extra khong bao gio duoc gan vao model.
    model_config = ConfigDict(extra="allow")

    @field_validator("image_url")
    @classmethod
    def validate_image_url(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if not v:
            return ""
        lower_v = v.lower()
        if lower_v.startswith(("javascript:", "vbscript:", "data:text/html")):
            raise ValueError("URL hình ảnh không an toàn hoặc chứa giao thức nguy hiểm")
        return v

class ContentResponse(BaseModel):
    id: int
    workspace_id: Optional[int] = None
    campaign_id: int
    channel_id: int
    created_by: int
    title: str
    body: str
    cta: Optional[str] = None
    image_url: Optional[str] = None
    status: str
    version_no: int
    source_ids_json: str
    warnings_json: Optional[str] = "[]"

    created_at: datetime
    updated_at: datetime
    creator: Optional[UserResponse] = None
    channel: Optional[ChannelResponse] = None
    model_config = ConfigDict(from_attributes=True)

# --- COMPLIANCE GUARDRAIL & BRAND SAFETY (M3) ---
class ViolationItem(BaseModel):
    category: str = Field(..., description="'AD_POLICY' | 'BRAND_BANNED'")
    severity: str = Field(..., description="'HIGH' | 'MEDIUM' | 'LOW'")
    word: str = Field(..., description="Từ khóa vi phạm được phát hiện")
    suggestion: str = Field(..., description="Đề xuất diễn đạt thay thế an toàn")

class ComplianceCheckRequest(BaseModel):
    workspace_id: Optional[int] = Field(None, description="ID Workspace chứa cấu hình Brand Kit")
    channel: Optional[str] = Field("facebook", description="Kênh truyền thông")
    title: Optional[str] = Field("", description="Tiêu đề nội dung cần quét")
    body: Optional[str] = Field("", description="Thân bài viết cần quét")
    cta: Optional[str] = Field(None, description="Lời kêu gọi hành động (tuỳ chọn)")

class ComplianceCheckResponse(BaseModel):
    status: str = Field(..., description="'PASSED' | 'WARNING' | 'VIOLATION'")
    score: int = Field(100, ge=0, le=100, description="Điểm đánh giá tuân thủ (0-100)")
    can_submit: bool = Field(True, description="True nếu không có vi phạm mức độ HIGH")
    violations: List[ViolationItem] = Field(default_factory=list, description="Danh sách chi tiết các vi phạm phát hiện")

# --- CONTENT REVIEW ---
class ReviewCreate(BaseModel):
    decision: str = Field(..., pattern="^(APPROVED|REJECTED|REQUEST_CHANGES)$")
    reason: Optional[str] = Field(None, min_length=3, description="Lý do phê duyệt hoặc từ chối (tối thiểu 3 ký tự)")

    @field_validator("reason")
    @classmethod
    def validate_reason_not_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            clean = v.strip()
            if not clean:
                raise ValueError("Lý do từ chối không được để trống hoặc chỉ chứa khoảng trắng")
            if len(clean) < 3:
                raise ValueError("Lý do từ chối quá ngắn (tối thiểu 3 ký tự)")
            return clean
        return v

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
    content_id: Optional[int] = None
    scheduled_at: str # YYYY-MM-DD HH:MM
    timezone: str = "Asia/Ho_Chi_Minh"

class ScheduleUpdate(BaseModel):
    scheduled_at: Optional[str] = Field(None, description="Thời gian hẹn đăng mới (YYYY-MM-DD HH:MM hoặc ISO)")
    timezone: Optional[str] = Field("Asia/Ho_Chi_Minh", description="Múi giờ đăng bài")

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

class ChannelAttributionResponse(BaseModel):
    channel_id: int
    channel_name: str
    channel_slug: str = ""
    channel_code: Optional[str] = None
    views: int = 0
    clicks: int = 0
    conversions: int = 0
    cost: float = 0.0
    revenue: float = 0.0
    ctr_percent: float = 0.0
    cpc_avg: float = 0.0
    cvr_percent: float = 0.0
    roas: float = 0.0
    roi_percent: float = 0.0
    share_of_cost: float = 0.0
    share_of_revenue: float = 0.0
    model_config = ConfigDict(from_attributes=True)

class AIDoctorRecommendation(BaseModel):
    action: str = Field(..., description="SCALE | REDUCE | OPTIMIZE | PAUSE")
    channel: Optional[str] = "all"
    reason: str
    suggestion: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    impact: Optional[str] = None

class AIDoctorBottleneck(BaseModel):
    category: Optional[str] = "METRIC"
    severity: str = Field(..., description="HIGH | MEDIUM | LOW")
    channel: Optional[str] = None
    metric_name: Optional[str] = None
    current_value: Optional[float] = None
    benchmark_value: Optional[float] = None
    description: str

class AIDoctorResponse(BaseModel):
    campaign_id: Optional[int] = None
    campaign_name: Optional[str] = None
    health_status: str = Field(..., description="HEALTHY | NEEDS_ATTENTION | CRITICAL")
    health_score: int = Field(..., ge=0, le=100)
    diagnosis_summary: str
    key_bottlenecks: List[str] = Field(default_factory=list)
    bottlenecks: List[str] = Field(default_factory=list)  # Hỗ trợ cả 2 tên trường cho các test assertion
    recommendations: List[AIDoctorRecommendation] = Field(default_factory=list)
    metrics_analyzed: Optional[Dict[str, Any]] = None
    channel_breakdown: Optional[List[ChannelAttributionResponse]] = Field(default_factory=list)
    is_sparse_data: bool = False
    generated_at: Optional[str] = None
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
    cpa_avg: float = Field(0.0, description="Cost Per Acquisition = total_cost / total_conversions")
    roi_percent: float # ((revenue - cost) / cost) * 100
    roas: float = Field(0.0, description="Return on Ad Spend = revenue / cost")
    channel_metrics: Optional[List[ChannelAttributionResponse]] = Field(default_factory=list)
    channel_breakdown: Optional[List[Dict[str, Any]]] = None

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
    is_fallback: bool = False
    model_provider: Optional[str] = None

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
    is_fallback: bool = False
    model_provider: Optional[str] = None

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
    is_fallback: bool = False
    model_provider: Optional[str] = None


# ==============================================================================
# R2: OMNICHANNEL CREATIVE ENGINE SCHEMAS (GOLDEN SPECIFICATION)
# ==============================================================================

class FacebookCreative(BaseModel):
    title: str = Field(..., min_length=1, description="Tiêu đề bài viết Facebook (hoặc Headline)")
    body: str = Field(..., min_length=1, description="Thân bài ngắt nhịp kích thích tương tác (hoặc Primary Text)")
    cta: str = Field(..., min_length=1, description="Lời kêu gọi hành động cụ thể")
    hashtags: List[str] = Field(default_factory=list, description="Danh sách hashtag tối ưu phân phối")
    headline: Optional[str] = None
    primary_text: Optional[str] = None
    visual_suggestion: Optional[str] = Field(None, description="Gợi ý hình ảnh hoặc banner minh họa")

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def sync_facebook_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "title" not in data and "headline" in data:
                data["title"] = data["headline"]
            elif "headline" not in data and "title" in data:
                data["headline"] = data["title"]
            if "body" not in data and "primary_text" in data:
                data["body"] = data["primary_text"]
            elif "primary_text" not in data and "body" in data:
                data["primary_text"] = data["body"]
        return data


class TikTokScene(BaseModel):
    scene: int = Field(1, description="Số thứ tự phân cảnh (1, 2, 3, ...)")
    scene_number: Optional[int] = None
    duration_seconds: Optional[str] = Field("0-10s", description="Thời lượng cảnh")
    visual: str = Field(..., min_length=1, description="Mô tả hành động của diễn viên và góc máy quay (Visual Action)")
    visual_action: Optional[str] = None
    voiceover: str = Field(..., min_length=1, description="Lời thoại nhân vật hoặc thuyết minh chi tiết (Voiceover Script)")
    voiceover_script: Optional[str] = None
    audio: Optional[str] = Field("", description="Gợi ý âm thanh hiệu ứng SFX hoặc beat nhạc (Audio Hint)")
    audio_hint: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def sync_scene_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "scene" not in data and "scene_number" in data:
                data["scene"] = data["scene_number"]
            elif "scene_number" not in data and "scene" in data:
                data["scene_number"] = data["scene"]
            if "visual" not in data and "visual_action" in data:
                data["visual"] = data["visual_action"]
            elif "visual_action" not in data and "visual" in data:
                data["visual_action"] = data["visual"]
            if "voiceover" not in data and "voiceover_script" in data:
                data["voiceover"] = data["voiceover_script"]
            elif "voiceover_script" not in data and "voiceover" in data:
                data["voiceover_script"] = data["voiceover"]
            if "audio" not in data and "audio_hint" in data:
                data["audio"] = data["audio_hint"]
            elif "audio_hint" not in data and "audio" in data:
                data["audio_hint"] = data.get("audio", "")
        return data


class TikTokCreative(BaseModel):
    hook_3s: str = Field(..., min_length=1, description="Hook 3 giây đầu giữ chân người xem")
    target_duration: str = Field("30-45 giây", description="Tổng thời lượng video ước tính")
    scenes: List[TikTokScene] = Field(default_factory=list, description="Danh sách phân cảnh chi tiết")
    suggested_audio: str = Field(..., min_length=1, description="Gợi ý bài nhạc nền thịnh hành (Trending Sound)")
    sound_recommendation: Optional[str] = None
    caption_with_hashtags: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def sync_tiktok_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "suggested_audio" not in data and "sound_recommendation" in data:
                data["suggested_audio"] = data["sound_recommendation"]
            elif "sound_recommendation" not in data and "suggested_audio" in data:
                data["sound_recommendation"] = data["suggested_audio"]
            if "caption_with_hashtags" not in data:
                hook = data.get("hook_3s", "")
                data["caption_with_hashtags"] = f"{hook} #TikTokMarketing #ViralVideo"
        return data


class EmailCreative(BaseModel):
    subject_options: List[str] = Field(default_factory=list, description="Danh sách tiêu đề A/B Testing")
    subject_line_a: Optional[str] = None
    subject_line_b: Optional[str] = None
    preheader: Optional[str] = Field(None, description="Đoạn xem trước hiển thị trong hộp thư đến (Preheader)")
    greeting: Optional[str] = Field(None, description="Lời chào cá nhân hóa")
    body: str = Field(..., min_length=1, description="Thân bài email nuôi dưỡng và bán hàng có cấu trúc")
    body_content: Optional[str] = None
    cta_button: str = Field(..., min_length=1, description="Nội dung nút kêu gọi hành động chuyển đổi cao")
    cta_button_text: Optional[str] = None
    cta_destination_type: Optional[str] = "Landing Page"
    ps_note: Optional[str] = Field(None, description="Tái bút (P.S.) tăng tỷ lệ chuyển đổi")

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def sync_email_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "body" not in data and "body_content" in data:
                data["body"] = data["body_content"]
            elif "body_content" not in data and "body" in data:
                data["body_content"] = data["body"]
            if "cta_button" not in data and "cta_button_text" in data:
                data["cta_button"] = data["cta_button_text"]
            elif "cta_button_text" not in data and "cta_button" in data:
                data["cta_button_text"] = data["cta_button"]
            opts = data.get("subject_options", [])
            if opts and len(opts) >= 2:
                if not data.get("subject_line_a"):
                    data["subject_line_a"] = opts[0]
                if not data.get("subject_line_b"):
                    data["subject_line_b"] = opts[1]
            elif opts and len(opts) == 1:
                if not data.get("subject_line_a"):
                    data["subject_line_a"] = opts[0]
            elif not opts:
                sa = data.get("subject_line_a", "Ưu đãi đặc quyền dành riêng cho bạn")
                sb = data.get("subject_line_b", "[Khám phá ngay] Giải pháp đột phá mới")
                data["subject_options"] = [sa, sb]
        return data


class OmnichannelRequest(BaseModel):
    campaign_id: Optional[int] = None
    brief: str = Field(..., min_length=1, max_length=10000, description="Bản brief yêu cầu chiến dịch")
    target_audience: Optional[str] = Field("Đại chúng", max_length=1000, description="Đối tượng độc giả mục tiêu")
    channels: Optional[List[str]] = Field(
        default_factory=lambda: ["facebook", "tiktok", "email"],
        description="Danh sách các kênh cần sinh nội dung"
    )
    brand_kit_id: Optional[int] = None
    product_name: Optional[str] = None
    product_usp: Optional[str] = None
    tone: Optional[str] = None
    prompt_version: str = "v3"

    @field_validator("brief")
    @classmethod
    def validate_brief_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Bản brief chiến dịch không được để trống hoặc chỉ chứa khoảng trắng.")
        return v.strip()

    @field_validator("target_audience")
    @classmethod
    def validate_target_audience_not_empty(cls, v: Optional[str]) -> str:
        if v is None or not v.strip():
            return "Đại chúng"
        return v.strip()

    @field_validator("channels")
    @classmethod
    def validate_channels(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is not None:
            if len(v) == 0:
                raise ValueError("Danh sách channels không được là mảng rỗng.")
            valid_set = {"facebook", "tiktok", "email"}
            cleaned = []
            for c in v:
                norm = c.lower().strip()
                if norm not in valid_set:
                    raise ValueError(f"Kênh '{c}' không được hỗ trợ trong Omnichannel Engine (chỉ hỗ trợ: {', '.join(sorted(valid_set))})")
                if norm not in cleaned:
                    cleaned.append(norm)
            return cleaned
        return ["facebook", "tiktok", "email"]


class OmnichannelResponse(BaseModel):
    task_type: str = "OMNICHANNEL"
    campaign_id: Optional[int] = None
    facebook: Optional[FacebookCreative] = None
    tiktok: Optional[TikTokCreative] = None
    email: Optional[EmailCreative] = None
    is_fallback: bool = False
    compliance_score: int = 100
    warnings: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    model_used: str = "gemini-2.5-flash"
    prompt_version: str = "v3"
    model_provider: Optional[str] = "gemini"

    model_config = ConfigDict(from_attributes=True)


# Aliases for backwards and spec compatibility
FacebookContentResponse = FacebookCreative
TikTokSceneItem = TikTokScene
TikTokContentResponse = TikTokCreative
EmailContentResponse = EmailCreative


# ==============================================================================
# Enterprise Settings & BYOK Custom AI API Key (M6 - FEAT-BE-22..FEAT-BE-25)
# ==============================================================================

class AIKeyTestRequest(BaseModel):
    provider: str = Field("gemini", pattern="^(gemini|openrouter|openai)$", description="Nhà cung cấp AI ('gemini', 'openrouter', 'openai')")
    api_key: str = Field(..., description="API Key cần kiểm tra")
    model: Optional[str] = Field("gemini-2.5-flash", description="Model AI cần kiểm tra")

    @field_validator("api_key")
    @classmethod
    def validate_api_key_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("API Key không được để trống hoặc chỉ chứa khoảng trắng.")
        return v.strip()

    @field_validator("provider", mode="before")
    @classmethod
    def validate_provider(cls, v: Any) -> str:
        # Chạy TRƯỚC ràng buộc `pattern` của field để trả thông báo lỗi thân thiện,
        # đồng thời chuẩn hoá alias ("google" -> "gemini", "gpt" -> "openai") về đúng
        # 3 provider trong whitelist. `pattern` vẫn là lớp phòng thủ thứ hai.
        if not isinstance(v, str):
            raise ValueError(f"Nhà cung cấp '{v}' không được hỗ trợ. Chỉ hỗ trợ 'gemini', 'openrouter', 'openai'.")
        lower_p = v.lower().strip()
        if lower_p in ["google", "gemini"]:
            return "gemini"
        if lower_p == "openrouter":
            return "openrouter"
        if lower_p in ["openai", "gpt"]:
            return "openai"
        raise ValueError(f"Nhà cung cấp '{v}' không được hỗ trợ. Chỉ hỗ trợ 'gemini', 'openrouter', 'openai'.")

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: Optional[str], info: ValidationInfo) -> str:
        provider = info.data.get("provider", "gemini") if info.data else "gemini"
        if not v or not v.strip():
            if provider == "openai":
                return "gpt-4o"
            elif provider == "openrouter":
                return "meta-llama/llama-3.3-70b-instruct"
            return "gemini-2.5-flash"
        clean_m = v.strip()
        lower_m = clean_m.lower()

        if provider == "gemini":
            if not lower_m.startswith("gemini"):
                raise ValueError(f"Mô hình '{v}' không thuộc hệ sinh thái Google Gemini.")
            return lower_m
        elif provider == "openai":
            valid_prefixes = ("gpt-", "o1", "o3", "text-embedding-", "chatgpt-")
            if not any(lower_m.startswith(p) for p in valid_prefixes):
                raise ValueError(f"Mô hình '{v}' không thuộc hệ sinh thái OpenAI.")
            return lower_m
        elif provider == "openrouter":
            if "/" not in clean_m or len(clean_m) < 3:
                raise ValueError(f"Mô hình '{v}' không hợp lệ cho OpenRouter (cần định dạng tác giả/tên-mô-hình, ví dụ 'meta-llama/llama-3.3-70b-instruct').")
            return clean_m
        return clean_m

    @model_validator(mode="after")
    def validate_provider_and_model_compatibility(self) -> "AIKeyTestRequest":
        prov = (self.provider or "gemini").lower().strip()
        m = (self.model or "").lower().strip()
        if prov == "gemini":
            if not m.startswith("gemini"):
                raise ValueError(f"Mô hình '{self.model}' không thuộc hệ sinh thái Google Gemini.")
        elif prov == "openai":
            valid_prefixes = ("gpt-", "o1", "o3", "text-embedding-", "chatgpt-")
            if not any(m.startswith(p) for p in valid_prefixes):
                raise ValueError(f"Mô hình '{self.model}' không thuộc hệ sinh thái OpenAI.")
        elif prov == "openrouter":
            if "/" not in self.model or len(self.model) < 3:
                raise ValueError(f"Mô hình '{self.model}' không hợp lệ cho OpenRouter.")
        return self


class AIKeyTestResponse(BaseModel):
    success: bool
    latency_ms: int
    message: str
    provider: Optional[str] = "gemini"
    model: Optional[str] = "gemini-2.5-flash"
    error: Optional[str] = None


class AIKeyCreate(BaseModel):
    provider: str = Field("gemini", pattern="^(gemini|openrouter|openai)$", description="Nhà cung cấp AI ('gemini', 'openrouter', 'openai')")
    api_key: str = Field(..., description="API Key cần lưu trữ an toàn")
    model: Optional[str] = Field("gemini-2.5-flash", description="Model AI lựa chọn")
    workspace_id: Optional[int] = Field(None, description="ID Workspace nếu lưu khóa cho Workspace")
    is_active: Optional[bool] = Field(True, description="Trạng thái kích hoạt khóa")

    @field_validator("api_key")
    @classmethod
    def validate_api_key_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("API Key không được để trống hoặc chỉ chứa khoảng trắng.")
        return v.strip()

    @field_validator("provider", mode="before")
    @classmethod
    def validate_provider(cls, v: Any) -> str:
        # Chạy TRƯỚC ràng buộc `pattern` của field để trả thông báo lỗi thân thiện,
        # đồng thời chuẩn hoá alias ("google" -> "gemini", "gpt" -> "openai") về đúng
        # 3 provider trong whitelist. `pattern` vẫn là lớp phòng thủ thứ hai.
        if not isinstance(v, str):
            raise ValueError(f"Nhà cung cấp '{v}' không được hỗ trợ. Chỉ hỗ trợ 'gemini', 'openrouter', 'openai'.")
        lower_p = v.lower().strip()
        if lower_p in ["google", "gemini"]:
            return "gemini"
        if lower_p == "openrouter":
            return "openrouter"
        if lower_p in ["openai", "gpt"]:
            return "openai"
        raise ValueError(f"Nhà cung cấp '{v}' không được hỗ trợ. Chỉ hỗ trợ 'gemini', 'openrouter', 'openai'.")

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: Optional[str], info: ValidationInfo) -> str:
        provider = info.data.get("provider", "gemini") if info.data else "gemini"
        if not v or not v.strip():
            if provider == "openai":
                return "gpt-4o"
            elif provider == "openrouter":
                return "meta-llama/llama-3.3-70b-instruct"
            return "gemini-2.5-flash"
        clean_m = v.strip()
        lower_m = clean_m.lower()

        if provider == "gemini":
            if not lower_m.startswith("gemini"):
                raise ValueError(f"Mô hình '{v}' không thuộc hệ sinh thái Google Gemini.")
            return lower_m
        elif provider == "openai":
            valid_prefixes = ("gpt-", "o1", "o3", "text-embedding-", "chatgpt-")
            if not any(lower_m.startswith(p) for p in valid_prefixes):
                raise ValueError(f"Mô hình '{v}' không thuộc hệ sinh thái OpenAI.")
            return lower_m
        elif provider == "openrouter":
            if "/" not in clean_m or len(clean_m) < 3:
                raise ValueError(f"Mô hình '{v}' không hợp lệ cho OpenRouter (cần định dạng tác giả/tên-mô-hình, ví dụ 'meta-llama/llama-3.3-70b-instruct').")
            return clean_m
        return clean_m


AISettingsUpdate = AIKeyCreate


class AIKeyResponse(BaseModel):
    id: Optional[int] = None
    provider: str = "gemini"
    model: str = "gemini-2.5-flash"
    masked_key: str = Field(..., description="Khóa API đã được che mặt nạ bảo mật")
    is_active: bool = True
    workspace_id: Optional[int] = None
    user_id: Optional[int] = None
    scope: Optional[str] = None
    status: Optional[str] = "SAVED"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


AIKeySaveRequest = AIKeyCreate
AIKeySaveResponse = AIKeyResponse


# --- NOTIFICATIONS ---
class NotificationUpdate(BaseModel):
    read: Optional[bool] = Field(None, description="Trạng thái đã đọc")

class NotificationResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    workspace_id: int
    title: str
    message: str
    type: str
    read: bool
    target_tab: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- COMMAND CENTER ---
class CommandCenterAttentionItem(BaseModel):
    id: str
    type: str # "OVERDUE_TASK", "PENDING_APPROVAL", "BUDGET_OVERRUN", "CAMPAIGN_DEADLINE"
    severity: str # "HIGH", "CRITICAL", "MEDIUM"
    title: str
    message: str
    campaign_id: Optional[int] = None
    campaign_name: Optional[str] = None
    link: str
    due_date: Optional[str] = None

class CommandCenterMyWorkItem(BaseModel):
    id: int
    task_type: str
    title: str
    status: str
    priority: str
    due_date: Optional[str] = None
    campaign_id: int
    campaign_name: str
    is_overdue: bool

class CommandCenterCampaignHealth(BaseModel):
    campaign_id: int
    campaign_name: str
    status: str
    budget: float
    spent: float
    budget_utilization_pct: float
    total_tasks: int
    completed_tasks: int
    overdue_tasks: int
    health_status: str # "ON_TRACK", "AT_RISK", "CRITICAL"
    health_score: int # 0 to 100
    start_date: str
    end_date: str
    kpi_target: Optional[float] = None
    kpi_actual: Optional[float] = None
    kpi_achievement_pct: Optional[float] = None
    budget_risk: bool = False

class CommandCenterResponse(BaseModel):
    attention_items: List[CommandCenterAttentionItem]
    my_work_today: List[CommandCenterMyWorkItem]
    campaigns_health: List[CommandCenterCampaignHealth]
    summary_counts: Dict[str, int]
