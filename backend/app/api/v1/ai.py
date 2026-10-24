import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import ValidationError
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.pagination import Page, PageParams, page_params, paginate_query
from app.core.security import get_current_user, enforce_quota
from app.models.entities import (
    Campaign, MarketingChannel, Product, CampaignMetric, AILog, User,
    CampaignMember, BrandKit, Workspace, WorkspaceMember,
    MarketingContent, Task, AIChatThread, AIChatThreadMessage,
    MuseBoardCard, AgentStagedProposal,
)
from app.schemas.schemas import (
    AIIdeaRequest, AIIdeaResponse,
    AIDraftRequest, AIDraftResponse,
    AISummaryRequest, AISummaryResponse,
    AIPlanRequest, AIPlanResponse,
    OmnichannelRequest, OmnichannelResponse,
    AIAngleMatrixRequest, AIAngleMatrixResponse,
    AIPrelaunchCriticRequest, AIPrelaunchCriticResponse,
    AIChatCanvasRequest, AIChatCanvasResponse,
    AIChatThreadCreate, AIChatThreadUpdate, AIChatThreadResponse, AIChatThreadMessageItem,
    MuseBoardCardCreate, MuseBoardCardUpdate, MuseBoardCardResponse,
    AgentStagedProposalResponse, AgentExecuteProposalRequest,
    AILogResponse
)
from app.services.ai.ai_service import ai_service

# ==============================================================================
# KIẾN TRÚC THỰC THI AI KÉP (DUAL-MODE AI EXECUTION: SYNC + ASYNC JOB QUEUE)
# ==============================================================================
# Hệ thống hỗ trợ đồng thời 2 chế độ gọi AI phục vụ đúng yêu cầu học phần AIA331:
#   1. Chế độ Đồng bộ (Synchronous Fast-Path): `/ideas`, `/draft`, `/generate`,
#      `/summary`, `/summarize`, `/omnichannel`, `/plan` trả kết quả trực tiếp
#      cho giao diện Web (AI Studio, Dashboard, Campaign Detail).
#   2. Chế độ Hàng đợi Bất đồng bộ (Async Job Queue): `POST /api/v1/ai/jobs`
#      (trả 202 Accepted) + `GET /api/v1/ai/jobs/{job_id}` xử lý nền cho các
#      tác vụ nặng hoặc hàng loạt.
# ==============================================================================

router = APIRouter(prefix="/ai", tags=["Tính năng Trí Tuệ Nhân Tạo (AI Engine)"])

def check_campaign_access_for_ai(campaign_id: int, user: User, db: Session) -> Campaign:
    """Xác thực phân quyền mức bản ghi và cách ly đa người thuê (Tenant Isolation):
    - User ADMIN có toàn quyền truy cập AI Context của bất kỳ chiến dịch nào.
    - User MANAGER / AGENCY_MANAGER:
      + Phải là owner hoặc member của workspace chứa campaign (khi có workspace).
      + Campaign legacy workspace_id IS NULL: fail-closed — chỉ owner hoặc CampaignMember.
    - User MARKETER hoặc role khác:
      + Nếu campaign.workspace_id khác NULL: kiểm tra workspace isolation.
      + Đồng thời user chỉ được thao tác trên campaign mà họ sở hữu (owner_id) HOẶC là thành viên chiến dịch (CampaignMember).
    """
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chiến dịch không tồn tại")

    if user.role == "ADMIN":
        return campaign

    # Kiểm tra Tenant Isolation đối với workspace (kể cả workspace_id == 1)
    if campaign.workspace_id is not None:
        ws = db.query(Workspace).filter(Workspace.id == campaign.workspace_id).first()
        is_ws_owner = ws is not None and ws.owner_id == user.id
        is_ws_member = db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == campaign.workspace_id,
            WorkspaceMember.user_id == user.id
        ).first() is not None
        if not (is_ws_owner or is_ws_member):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access campaigns in this workspace"
            )
        if user.role in ("MANAGER", "AGENCY_MANAGER"):
            return campaign

    # Fail-closed: campaign không workspace thì không có ranh giới tenant để tin cậy,
    # mọi role (kể cả MANAGER/AGENCY_MANAGER) đều phải là owner hoặc CampaignMember.
    owner_id = getattr(campaign, "owner_id", None)
    if owner_id is None and hasattr(campaign, "created_by"):
        owner_id = getattr(campaign, "created_by", None)
    if owner_id == user.id:
        return campaign

    is_member = db.query(CampaignMember).filter(
        CampaignMember.campaign_id == campaign_id,
        CampaignMember.user_id == user.id
    ).first()
    if is_member:
        return campaign

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not authorized to access this resource"
    )


def _resolve_ai_workspace_id(
    db: Session,
    current_user: User,
    campaign: Optional[Campaign] = None,
    explicit_ws_id: Optional[int] = None,
) -> Optional[int]:
    if campaign is not None and campaign.workspace_id is not None:
        return campaign.workspace_id
    if explicit_ws_id is not None:
        return explicit_ws_id
    membership = db.query(WorkspaceMember).filter(WorkspaceMember.user_id == current_user.id).first()
    if membership:
        return membership.workspace_id
    owned_ws = db.query(Workspace).filter(Workspace.owner_id == current_user.id).first()
    if owned_ws:
        return owned_ws.id
    if current_user.role == "ADMIN":
        return 1
    return None

@router.post(
    "/ideas",
    response_model=AIIdeaResponse,
    description="Gợi ý ý tưởng nội dung tiếp thị (AIA331 Mục 3.2.1). Hỗ trợ cả chế độ đồng bộ và hàng đợi `POST /ai/jobs` (`kind=ideas`).",
)
def generate_ideas(
    req: AIIdeaRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Hạn mức: trước đây endpoint AI hoàn toàn không bị giới hạn, nên bất kỳ ai
    # giữ token (hoặc khoá BYOK) cũng có thể tiêu hết hạn mức của tổ chức.
    enforce_quota(f"ai:ideas:user={current_user.id}")
    user_id = current_user.id
    cid = req.campaign_id

    if cid is not None:
        campaign = check_campaign_access_for_ai(cid, current_user, db)
        ws_id = _resolve_ai_workspace_id(db, current_user, campaign, getattr(req, "workspace_id", None))
        product = db.query(Product).filter(Product.id == campaign.product_id).first()
        brand_kit = (
            db.query(BrandKit).filter(BrandKit.workspace_id == ws_id).first()
            if ws_id
            else None
        )
        channel = db.query(MarketingChannel).filter(MarketingChannel.code == req.channel_code).first()
        campaign_name = campaign.name
        objective = campaign.objective
        audience = campaign.audience
        product_name = (
            (req.custom_product.strip() if req.custom_product and req.custom_product.strip() else None)
            or (product.name if product and product.name else None)
            or (brand_kit.brand_name if brand_kit and brand_kit.brand_name else None)
            or campaign.name
        )
        product_usp = (
            (req.custom_usp.strip() if req.custom_usp and req.custom_usp.strip() else None)
            or (product.usp if product and product.usp else None)
            or (product.description if product and product.description else None)
            or (brand_kit.usp if brand_kit and brand_kit.usp else None)
            or campaign.key_message
            or campaign.objective
        )
    else:
        ws_id = _resolve_ai_workspace_id(db, current_user, None, getattr(req, "workspace_id", None))
        brand_kit = (
            db.query(BrandKit).filter(BrandKit.workspace_id == ws_id).first()
            if ws_id
            else None
        )
        custom_topic = (req.custom_topic or "").strip()
        custom_product = (req.custom_product or "").strip()
        custom_usp = (req.custom_usp or "").strip()
        if not custom_topic and not custom_product:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Thiếu ngữ cảnh đầu vào: Vui lòng chọn một Chiến dịch có sẵn hoặc nhập Chủ đề / Tên sản phẩm và USP để AI có dữ liệu sinh ý tưởng.",
            )
        channel = db.query(MarketingChannel).filter(MarketingChannel.code == req.channel_code).first()
        campaign_name = custom_topic or custom_product
        objective = custom_topic or f"Quảng bá sản phẩm {custom_product}"
        audience = (
            (brand_kit.target_audience if brand_kit and brand_kit.target_audience else None)
            or "Theo ngữ cảnh chủ đề và sản phẩm do người dùng cung cấp"
        )
        product_name = (
            custom_product
            or (brand_kit.brand_name if brand_kit and brand_kit.brand_name else None)
            or custom_topic
        )
        product_usp = (
            custom_usp
            or (brand_kit.usp if brand_kit and brand_kit.usp else None)
            or custom_topic
        )

    campaign_brief = f"{campaign_name} - Mục tiêu: {objective} - Đối tượng: {audience} - Sản phẩm: {product_name}"
    context = {
        "workspace_id": ws_id,
        "campaign_name": campaign_name,
        "campaign_brief": campaign_brief,
        "objective": objective,
        "audience": audience,
        "product_name": product_name,
        "product_usp": product_usp,
        "channel_name": channel.name if channel else req.channel_code,
        "tone": req.tone or (brand_kit.tone_of_voice if brand_kit and brand_kit.tone_of_voice else "Chuyên nghiệp")
    }
    if req.chain_id is not None:
        # Chuỗi fallback tường minh (xem AIService._resolve_chain_hops).
        context["model_chain_id"] = req.chain_id
    if getattr(req, "preferred_provider", None):
        context["provider"] = req.preferred_provider
    if getattr(req, "preferred_model", None):
        context["model"] = req.preferred_model

    try:
        result = ai_service.execute_task(
            db=db,
            user_id=user_id,
            campaign_id=cid,
            task_type="idea_generation",
            task_code="IDEA",
            prompt_version=req.prompt_version,
            context=context
        )
        return AIIdeaResponse.model_validate(result)
    except ValidationError:
        if ai_service.fallback_enabled:
            fallback = ai_service._generate_fallback("idea_generation", context)
            fallback["model_used"] = f"{ai_service.model} (Fallback Recovered)"
            fallback["prompt_version"] = req.prompt_version
            fallback["task_type"] = "IDEA"
            fallback.setdefault("warnings", []).append("Phản hồi AI sai cấu trúc schema, đã kích hoạt Smart Fallback.")
            return AIIdeaResponse.model_validate(fallback)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Phản hồi từ AI không đúng cấu trúc schema yêu cầu.")
    except Exception as e:
        if ai_service.fallback_enabled:
            fallback = ai_service._generate_fallback("idea_generation", context)
            fallback["model_used"] = f"{ai_service.model} (Fallback Recovered)"
            fallback["prompt_version"] = req.prompt_version
            fallback["task_type"] = "IDEA"
            fallback.setdefault("warnings", []).append(f"Dịch vụ AI gặp sự cố ({str(e)}), đã kích hoạt Smart Fallback.")
            return AIIdeaResponse.model_validate(fallback)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Lỗi dịch vụ AI: {str(e)}")

@router.post(
    "/draft",
    response_model=AIDraftResponse,
    description="Soạn thảo nội dung tiếp thị theo kênh (AIA331 Mục 3.2.2). Hỗ trợ cả chế độ đồng bộ và `POST /ai/jobs` (`kind=draft`).",
)
@router.post(
    "/generate",
    response_model=AIDraftResponse,
    description="Soạn thảo nội dung tiếp thị theo kênh (AIA331 Mục 3.2.2). Hỗ trợ cả chế độ đồng bộ và `POST /ai/jobs` (`kind=draft`).",
)
def generate_draft(
    req: AIDraftRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    enforce_quota(f"ai:draft:user={current_user.id}")
    user_id = current_user.id
    cid = req.campaign_id

    if not req.selected_idea or not req.selected_idea.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Thiếu ý tưởng đầu vào: Vui lòng chọn hoặc nhập một góc tiếp cận (selected_idea) trước khi yêu cầu AI viết bản thảo.",
        )

    if cid is not None:
        campaign = check_campaign_access_for_ai(cid, current_user, db)
        ws_id = _resolve_ai_workspace_id(db, current_user, campaign, getattr(req, "workspace_id", None))
        product = db.query(Product).filter(Product.id == campaign.product_id).first()
        brand_kit = (
            db.query(BrandKit).filter(BrandKit.workspace_id == ws_id).first()
            if ws_id
            else None
        )
        channel = db.query(MarketingChannel).filter(MarketingChannel.code == req.channel_code).first()
        campaign_name = campaign.name
        product_name = (
            (req.custom_product.strip() if req.custom_product and req.custom_product.strip() else None)
            or (product.name if product and product.name else None)
            or (brand_kit.brand_name if brand_kit and brand_kit.brand_name else None)
            or campaign.name
        )
        product_usp = (
            (req.custom_usp.strip() if req.custom_usp and req.custom_usp.strip() else None)
            or (product.usp if product and product.usp else None)
            or (product.description if product and product.description else None)
            or (brand_kit.usp if brand_kit and brand_kit.usp else None)
            or campaign.key_message
            or campaign.objective
        )
    else:
        ws_id = _resolve_ai_workspace_id(db, current_user, None, getattr(req, "workspace_id", None))
        brand_kit = (
            db.query(BrandKit).filter(BrandKit.workspace_id == ws_id).first()
            if ws_id
            else None
        )
        custom_product = (req.custom_product or "").strip()
        custom_usp = (req.custom_usp or "").strip()
        if not custom_product:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Thiếu ngữ cảnh sản phẩm: Vui lòng chọn một Chiến dịch hoặc nhập Tên sản phẩm và USP trước khi yêu cầu AI viết bản thảo.",
            )
        channel = db.query(MarketingChannel).filter(MarketingChannel.code == req.channel_code).first()
        campaign_name = custom_product
        product_name = custom_product
        product_usp = (
            custom_usp
            or (brand_kit.usp if brand_kit and brand_kit.usp else None)
            or req.selected_idea.strip()
        )

    campaign_brief = f"{campaign_name} - Sản phẩm: {product_name} - USP: {product_usp}"
    context = {
        "workspace_id": ws_id,
        "campaign_name": campaign_name,
        "campaign_brief": campaign_brief,
        "product_name": product_name,
        "product_usp": product_usp,
        "channel_name": channel.name if channel else req.channel_code,
        "channel_rules": channel.format_rules if channel else "Viết hấp dẫn, súc tích",
        "selected_idea": req.selected_idea
    }
    if req.chain_id is not None:
        context["model_chain_id"] = req.chain_id
    if getattr(req, "preferred_provider", None):
        context["provider"] = req.preferred_provider
    if getattr(req, "preferred_model", None):
        context["model"] = req.preferred_model

    try:
        result = ai_service.execute_task(
            db=db,
            user_id=user_id,
            campaign_id=cid,
            task_type="content_draft",
            task_code="DRAFT",
            prompt_version=req.prompt_version,
            context=context
        )
        return AIDraftResponse.model_validate(result)
    except ValidationError:
        if ai_service.fallback_enabled:
            fallback = ai_service._generate_fallback("content_draft", context)
            fallback["model_used"] = f"{ai_service.model} (Fallback Recovered)"
            fallback["prompt_version"] = req.prompt_version
            fallback["task_type"] = "DRAFT"
            fallback.setdefault("warnings", []).append("Phản hồi AI sai cấu trúc schema, đã kích hoạt Smart Fallback.")
            return AIDraftResponse.model_validate(fallback)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Phản hồi từ AI không đúng cấu trúc schema yêu cầu.")
    except Exception as e:
        if ai_service.fallback_enabled:
            fallback = ai_service._generate_fallback("content_draft", context)
            fallback["model_used"] = f"{ai_service.model} (Fallback Recovered)"
            fallback["prompt_version"] = req.prompt_version
            fallback["task_type"] = "DRAFT"
            fallback.setdefault("warnings", []).append(f"Dịch vụ AI gặp sự cố ({str(e)}), đã kích hoạt Smart Fallback.")
            return AIDraftResponse.model_validate(fallback)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Lỗi dịch vụ AI: {str(e)}")

@router.post(
    "/summary",
    response_model=AISummaryResponse,
    description="Tóm tắt hiệu quả chiến dịch và đề xuất cải thiện (AIA331 Mục 3.2.3). Hỗ trợ cả chế độ đồng bộ và `POST /ai/jobs` (`kind=summary`).",
)
@router.post(
    "/summarize",
    response_model=AISummaryResponse,
    description="Tóm tắt hiệu quả chiến dịch và đề xuất cải thiện (AIA331 Mục 3.2.3). Hỗ trợ cả chế độ đồng bộ và `POST /ai/jobs` (`kind=summary`).",
)
def generate_summary(
    req: AISummaryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    enforce_quota(f"ai:summary:user={current_user.id}")
    user_id = current_user.id
    campaign = check_campaign_access_for_ai(req.campaign_id, current_user, db)

    metrics = db.query(CampaignMetric).filter(CampaignMetric.campaign_id == campaign.id).all()
    total_views = sum(m.views for m in metrics)
    total_clicks = sum(m.clicks for m in metrics)
    total_conversions = sum(m.conversions for m in metrics)
    total_cost = sum(float(m.cost) for m in metrics)
    total_revenue = sum(float(m.revenue) for m in metrics)

    ctr = round((total_clicks / total_views * 100.0) if total_views > 0 else 0.0, 2)
    cpc = round((total_cost / total_clicks) if total_clicks > 0 else 0.0, 2)
    cvr = round((total_conversions / total_clicks * 100.0) if total_clicks > 0 else 0.0, 2)
    roi = round(((total_revenue - total_cost) / total_cost * 100.0) if total_cost > 0 else 0.0, 2)

    context = {
        "workspace_id": campaign.workspace_id,
        "campaign_name": campaign.name,
        "objective": campaign.objective,
        "budget": f"{float(campaign.budget):,.0f}",
        "total_views": total_views,
        "total_clicks": total_clicks,
        "ctr": ctr,
        "total_conversions": total_conversions,
        "cvr": cvr,
        "total_cost": f"{total_cost:,.0f}",
        "cpc": f"{cpc:,.0f}",
        "total_revenue": f"{total_revenue:,.0f}",
        "roi": roi
    }
    if req.chain_id is not None:
        context["model_chain_id"] = req.chain_id

    try:
        result = ai_service.execute_task(
            db=db,
            user_id=user_id,
            campaign_id=campaign.id,
            task_type="performance_summary",
            task_code="SUMMARY",
            prompt_version=req.prompt_version,
            context=context
        )
        return AISummaryResponse.model_validate(result)
    except ValidationError:
        if ai_service.fallback_enabled:
            fallback = ai_service._generate_fallback("performance_summary", context)
            fallback["model_used"] = f"{ai_service.model} (Fallback Recovered)"
            fallback["prompt_version"] = req.prompt_version
            fallback["task_type"] = "SUMMARY"
            fallback.setdefault("warnings", []).append("Phản hồi AI sai cấu trúc schema, đã kích hoạt Smart Fallback.")
            return AISummaryResponse.model_validate(fallback)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Phản hồi từ AI không đúng cấu trúc schema yêu cầu.")
    except Exception as e:
        if ai_service.fallback_enabled:
            fallback = ai_service._generate_fallback("performance_summary", context)
            fallback["model_used"] = f"{ai_service.model} (Fallback Recovered)"
            fallback["prompt_version"] = req.prompt_version
            fallback["task_type"] = "SUMMARY"
            fallback.setdefault("warnings", []).append(f"Dịch vụ AI gặp sự cố ({str(e)}), đã kích hoạt Smart Fallback.")
            return AISummaryResponse.model_validate(fallback)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Lỗi dịch vụ AI: {str(e)}")

@router.post(
    "/plan",
    response_model=AIPlanResponse,
    description="Sinh kế hoạch chiến dịch (phân bổ ngân sách, KPI, công việc). Hỗ trợ cả chế độ đồng bộ và `POST /ai/jobs` (`kind=plan`).",
)
def generate_plan(
    req: AIPlanRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Sinh KẾ HOẠCH chiến dịch (phân bổ ngân sách + KPI + task) cho một campaign.

    `campaign_id` là BẮT BUỘC (AIPlanRequest đã enforce): kế hoạch sinh từ con
    số thật — ngân sách, thời gian, đối tượng — chứ không từ chủ đề tự do.
    Endpoint chỉ SINH kế hoạch; việc ghi vào CSDL là `POST /campaigns/{id}/plan/apply`.
    """
    enforce_quota(f"ai:plan:user={current_user.id}")
    user_id = current_user.id
    campaign = check_campaign_access_for_ai(req.campaign_id, current_user, db)

    product = db.query(Product).filter(Product.id == campaign.product_id).first()

    # Kênh chiến dịch có thể dùng: đã phân bổ sẵn thì giữ nguyên lựa chọn của
    # người dùng; chưa có thì lấy toàn bộ kênh đang ACTIVE trong hệ thống.
    allocated_codes = [
        a.channel.code for a in campaign.budget_allocations
        if a.channel is not None and a.channel.code
    ]
    if allocated_codes:
        channel_codes = list(dict.fromkeys(allocated_codes))
        channels_display = ", ".join(channel_codes)
    else:
        active_channels = db.query(MarketingChannel).filter(
            MarketingChannel.status == "ACTIVE"
        ).order_by(MarketingChannel.id).all()
        channel_codes = [c.code for c in active_channels] or ["facebook"]
        channels_display = ", ".join(c.name for c in active_channels) or "Chưa có kênh"

    # Thời gian chiến dịch (chuỗi YYYY-MM-DD): offset task được kẹp trong khoảng
    # [0, (end - start).days] để không có task rơi ngoài lịch chiến dịch.
    try:
        start_d = datetime.strptime(campaign.start_date, "%Y-%m-%d").date()
        end_d = datetime.strptime(campaign.end_date, "%Y-%m-%d").date()
        max_due_offset = max((end_d - start_d).days, 0)
        duration_days = max_due_offset + 1
    except (TypeError, ValueError):
        max_due_offset = 30
        duration_days = 31

    # Mục tiêu KPI hiện có trên chiến dịch (nếu người dùng đã khai) làm chỉ tiêu
    # gợi ý cho AI — không tự bịa chỉ tiêu mới.
    from app.models.entities import CampaignKPITarget
    existing_kpi = (
        db.query(CampaignKPITarget)
        .filter(CampaignKPITarget.campaign_id == campaign.id)
        .order_by(CampaignKPITarget.id)
        .first()
    )

    context = {
        "workspace_id": campaign.workspace_id,
        "campaign_name": campaign.name,
        "objective": campaign.objective,
        "audience": campaign.audience,
        "product_name": product.name if product else "Sản phẩm",
        "product_usp": product.usp if product else "Chất lượng vượt trội",
        "budget": f"{float(campaign.budget):,.0f}",
        "budget_amount": float(campaign.budget),
        "start_date": campaign.start_date,
        "end_date": campaign.end_date,
        "duration_days": duration_days,
        "channels": channels_display,
        "channel_codes": channel_codes,
        "max_due_offset": max_due_offset,
        "target_kpi_name": existing_kpi.metric_name if existing_kpi else None,
        "target_kpi_value": float(existing_kpi.target_value) if existing_kpi else None,
        "workspace_id": campaign.workspace_id,
    }
    if req.chain_id is not None:
        context["model_chain_id"] = req.chain_id

    try:
        result = ai_service.execute_task(
            db=db,
            user_id=user_id,
            campaign_id=campaign.id,
            task_type="campaign_plan",
            task_code="PLAN",
            prompt_version=req.prompt_version,
            context=context
        )
        plan = AIPlanResponse.model_validate(result)
    except ValidationError:
        if ai_service.fallback_enabled:
            fallback = ai_service._generate_fallback("campaign_plan", context)
            fallback["model_used"] = f"{ai_service.model} (Fallback Recovered)"
            fallback["prompt_version"] = req.prompt_version
            fallback["task_type"] = "PLAN"
            fallback.setdefault("warnings", []).append("Phản hồi AI sai cấu trúc schema, đã kích hoạt Smart Fallback.")
            plan = AIPlanResponse.model_validate(fallback)
        else:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Phản hồi từ AI không đúng cấu trúc schema yêu cầu.")
    except HTTPException:
        raise
    except Exception as e:
        if ai_service.fallback_enabled:
            fallback = ai_service._generate_fallback("campaign_plan", context)
            fallback["model_used"] = f"{ai_service.model} (Fallback Recovered)"
            fallback["prompt_version"] = req.prompt_version
            fallback["task_type"] = "PLAN"
            fallback.setdefault("warnings", []).append(f"Dịch vụ AI gặp sự cố ({str(e)}), đã kích hoạt Smart Fallback.")
            plan = AIPlanResponse.model_validate(fallback)
        else:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Lỗi dịch vụ AI: {str(e)}")

    # Kẹp due_offset_days về [0, max_due_offset]: model thật có thể lệch một chút
    # so với số ngày chiến dịch; kẹp tại đây (kèm warning) thay vì để apply 400.
    clamped = 0
    for t in plan.tasks:
        if t.due_offset_days < 0:
            t.due_offset_days = 0
            clamped += 1
        elif t.due_offset_days > max_due_offset:
            t.due_offset_days = max_due_offset
            clamped += 1
    if clamped:
        plan.warnings.append(
            f"{clamped} công việc có ngày hoàn thành ngoài khoảng chiến dịch "
            f"({campaign.start_date} -> {campaign.end_date}), đã kẹp về biên cho phép."
        )
    return plan

def _score_omnichannel_compliance(payload: dict, brand_kit: Optional[BrandKit], db: Session) -> Optional[int]:
    """Chấm điểm tuân thủ TRÊN CHÍNH NỘI DUNG VỪA SINH, bằng bộ quy tắc tất định."""
    from app.services.compliance.compliance_service import ComplianceScanner

    if brand_kit is None or brand_kit.workspace_id is None:
        return None

    workspace_id = brand_kit.workspace_id
    scores: List[int] = []

    fb = payload.get("facebook") or {}
    if fb.get("title") or fb.get("body") or fb.get("primary_text"):
        scores.append(ComplianceScanner.scan(
            title=fb.get("title") or fb.get("headline") or "",
            body=fb.get("body") or fb.get("primary_text") or "",
            cta=fb.get("cta"),
            workspace_id=workspace_id,
            db=db,
        ).score)

    tk = payload.get("tiktok") or {}
    tk_visual = " ".join(
        str(scene.get("visual_action") or scene.get("visual") or "")
        for scene in (tk.get("scenes") or [])
        if isinstance(scene, dict)
    )
    tk_text = " ".join([tk.get("hook_3s") or "", tk_visual, tk.get("caption_with_hashtags") or ""]).strip()
    if tk_text:
        scores.append(ComplianceScanner.scan(
            title=tk.get("hook_3s") or "",
            body=tk_text,
            cta=None,
            workspace_id=workspace_id,
            db=db,
        ).score)

    em = payload.get("email") or {}
    em_text = " ".join([
        em.get("subject_line_a") or "",
        em.get("subject_line_b") or "",
        em.get("body") or em.get("body_content") or "",
        em.get("cta_button") or "",
    ]).strip()
    if em_text:
        scores.append(ComplianceScanner.scan(
            title=em.get("subject_line_a") or "",
            body=em_text,
            cta=em.get("cta_button"),
            workspace_id=workspace_id,
            db=db,
        ).score)

    return min(scores) if scores else None


@router.post(
    "/omnichannel",
    response_model=OmnichannelResponse,
    response_model_exclude_none=True,
    description="Sinh gói nội dung đa kênh (Facebook, TikTok, Email) từ 1 brief. Hỗ trợ cả chế độ đồng bộ và `POST /ai/jobs` (`kind=omnichannel`).",
)
def generate_omnichannel(
    req: OmnichannelRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deep 3-Channel AI Creative Engine (R2):
    Sinh trọn bộ tài sản tiếp thị Facebook, TikTok và Email từ 1 brief duy nhất,
    kế thừa Brand Kit (USP, Tone, Banned Keywords) của Workspace.
    """
    enforce_quota(f"ai:omnichannel:user={current_user.id}")
    user_id = current_user.id
    cid = req.campaign_id

    campaign = None
    product = None
    brand_kit = None

    if cid is not None:
        campaign = check_campaign_access_for_ai(cid, current_user, db)
        if campaign.product_id:
            product = db.query(Product).filter(Product.id == campaign.product_id).first()
        if campaign.workspace_id:
            brand_kit = db.query(BrandKit).filter(BrandKit.workspace_id == campaign.workspace_id).first()

    if not brand_kit and req.brand_kit_id:
        bk = db.query(BrandKit).filter(BrandKit.id == req.brand_kit_id).first()
        if bk:
            if current_user.role != "ADMIN" and bk.workspace_id is not None:
                ws = db.query(Workspace).filter(Workspace.id == bk.workspace_id).first()
                is_ws_owner = ws is not None and ws.owner_id == current_user.id
                is_ws_member = db.query(WorkspaceMember).filter(
                    WorkspaceMember.workspace_id == bk.workspace_id,
                    WorkspaceMember.user_id == current_user.id
                ).first() is not None
                if not (is_ws_owner or is_ws_member):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Not authorized to access this Brand Kit"
                    )
            brand_kit = bk

    if not brand_kit:
        membership = db.query(WorkspaceMember).filter(WorkspaceMember.user_id == user_id).first()
        if membership:
            brand_kit = db.query(BrandKit).filter(BrandKit.workspace_id == membership.workspace_id).first()

    target_ws_id = (
        (campaign.workspace_id if campaign and campaign.workspace_id else None)
        or (brand_kit.workspace_id if brand_kit and brand_kit.workspace_id else None)
        or _resolve_ai_workspace_id(db, current_user, campaign, getattr(req, "workspace_id", None))
    )

    brand_name = (
        (req.product_name.strip() if req.product_name and req.product_name.strip() else None)
        or (product.name if product and product.name else None)
        or (brand_kit.brand_name if brand_kit and brand_kit.brand_name else None)
        or (campaign.name if campaign else "Thương hiệu theo Brief")
    )
    usp = (
        (req.product_usp.strip() if req.product_usp and req.product_usp.strip() else None)
        or (product.usp if product and product.usp else None)
        or (product.description if product and product.description else None)
        or (brand_kit.usp if brand_kit and brand_kit.usp else None)
        or (campaign.key_message if campaign and campaign.key_message else None)
        or req.brief
    )
    tone_of_voice = req.tone or (brand_kit.tone_of_voice if brand_kit and brand_kit.tone_of_voice else "Chuyên nghiệp, hiện đại, tin cậy")

    import json
    banned_keywords = []
    if brand_kit and brand_kit.banned_keywords_json:
        try:
            banned_keywords = json.loads(brand_kit.banned_keywords_json)
        except Exception:
            banned_keywords = []

    target_audience = (
        (req.target_audience.strip() if req.target_audience and req.target_audience.strip() and req.target_audience.strip() != "Đại chúng" else None)
        or (campaign.audience if campaign and campaign.audience else None)
        or (brand_kit.target_audience if brand_kit and brand_kit.target_audience else None)
        or (req.target_audience.strip() if req.target_audience and req.target_audience.strip() else "Theo nội dung Brief")
    )
    product_name = (
        (req.product_name.strip() if req.product_name and req.product_name.strip() else None)
        or (product.name if product and product.name else None)
        or (brand_kit.brand_name if brand_kit and brand_kit.brand_name else None)
        or (campaign.name if campaign else "Theo nội dung Brief")
    )
    campaign_name = campaign.name if campaign else product_name

    requested_channels = req.channels if req.channels else ["facebook", "tiktok", "email"]

    context = {
        "workspace_id": target_ws_id,
        "campaign_name": campaign_name,
        "brief": req.brief,
        "target_audience": target_audience,
        "brand_name": brand_name,
        "product_name": product_name,
        "usp": usp,
        "product_usp": usp,
        "tone_of_voice": tone_of_voice,
        "tone": tone_of_voice,
        "banned_keywords": ", ".join(banned_keywords) if banned_keywords else "Không có",
        "requested_channels": ", ".join(requested_channels)
    }
    if req.chain_id is not None:
        context["model_chain_id"] = req.chain_id
    if getattr(req, "preferred_provider", None):
        context["provider"] = req.preferred_provider
    if getattr(req, "preferred_model", None):
        context["model"] = req.preferred_model

    def filter_channels(data: dict) -> dict:
        res = dict(data)
        if "facebook" not in requested_channels:
            res["facebook"] = None
        if "tiktok" not in requested_channels:
            res["tiktok"] = None
        if "email" not in requested_channels:
            res["email"] = None
        res["campaign_id"] = cid
        res.setdefault("model_used", ai_service.model)
        res.setdefault("is_fallback", False)
        res["prompt_version"] = req.prompt_version
        res["task_type"] = "OMNICHANNEL"
        res["compliance_score"] = _score_omnichannel_compliance(res, brand_kit, db)
        return res

    try:
        result = ai_service.execute_task(
            db=db,
            user_id=user_id,
            campaign_id=cid,
            task_type="omnichannel_generation",
            task_code="OMNICHANNEL",
            prompt_version=req.prompt_version,
            context=context
        )
        filtered_result = filter_channels(result)
        return OmnichannelResponse.model_validate(filtered_result)
    except ValidationError:
        if ai_service.fallback_enabled:
            fallback = ai_service._generate_fallback("omnichannel_generation", context)
            fallback["model_used"] = "template-fallback-engine"
            fallback["prompt_version"] = req.prompt_version
            fallback["task_type"] = "OMNICHANNEL"
            fallback.setdefault("warnings", []).append("Phản hồi AI sai cấu trúc schema, đã kích hoạt Smart Fallback.")
            filtered_fallback = filter_channels(fallback)
            return OmnichannelResponse.model_validate(filtered_fallback)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Phản hồi từ AI không đúng cấu trúc schema yêu cầu."
        )
    except Exception as e:
        if ai_service.fallback_enabled:
            fallback = ai_service._generate_fallback("omnichannel_generation", context)
            fallback["model_used"] = "template-fallback-engine"
            fallback["prompt_version"] = req.prompt_version
            fallback["task_type"] = "OMNICHANNEL"
            fallback.setdefault("warnings", []).append(f"Dịch vụ AI gặp sự cố ({str(e)}), đã kích hoạt Smart Fallback.")
            filtered_fallback = filter_channels(fallback)
            return OmnichannelResponse.model_validate(filtered_fallback)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Lỗi dịch vụ AI: {str(e)}")


@router.post(
    "/angle-matrix",
    response_model=AIAngleMatrixResponse,
    description="Ma trận Creative Angle × Hook 3x3 (Pain-Point, Social-Proof, Urgency/FOMO).",
)
def generate_angle_matrix(
    req: AIAngleMatrixRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sinh 9 biến thể quảng cáo theo ma trận 3 Góc tiếp cận × 3 Hook cho chiến dịch hoặc brief."""
    enforce_quota(f"ai:angle_matrix:user={current_user.id}")
    cid = req.campaign_id
    campaign = None
    product = None
    brand_kit = None

    if cid is not None:
        campaign = check_campaign_access_for_ai(cid, current_user, db)
        if campaign.product_id:
            product = db.query(Product).filter(Product.id == campaign.product_id).first()
        if campaign.workspace_id:
            brand_kit = db.query(BrandKit).filter(BrandKit.workspace_id == campaign.workspace_id).first()

    campaign_name = campaign.name if campaign else "Chiến dịch Tiếp thị Đa góc độ"
    funnel_stage = req.funnel_stage or (getattr(campaign, "funnel_stage", None) if campaign else "BoFU") or "BoFU"
    product_name = req.product_name or (product.name if product else (brand_kit.brand_name if brand_kit else campaign_name))
    product_usp = req.product_usp or (product.usp if product else (brand_kit.usp if brand_kit else "Tối ưu hiệu suất vượt trội"))
    target_audience = req.target_audience or req.audience or (campaign.audience if campaign else "Khách hàng tiềm năng")
    tone = req.tone or (brand_kit.tone_of_voice if brand_kit else "Chuyên nghiệp, thuyết phục")
    ch_code = (req.channel_code if req.channel_code and req.channel_code != "facebook" else (req.channel or req.channel_code or "facebook"))

    res = ai_service.generate_angle_hook_matrix(
        db=db,
        user_id=current_user.id,
        campaign_id=cid,
        workspace_id=campaign.workspace_id if campaign else req.workspace_id,
        campaign_name=campaign_name,
        objective=req.objective or (campaign.objective if campaign else None),
        funnel_stage=funnel_stage,
        channel=ch_code,
        channel_code=ch_code,
        product_name=product_name,
        product_usp=product_usp,
        target_audience=target_audience,
        audience=target_audience,
        tone=tone,
        brief=req.brief or req.key_message or "",
        angles=req.angles,
        hooks_per_angle=req.hooks_per_angle,
        prompt_version=req.prompt_version,
        chain_id=req.chain_id,
    )
    return AIAngleMatrixResponse.model_validate(res)


@router.post(
    "/prelaunch-critic",
    response_model=AIPrelaunchCriticResponse,
    description="AI Pre-Launch Focus Group Critic: Chấm điểm giả lập bởi 4 Persona khách hàng & chính sách trước khi chạy Ads.",
)
def evaluate_prelaunch_critic(
    req: AIPrelaunchCriticRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mô phỏng hội đồng 4 Persona khách hàng & chính sách đánh giá bài quảng cáo trước khi tiêu ngân sách."""
    enforce_quota(f"ai:prelaunch_critic:user={current_user.id}")
    cid = req.campaign_id
    campaign = None
    product = None

    if cid is not None:
        campaign = check_campaign_access_for_ai(cid, current_user, db)
        if campaign.product_id:
            product = db.query(Product).filter(Product.id == campaign.product_id).first()

    funnel_stage = req.funnel_stage or (getattr(campaign, "funnel_stage", None) if campaign else "BoFU") or "BoFU"
    target_audience = req.target_audience or req.audience or (campaign.audience if campaign else "Khách hàng mục tiêu")
    product_name = req.product_name or (product.name if product else (campaign.name if campaign else "Sản phẩm"))
    product_usp = req.product_usp or (product.usp if product else "Giải pháp hiệu quả vượt trội")
    ch_code = (req.channel_code if req.channel_code and req.channel_code != "facebook" else (req.channel or req.channel_code or "facebook"))

    res = ai_service.simulate_prelaunch_critic(
        db=db,
        user_id=current_user.id,
        campaign_id=cid,
        workspace_id=campaign.workspace_id if campaign else req.workspace_id,
        title=req.title or "Giải pháp tiếp thị chuyển đổi cao",
        body=req.body,
        cta=req.cta or "Tìm hiểu ngay",
        channel=ch_code,
        channel_code=ch_code,
        funnel_stage=funnel_stage,
        target_audience=target_audience,
        product_name=product_name,
        product_usp=product_usp,
        prompt_version=req.prompt_version,
        chain_id=req.chain_id,
    )
    return AIPrelaunchCriticResponse.model_validate(res)


@router.post(
    "/chat",
    response_model=AIChatCanvasResponse,
    description="Hội thoại nhiều lượt (Multi-turn Chat) song song với Bàn soạn thảo thủ công (Interactive Canvas & Copilot).",
)
def chat_canvas_copilot(
    req: AIChatCanvasRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Đối thoại trực tiếp nhiều lượt với AI (như Claude Artifacts / ChatGPT Canvas),
    tôn trọng bài viết thủ công trên bàn soạn thảo và cho phép bật/tắt từng chip ngữ cảnh.
    """
    enforce_quota(f"ai:chat:user={current_user.id}")
    cid = req.campaign_id
    campaign = None
    product = None
    brand_kit = None

    if cid is not None:
        campaign = check_campaign_access_for_ai(cid, current_user, db)
        if campaign.product_id:
            product = db.query(Product).filter(Product.id == campaign.product_id).first()
        if campaign.workspace_id:
            brand_kit = db.query(BrandKit).filter(BrandKit.workspace_id == campaign.workspace_id).first()

    target_ws_id = _resolve_ai_workspace_id(db, current_user, campaign, req.workspace_id)
    if not brand_kit and target_ws_id:
        brand_kit = db.query(BrandKit).filter(BrandKit.workspace_id == target_ws_id).first()

    flags = req.context_flags
    product_name = (
        (flags.custom_product_name.strip() if flags.custom_product_name and flags.custom_product_name.strip() else None)
        or (product.name if product and product.name else None)
        or (brand_kit.brand_name if brand_kit and brand_kit.brand_name else None)
        or (campaign.name if campaign else None)
        or ""
    )
    product_usp = (
        (flags.custom_product_usp.strip() if flags.custom_product_usp and flags.custom_product_usp.strip() else None)
        or (product.usp if product and product.usp else None)
        or (product.description if product and product.description else None)
        or (brand_kit.usp if brand_kit and brand_kit.usp else None)
        or (campaign.key_message if campaign and campaign.key_message else None)
        or (campaign.objective if campaign and campaign.objective else None)
        or ""
    )
    audience = (
        (flags.custom_target_audience.strip() if flags.custom_target_audience and flags.custom_target_audience.strip() else None)
        or (campaign.audience if campaign and campaign.audience else None)
        or (brand_kit.target_audience if brand_kit and brand_kit.target_audience else None)
        or ""
    )
    tone = (
        (flags.custom_tone.strip() if flags.custom_tone and flags.custom_tone.strip() else None)
        or (brand_kit.tone_of_voice if brand_kit and brand_kit.tone_of_voice else None)
        or "Tự nhiên, súc tích, đúng thực tế khách hàng Việt Nam"
    )

    import json as _json
    banned_keywords = []
    if brand_kit and brand_kit.banned_keywords_json:
        try:
            banned_keywords = _json.loads(brand_kit.banned_keywords_json)
        except Exception:
            banned_keywords = []

    context_data = {
        "campaign_name": campaign.name if campaign else "",
        "objective": campaign.objective if campaign else "",
        "audience": audience,
        "product_name": product_name,
        "product_usp": product_usp,
        "tone": tone,
        "banned_keywords": ", ".join(banned_keywords) if banned_keywords else "",
        "brand_guidelines": (brand_kit.brand_guidelines or "") if brand_kit else "",
    }

    res = ai_service.chat_with_canvas(
        db=db,
        user_id=current_user.id,
        campaign_id=cid,
        workspace_id=target_ws_id,
        channel_code=req.channel_code,
        message=req.message,
        quick_action=req.quick_action,
        history=[m.model_dump() for m in req.history],
        canvas=req.canvas.model_dump(),
        context_flags=req.context_flags.model_dump(),
        context_data=context_data,
        preferred_provider=req.preferred_provider,
        preferred_model=req.preferred_model,
        custom_base_url=req.custom_base_url,
        thread_id=req.thread_id,
    )
    return AIChatCanvasResponse.model_validate(res)


# ==============================================================================
# HỘI THOẠI DÀI HẠN (PERSISTENT LONG-TERM CHAT THREADS)
# ==============================================================================
def _serialize_chat_thread(
    thread: AIChatThread,
    include_messages: bool = False,
    db: Optional[Session] = None,
) -> AIChatThreadResponse:
    canvas_blocks = []
    if thread.canvas_blocks_json:
        try:
            parsed_blk = json.loads(thread.canvas_blocks_json)
            if isinstance(parsed_blk, list):
                canvas_blocks = parsed_blk
        except Exception:
            canvas_blocks = []
    msgs_out: List[AIChatThreadMessageItem] = []
    if include_messages and db is not None:
        rows = (
            db.query(AIChatThreadMessage)
            .filter(AIChatThreadMessage.thread_id == thread.id)
            .order_by(AIChatThreadMessage.id.asc())
            .all()
        )
        for r in rows:
            sug_c = None
            if r.suggested_canvas_json:
                try:
                    sug_c = json.loads(r.suggested_canvas_json)
                except Exception:
                    sug_c = None
            alts = []
            if r.alternatives_json:
                try:
                    alts = json.loads(r.alternatives_json)
                except Exception:
                    alts = []
            staged = None
            if r.staged_proposal_id and db is not None:
                prop_row = db.query(AgentStagedProposal).filter(AgentStagedProposal.id == r.staged_proposal_id).first()
                if prop_row:
                    staged = _serialize_staged_proposal(prop_row).model_dump()
            msgs_out.append(
                AIChatThreadMessageItem(
                    id=r.id,
                    thread_id=r.thread_id,
                    role=r.role,
                    content=r.content,
                    suggested_canvas=sug_c,
                    alternatives=alts if isinstance(alts, list) else [],
                    staged_proposal_id=r.staged_proposal_id,
                    staged_proposal=staged,
                    model_used=r.model_used,
                    model_provider=r.model_provider,
                    is_fallback=bool(r.is_fallback),
                    created_at=r.created_at,
                )
            )
    msg_count = len(msgs_out)
    if not include_messages and db is not None:
        msg_count = db.query(AIChatThreadMessage).filter(AIChatThreadMessage.thread_id == thread.id).count()
    return AIChatThreadResponse(
        id=thread.id,
        workspace_id=thread.workspace_id,
        user_id=thread.user_id,
        campaign_id=thread.campaign_id,
        title=thread.title,
        channel_code=thread.channel_code or "facebook",
        pinned=bool(thread.pinned),
        is_pinned=bool(thread.pinned),
        summary_memory=thread.summary_memory,
        canvas_blocks=canvas_blocks,
        canvas_snapshot={"blocks": canvas_blocks},
        message_count=msg_count,
        messages=msgs_out,
        created_at=thread.created_at,
        updated_at=thread.updated_at,
    )


@router.get("/threads", response_model=List[AIChatThreadResponse])
def list_chat_threads(
    workspace_id: Optional[int] = None,
    campaign_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lấy danh sách các cuộc trò chuyện dài hạn với AI của người dùng."""
    ws_id = _resolve_ai_workspace_id(db, current_user, None, workspace_id)
    q = db.query(AIChatThread).filter(AIChatThread.user_id == current_user.id)
    if ws_id is not None:
        q = q.filter((AIChatThread.workspace_id == ws_id) | (AIChatThread.workspace_id.is_(None)))
    if campaign_id is not None:
        q = q.filter(AIChatThread.campaign_id == campaign_id)
    rows = q.order_by(AIChatThread.pinned.desc(), AIChatThread.updated_at.desc()).limit(50).all()
    return [_serialize_chat_thread(t, include_messages=False, db=db) for t in rows]


@router.post("/threads", response_model=AIChatThreadResponse, status_code=status.HTTP_201_CREATED)
def create_chat_thread(
    req: AIChatThreadCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Khởi tạo cuộc trò chuyện dài hạn mới với AI."""
    campaign = None
    if req.campaign_id is not None:
        campaign = check_campaign_access_for_ai(req.campaign_id, current_user, db)
    ws_id = _resolve_ai_workspace_id(db, current_user, campaign, req.workspace_id) or 1
    blocks_payload = [b.model_dump() for b in req.canvas_blocks] if req.canvas_blocks else (
        [b.model_dump() for b in req.canvas_snapshot.blocks] if req.canvas_snapshot and req.canvas_snapshot.blocks else []
    )
    thread = AIChatThread(
        workspace_id=ws_id,
        user_id=current_user.id,
        campaign_id=req.campaign_id,
        title=(req.title or "Cuộc trò chuyện mới").strip()[:255],
        channel_code=req.channel_code or "facebook",
        pinned=bool(req.pinned or req.is_pinned),
        canvas_blocks_json=json.dumps(blocks_payload, ensure_ascii=False),
    )
    db.add(thread)
    db.commit()
    db.refresh(thread)
    return _serialize_chat_thread(thread, include_messages=True, db=db)


@router.get("/threads/{thread_id}", response_model=AIChatThreadResponse)
def get_chat_thread_detail(
    thread_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lấy toàn bộ lịch sử tin nhắn và trạng thái bàn viết của 1 cuộc trò chuyện dài hạn."""
    thread = db.query(AIChatThread).filter(AIChatThread.id == thread_id).first()
    if not thread or (thread.user_id != current_user.id and current_user.role != "ADMIN"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy cuộc trò chuyện")
    return _serialize_chat_thread(thread, include_messages=True, db=db)


@router.patch("/threads/{thread_id}", response_model=AIChatThreadResponse)
def update_chat_thread(
    thread_id: int,
    req: AIChatThreadUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Đổi tên, ghim hoặc lưu nhanh trạng thái bàn viết vào cuộc trò chuyện."""
    thread = db.query(AIChatThread).filter(AIChatThread.id == thread_id).first()
    if not thread or (thread.user_id != current_user.id and current_user.role != "ADMIN"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy cuộc trò chuyện")
    if req.title is not None:
        thread.title = req.title.strip()[:255] or thread.title
    if req.channel_code is not None:
        thread.channel_code = req.channel_code
    if req.pinned is not None or req.is_pinned is not None:
        thread.pinned = bool(req.pinned if req.pinned is not None else req.is_pinned)
    if req.summary_memory is not None:
        thread.summary_memory = req.summary_memory
    if req.canvas_blocks is not None:
        thread.canvas_blocks_json = json.dumps([b.model_dump() for b in req.canvas_blocks], ensure_ascii=False)
    elif req.canvas_snapshot is not None and req.canvas_snapshot.blocks:
        thread.canvas_blocks_json = json.dumps([b.model_dump() for b in req.canvas_snapshot.blocks], ensure_ascii=False)
    thread.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(thread)
    return _serialize_chat_thread(thread, include_messages=True, db=db)


@router.delete("/threads/{thread_id}")
def delete_chat_thread(
    thread_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Xóa cuộc trò chuyện và toàn bộ tin nhắn bên trong."""
    thread = db.query(AIChatThread).filter(AIChatThread.id == thread_id).first()
    if not thread or (thread.user_id != current_user.id and current_user.role != "ADMIN"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy cuộc trò chuyện")
    db.query(AIChatThreadMessage).filter(AIChatThreadMessage.thread_id == thread.id).delete()
    db.delete(thread)
    db.commit()
    return {"status": "ok", "deleted_id": thread_id}


# ==============================================================================
# BẢNG TƯ DUY DÀI HẠN & KHO BÀI MẪU RA ĐƠN (MUSE AI SPATIAL MEMORY BOARD)
# ==============================================================================
def _serialize_muse_card(card: MuseBoardCard) -> MuseBoardCardResponse:
    tags_list: List[str] = []
    if card.tags_json:
        try:
            parsed = json.loads(card.tags_json)
            if isinstance(parsed, list):
                tags_list = [str(t) for t in parsed if t]
        except Exception:
            tags_list = []
    return MuseBoardCardResponse(
        id=card.id,
        workspace_id=card.workspace_id,
        user_id=card.user_id,
        campaign_id=card.campaign_id,
        title=card.title,
        card_type=card.card_type,
        content=card.content,
        trigger_command=card.trigger_command,
        skill_trigger=card.trigger_command,
        skill_instruction=card.content,
        tags=tags_list,
        color_theme=card.color_theme or "indigo",
        color_accent=card.color_theme or "indigo",
        is_active_memory=bool(card.is_active_memory),
        is_pinned=bool(card.is_active_memory),
        created_at=card.created_at,
        updated_at=card.updated_at,
    )


@router.get("/muse-cards", response_model=List[MuseBoardCardResponse])
def list_muse_board_cards(
    workspace_id: Optional[int] = None,
    card_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lấy danh sách thẻ trên Bảng Tư Duy Muse AI (Ý tưởng, Bài mẫu ra đơn, Lệnh /skill, Insight)."""
    ws_id = _resolve_ai_workspace_id(db, current_user, None, workspace_id)
    q = db.query(MuseBoardCard)
    if ws_id is not None:
        q = q.filter((MuseBoardCard.workspace_id == ws_id) | (MuseBoardCard.user_id == current_user.id))
    else:
        q = q.filter(MuseBoardCard.user_id == current_user.id)
    if card_type:
        q = q.filter(MuseBoardCard.card_type == card_type.strip().upper())
    cards = q.order_by(MuseBoardCard.is_active_memory.desc(), MuseBoardCard.updated_at.desc()).limit(100).all()
    return [_serialize_muse_card(c) for c in cards]


@router.post("/muse-cards", response_model=MuseBoardCardResponse, status_code=status.HTTP_201_CREATED)
def create_muse_board_card(
    req: MuseBoardCardCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Ghim 1 thẻ mới lên Bảng Tư Duy Muse AI (hoặc thêm Bài Mẫu Ra Đơn / Lệnh tắt /skill)."""
    ws_id = _resolve_ai_workspace_id(db, current_user, None, req.workspace_id) or 1
    raw_trig = req.trigger_command or req.skill_trigger
    trigger_clean = None
    if raw_trig:
        t_raw = raw_trig.strip().lower()
        trigger_clean = t_raw if t_raw.startswith("/") else f"/{t_raw}"
    full_content = req.content.strip()
    if req.skill_instruction and req.skill_instruction.strip() and req.skill_instruction.strip() not in full_content:
        full_content = f"{req.skill_instruction.strip()}\n\n{full_content}"
    card = MuseBoardCard(
        workspace_id=ws_id,
        user_id=current_user.id,
        campaign_id=req.campaign_id,
        title=req.title.strip(),
        card_type=req.card_type,
        content=full_content,
        trigger_command=trigger_clean,
        tags_json=json.dumps(req.tags or [], ensure_ascii=False),
        color_theme=req.color_accent if req.color_accent != "indigo" else (req.color_theme or "indigo"),
        is_active_memory=bool(req.is_pinned if req.is_pinned is not None else req.is_active_memory),
    )
    db.add(card)
    db.commit()
    db.refresh(card)
    return _serialize_muse_card(card)


@router.patch("/muse-cards/{card_id}", response_model=MuseBoardCardResponse)
def update_muse_board_card(
    card_id: int,
    req: MuseBoardCardUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cập nhật nội dung hoặc trạng thái kích hoạt bộ nhớ của thẻ trên Bảng Tư Duy Muse AI."""
    card = db.query(MuseBoardCard).filter(MuseBoardCard.id == card_id).first()
    if not card or (card.user_id != current_user.id and current_user.role != "ADMIN"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy thẻ ghi nhớ")
    if req.title is not None:
        card.title = req.title.strip()
    if req.card_type is not None:
        card.card_type = req.card_type
    if req.content is not None:
        card.content = req.content.strip()
    raw_trig = req.trigger_command if req.trigger_command is not None else req.skill_trigger
    if raw_trig is not None:
        t_raw = raw_trig.strip().lower()
        card.trigger_command = (t_raw if t_raw.startswith("/") else f"/{t_raw}") if t_raw else None
    if req.tags is not None:
        card.tags_json = json.dumps(req.tags, ensure_ascii=False)
    if req.color_theme is not None or req.color_accent is not None:
        card.color_theme = req.color_accent or req.color_theme or card.color_theme
    if req.is_active_memory is not None or req.is_pinned is not None:
        card.is_active_memory = bool(req.is_pinned if req.is_pinned is not None else req.is_active_memory)
    card.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(card)
    return _serialize_muse_card(card)


@router.delete("/muse-cards/{card_id}")
def delete_muse_board_card(
    card_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Xóa thẻ khỏi Bảng Tư Duy Muse AI."""
    card = db.query(MuseBoardCard).filter(MuseBoardCard.id == card_id).first()
    if not card or (card.user_id != current_user.id and current_user.role != "ADMIN"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy thẻ ghi nhớ")
    db.delete(card)
    db.commit()
    return {"status": "ok", "deleted_id": card_id}


# ==============================================================================
# ĐIỀU KHIỂN DỰ ÁN BẰNG LLM (STAGED PROPOSAL EXECUTION & ATOMIC UNDO ROLLBACK)
# ==============================================================================
def _serialize_staged_proposal(prop: AgentStagedProposal) -> AgentStagedProposalResponse:
    actions = []
    if prop.actions_json:
        try:
            actions = json.loads(prop.actions_json)
            if isinstance(actions, list):
                for a in actions:
                    if isinstance(a, dict):
                        a.setdefault("summary", a.get("description") or "")
                        a.setdefault("description", a.get("summary") or "")
                        a.setdefault("parameters", a.get("params") or {})
                        a.setdefault("params", a.get("parameters") or {})
        except Exception:
            actions = []
    exec_res = None
    if prop.execution_result_json:
        try:
            exec_res = json.loads(prop.execution_result_json)
        except Exception:
            exec_res = None
    return AgentStagedProposalResponse(
        id=prop.id,
        workspace_id=prop.workspace_id,
        thread_id=prop.thread_id,
        goal_summary=prop.goal_summary,
        summary=prop.goal_summary,
        status=prop.status,
        actions=actions if isinstance(actions, list) else [],
        execution_result=exec_res if isinstance(exec_res, dict) else None,
        executed_result=exec_res if isinstance(exec_res, dict) else None,
        can_undo=(prop.status == "EXECUTED" and bool(prop.rollback_snapshot_json)),
        created_at=prop.created_at,
        executed_at=prop.executed_at,
        rolled_back_at=prop.rolled_back_at,
    )


@router.post("/proposals/{proposal_id}/execute", response_model=AgentStagedProposalResponse)
def execute_staged_proposal(
    proposal_id: int,
    req: AgentExecuteProposalRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Thực thi nguyên tử (Atomic Commit) các hành động trong Thẻ Kế Hoạch đã được người dùng kiểm duyệt,
    đồng thời ghi lại `rollback_snapshot_json` để cho phép bấm [Hoàn tác (Undo)] chỉ với 1 cú nhấp.
    """
    from app.models.entities import ProductCategory
    from app.api.v1.contents import _resolve_or_create_scratchpad_campaign

    prop = db.query(AgentStagedProposal).filter(AgentStagedProposal.id == proposal_id).first()
    if not prop or (prop.user_id != current_user.id and current_user.role != "ADMIN"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy đề xuất thao tác")
    if prop.status != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Đề xuất đang ở trạng thái '{prop.status}', chỉ có thể thực thi khi ở trạng thái PENDING.",
        )

    ws_id = prop.workspace_id or _resolve_ai_workspace_id(db, current_user, None, None) or 1
    override_src = req.override_actions if req.override_actions is not None else req.overridden_actions
    actions_list = (
        [a.model_dump() for a in override_src]
        if override_src is not None
        else (json.loads(prop.actions_json) if prop.actions_json else [])
    )

    created_campaign_ids: List[int] = []
    created_content_ids: List[int] = []
    created_task_ids: List[int] = []
    created_metric_ids: List[int] = []
    created_muse_card_ids: List[int] = []
    created_product_ids: List[int] = []
    updated_campaigns_prev: List[Dict[str, Any]] = []
    updated_products_prev: List[Dict[str, Any]] = []
    updated_brand_kits_prev: List[Dict[str, Any]] = []
    updated_tasks_prev: List[Dict[str, Any]] = []
    updated_contents_prev: List[Dict[str, Any]] = []
    active_campaign_id: Optional[int] = None

    for act in actions_list:
        if not isinstance(act, dict) or not act.get("enabled", True):
            continue
        if req.selected_action_ids and act.get("action_id") not in req.selected_action_ids:
            continue
        tname = str(act.get("tool_name") or "").strip()
        params = act.get("params") or act.get("parameters") or {}
        if not isinstance(params, dict):
            params = {}

        if tname == "propose_campaign_plan":
            prod = db.query(Product).order_by(Product.id.asc()).first()
            if not prod:
                cat = db.query(ProductCategory).order_by(ProductCategory.id.asc()).first()
                if not cat:
                    cat = ProductCategory(name="Danh mục Chung", description="Danh mục mặc định")
                    db.add(cat)
                    db.flush()
                prod = Product(
                    category_id=cat.id,
                    name=str(params.get("name") or "Sản phẩm Chủ lực"),
                    usp="Tối ưu chuyển đổi thực tế",
                    status="ACTIVE",
                )
                db.add(prod)
                db.flush()

            new_camp = Campaign(
                workspace_id=ws_id,
                product_id=prod.id,
                owner_id=current_user.id,
                name=str(params.get("name") or "Chiến dịch mới từ AI Agent")[:255],
                objective=str(params.get("objective") or "Tối ưu chuyển đổi tin nhắn & đơn hàng"),
                audience=str(params.get("audience") or "Khách hàng mục tiêu"),
                start_date=str(params.get("start_date") or datetime.utcnow().strftime("%Y-%m-%d")),
                end_date=str(params.get("end_date") or "2026-12-31"),
                budget=float(params.get("budget") or 0.0),
                status="ACTIVE",
                funnel_stage="BoFU",
            )
            db.add(new_camp)
            db.flush()
            created_campaign_ids.append(new_camp.id)
            active_campaign_id = new_camp.id

        elif tname == "update_campaign":
            target_camp_id = params.get("campaign_id") or active_campaign_id
            camp_q = db.query(Campaign)
            if target_camp_id:
                camp_obj = camp_q.filter(Campaign.id == int(target_camp_id)).first()
            else:
                camp_obj = camp_q.filter(Campaign.workspace_id == ws_id).order_by(Campaign.id.desc()).first()
            if camp_obj:
                updated_campaigns_prev.append({
                    "id": camp_obj.id,
                    "name": camp_obj.name,
                    "status": camp_obj.status,
                    "budget": float(camp_obj.budget or 0.0),
                    "objective": camp_obj.objective,
                })
                if params.get("status") in ("ACTIVE", "PAUSED", "COMPLETED", "DRAFT"):
                    camp_obj.status = str(params["status"])
                if params.get("budget") is not None and float(params.get("budget") or 0) > 0:
                    camp_obj.budget = float(params["budget"])
                if params.get("name"):
                    camp_obj.name = str(params["name"])[:255]
                if params.get("objective"):
                    camp_obj.objective = str(params["objective"])
                db.flush()
                active_campaign_id = camp_obj.id

        elif tname == "upsert_product":
            prod_id = params.get("product_id")
            prod_obj = None
            if prod_id:
                prod_obj = db.query(Product).filter(Product.id == int(prod_id)).first()
            elif params.get("name"):
                prod_obj = db.query(Product).filter(Product.name == str(params["name"]).strip()).first()
            if prod_obj:
                updated_products_prev.append({
                    "id": prod_obj.id,
                    "name": prod_obj.name,
                    "usp": prod_obj.usp,
                    "status": prod_obj.status,
                })
                if params.get("name"):
                    prod_obj.name = str(params["name"])[:255]
                if params.get("usp"):
                    prod_obj.usp = str(params["usp"])
                if params.get("status") in ("ACTIVE", "ARCHIVED"):
                    prod_obj.status = str(params["status"])
                db.flush()
            else:
                cat = db.query(ProductCategory).order_by(ProductCategory.id.asc()).first()
                if not cat:
                    cat = ProductCategory(name="Danh mục Chung", description="Danh mục mặc định")
                    db.add(cat)
                    db.flush()
                new_prod = Product(
                    category_id=cat.id,
                    name=str(params.get("name") or "Sản phẩm Mới")[:255],
                    usp=str(params.get("usp") or "Điểm mạnh thực chiến"),
                    status="ACTIVE",
                )
                db.add(new_prod)
                db.flush()
                created_product_ids.append(new_prod.id)

        elif tname == "update_brand_kit":
            bk = db.query(BrandKit).filter(BrandKit.workspace_id == ws_id).order_by(BrandKit.id.desc()).first()
            if bk:
                updated_brand_kits_prev.append({
                    "id": bk.id,
                    "voice_tone": bk.voice_tone,
                    "banned_words": bk.banned_words,
                })
                if params.get("voice_tone"):
                    bk.voice_tone = str(params["voice_tone"])[:255]
                if params.get("banned_words") is not None:
                    bk.banned_words = str(params["banned_words"])
                db.flush()

        elif tname == "propose_content_drafts":
            target_camp_id = params.get("campaign_id") or active_campaign_id
            if not target_camp_id:
                scratch_camp = _resolve_or_create_scratchpad_campaign(db, current_user, ws_id)
                target_camp_id = scratch_camp.id
            ch_code = str(params.get("channel_code") or "facebook").lower()
            ch_row = db.query(MarketingChannel).filter(MarketingChannel.code == ch_code).first()
            if not ch_row:
                ch_row = db.query(MarketingChannel).order_by(MarketingChannel.id.asc()).first()
            ch_id = ch_row.id if ch_row else 1
            blocks_val = params.get("blocks")
            blocks_str = json.dumps(blocks_val, ensure_ascii=False) if isinstance(blocks_val, list) else "[]"
            new_cnt = MarketingContent(
                workspace_id=ws_id,
                campaign_id=int(target_camp_id),
                channel_id=ch_id,
                created_by=current_user.id,
                title=str(params.get("title") or "Bài viết nháp từ AI Copilot")[:255],
                body=str(params.get("body") or "Nội dung bài viết"),
                cta=str(params.get("cta") or "Nhắn tin ngay"),
                status="DRAFT",
                blocks_json=blocks_str,
            )
            db.add(new_cnt)
            db.flush()
            created_content_ids.append(new_cnt.id)

        elif tname == "update_content_status":
            cnt_id = params.get("content_id")
            cnt_q = db.query(MarketingContent).filter(MarketingContent.workspace_id == ws_id)
            cnt_obj = cnt_q.filter(MarketingContent.id == int(cnt_id)).first() if cnt_id else cnt_q.order_by(MarketingContent.id.desc()).first()
            if cnt_obj:
                updated_contents_prev.append({"id": cnt_obj.id, "status": cnt_obj.status})
                new_st = str(params.get("status") or "APPROVED").upper()
                if new_st in ("DRAFT", "IN_REVIEW", "APPROVED", "REJECTED", "PUBLISHED"):
                    cnt_obj.status = new_st
                db.flush()

        elif tname == "propose_tasks_batch":
            target_camp_id = params.get("campaign_id") or active_campaign_id
            if not target_camp_id:
                scratch_camp = _resolve_or_create_scratchpad_campaign(db, current_user, ws_id)
                target_camp_id = scratch_camp.id
            t_items = params.get("tasks") if isinstance(params.get("tasks"), list) else []
            for t_item in t_items[:10]:
                if not isinstance(t_item, dict):
                    continue
                t_type = str(t_item.get("task_type") or "CONTENT").upper()
                if t_type not in ("RESEARCH", "CONTENT", "DESIGN", "ADS", "OTHER"):
                    t_type = "OTHER"
                t_prio = str(t_item.get("priority") or "MEDIUM").upper()
                if t_prio not in ("LOW", "MEDIUM", "HIGH", "URGENT"):
                    t_prio = "MEDIUM"
                new_task = Task(
                    workspace_id=ws_id,
                    campaign_id=int(target_camp_id),
                    assignee_id=current_user.id,
                    creator_id=current_user.id,
                    title=str(t_item.get("title") or "Việc cần làm")[:255],
                    description=str(t_item.get("description") or "Khởi tạo từ AI Project Control"),
                    task_type=t_type,
                    priority=t_prio,
                    status="TODO",
                )
                db.add(new_task)
                db.flush()
                created_task_ids.append(new_task.id)

        elif tname == "update_tasks_status":
            target_camp_id = params.get("campaign_id") or active_campaign_id
            new_st = str(params.get("new_status") or "DONE").upper()
            if new_st not in ("TODO", "IN_PROGRESS", "DONE"):
                new_st = "DONE"
            tq = db.query(Task).filter(Task.workspace_id == ws_id)
            if target_camp_id:
                tq = tq.filter(Task.campaign_id == int(target_camp_id))
            task_ids_param = params.get("task_ids")
            if isinstance(task_ids_param, list) and task_ids_param:
                tq = tq.filter(Task.id.in_([int(x) for x in task_ids_param if str(x).isdigit()]))
            else:
                tq = tq.filter(Task.status != new_st)
            for t_obj in tq.limit(10).all():
                updated_tasks_prev.append({"id": t_obj.id, "status": t_obj.status})
                t_obj.status = new_st
            db.flush()

        elif tname == "log_daily_metrics":
            target_camp_id = params.get("campaign_id") or active_campaign_id
            if not target_camp_id:
                scratch_camp = _resolve_or_create_scratchpad_campaign(db, current_user, ws_id)
                target_camp_id = scratch_camp.id
            ch_code = str(params.get("channel_code") or "facebook").lower()
            ch_row = db.query(MarketingChannel).filter(MarketingChannel.code == ch_code).first()
            if not ch_row:
                ch_row = db.query(MarketingChannel).order_by(MarketingChannel.id.asc()).first()
            ch_id = ch_row.id if ch_row else 1
            clicks_val = max(0, int(params.get("clicks") or 0))
            views_val = max(clicks_val, int(params.get("views") or 0))
            m_date = str(params.get("report_date") or params.get("metric_date") or datetime.utcnow().strftime("%Y-%m-%d"))
            new_metric = CampaignMetric(
                campaign_id=int(target_camp_id),
                channel_id=ch_id,
                metric_date=m_date,
                views=views_val,
                clicks=clicks_val,
                conversions=max(0, int(params.get("conversions") or 0)),
                cost=max(0.0, float(params.get("cost") or 0.0)),
                revenue=max(0.0, float(params.get("revenue") or 0.0)),
            )
            db.add(new_metric)
            db.flush()
            created_metric_ids.append(new_metric.id)

        elif tname == "create_tracking_link":
            short_code = str(params.get("short_code") or "mf_link").strip()
            target_url = str(params.get("target_url") or "https://zalo.me").strip()
            new_card = MuseBoardCard(
                workspace_id=ws_id,
                user_id=current_user.id,
                campaign_id=params.get("campaign_id") or active_campaign_id,
                title=str(params.get("title") or f"Smart Link /r/{short_code}")[:255],
                card_type="INSIGHT",
                content=f"Smart Tracking Link: /r/{short_code} -> {target_url} (Kênh: {params.get('channel_code') or 'facebook'})",
                tags_json=json.dumps(["smart_link", short_code], ensure_ascii=False),
                color_theme="indigo",
                is_active_memory=True,
            )
            db.add(new_card)
            db.flush()
            created_muse_card_ids.append(new_card.id)

        elif tname in ("save_custom_skill", "pin_muse_memory_card"):
            is_skill = tname == "save_custom_skill"
            trig_clean = None
            if is_skill:
                trig_raw = str(params.get("skill_trigger") or params.get("trigger_command") or "/viet_nhanh").strip().lower()
                trig_clean = trig_raw if trig_raw.startswith("/") else f"/{trig_raw}"
            c_type = "CUSTOM_SKILL" if is_skill else str(params.get("card_type") or "INSIGHT").upper()
            if c_type not in ("IDEA", "WINNING_POST", "CUSTOM_SKILL", "INSIGHT", "NOTE"):
                c_type = "INSIGHT"
            new_card = MuseBoardCard(
                workspace_id=ws_id,
                user_id=current_user.id,
                campaign_id=active_campaign_id,
                title=str(params.get("title") or (f"Lệnh tùy biến {trig_clean}" if is_skill else "Thẻ nhớ Muse AI"))[:255],
                card_type=c_type,
                content=str(params.get("content") or params.get("skill_instruction") or ""),
                trigger_command=trig_clean,
                color_theme="emerald" if is_skill else "indigo",
                is_active_memory=True,
            )
            db.add(new_card)
            db.flush()
            created_muse_card_ids.append(new_card.id)

    snapshot = {
        "created_campaign_ids": created_campaign_ids,
        "created_content_ids": created_content_ids,
        "created_task_ids": created_task_ids,
        "created_metric_ids": created_metric_ids,
        "created_muse_card_ids": created_muse_card_ids,
        "created_product_ids": created_product_ids,
        "updated_campaigns_prev": updated_campaigns_prev,
        "updated_products_prev": updated_products_prev,
        "updated_brand_kits_prev": updated_brand_kits_prev,
        "updated_tasks_prev": updated_tasks_prev,
        "updated_contents_prev": updated_contents_prev,
    }
    exec_summary = {
        "campaigns_created": len(created_campaign_ids),
        "campaigns_updated": len(updated_campaigns_prev),
        "products_upserted": len(created_product_ids) + len(updated_products_prev),
        "contents_created": len(created_content_ids),
        "tasks_created": len(created_task_ids),
        "tasks_updated": len(updated_tasks_prev),
        "metrics_logged": len(created_metric_ids),
        "skills_saved": len(created_muse_card_ids),
        "ids": snapshot,
    }
    prop.actions_json = json.dumps(actions_list, ensure_ascii=False)
    prop.rollback_snapshot_json = json.dumps(snapshot, ensure_ascii=False)
    prop.execution_result_json = json.dumps(exec_summary, ensure_ascii=False)
    prop.status = "EXECUTED"
    prop.executed_at = datetime.utcnow()
    db.commit()
    db.refresh(prop)
    return _serialize_staged_proposal(prop)


@router.post("/proposals/{proposal_id}/undo", response_model=AgentStagedProposalResponse)
def undo_staged_proposal(
    proposal_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Hoàn tác nguyên tử (Atomic Undo Rollback) toàn bộ bản ghi vừa được tạo hoặc sửa bởi Thẻ Kế Hoạch."""
    prop = db.query(AgentStagedProposal).filter(AgentStagedProposal.id == proposal_id).first()
    if not prop or (prop.user_id != current_user.id and current_user.role != "ADMIN"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy đề xuất thao tác")
    if prop.status != "EXECUTED" or not prop.rollback_snapshot_json:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chỉ có thể hoàn tác (Undo) đề xuất đã thực thi (EXECUTED).",
        )

    snap = json.loads(prop.rollback_snapshot_json)
    for tid in snap.get("created_task_ids", []):
        db.query(Task).filter(Task.id == tid).delete()
    for cid in snap.get("created_content_ids", []):
        db.query(MarketingContent).filter(MarketingContent.id == cid).delete()
    for mid in snap.get("created_metric_ids", []):
        db.query(CampaignMetric).filter(CampaignMetric.id == mid).delete()
    for mcid in snap.get("created_muse_card_ids", []):
        db.query(MuseBoardCard).filter(MuseBoardCard.id == mcid).delete()
    for camp_id in snap.get("created_campaign_ids", []):
        db.query(Campaign).filter(Campaign.id == camp_id).delete()
    for prod_id in snap.get("created_product_ids", []):
        db.query(Product).filter(Product.id == prod_id).delete()

    for c_prev in snap.get("updated_campaigns_prev", []):
        c_row = db.query(Campaign).filter(Campaign.id == c_prev.get("id")).first()
        if c_row:
            c_row.name = c_prev.get("name", c_row.name)
            c_row.status = c_prev.get("status", c_row.status)
            c_row.budget = c_prev.get("budget", c_row.budget)
            c_row.objective = c_prev.get("objective", c_row.objective)
    for p_prev in snap.get("updated_products_prev", []):
        p_row = db.query(Product).filter(Product.id == p_prev.get("id")).first()
        if p_row:
            p_row.name = p_prev.get("name", p_row.name)
            p_row.usp = p_prev.get("usp", p_row.usp)
            p_row.status = p_prev.get("status", p_row.status)
    for bk_prev in snap.get("updated_brand_kits_prev", []):
        bk_row = db.query(BrandKit).filter(BrandKit.id == bk_prev.get("id")).first()
        if bk_row:
            bk_row.voice_tone = bk_prev.get("voice_tone", bk_row.voice_tone)
            bk_row.banned_words = bk_prev.get("banned_words", bk_row.banned_words)
    for t_prev in snap.get("updated_tasks_prev", []):
        t_row = db.query(Task).filter(Task.id == t_prev.get("id")).first()
        if t_row:
            t_row.status = t_prev.get("status", t_row.status)
    for cnt_prev in snap.get("updated_contents_prev", []):
        cnt_row = db.query(MarketingContent).filter(MarketingContent.id == cnt_prev.get("id")).first()
        if cnt_row:
            cnt_row.status = cnt_prev.get("status", cnt_row.status)

    prop.status = "ROLLED_BACK"
    prop.rolled_back_at = datetime.utcnow()
    db.commit()
    db.refresh(prop)
    return _serialize_staged_proposal(prop)


@router.get("/logs", response_model=Page[AILogResponse])
def get_ai_logs(
    campaign_id: Optional[int] = None,
    result_status: Optional[str] = Query(None, alias="status"),
    pagination: PageParams = Depends(page_params),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Nhật ký lượt gọi AI, có phân trang.

    Trước đây `limit(50)` được hardcode và response là mảng phẳng — client không
    biết còn bao nhiêu log nên không thể lọc theo trạng thái hay xem trang sau.
    """
    query = db.query(AILog)
    if campaign_id:
        if current_user.role not in ("ADMIN", "MANAGER"):
            check_campaign_access_for_ai(campaign_id, current_user, db)
        query = query.filter(AILog.campaign_id == campaign_id)
    elif current_user.role != "ADMIN":
        query = query.filter(AILog.user_id == current_user.id)
    if result_status:
        query = query.filter(AILog.result_status == result_status)

    return paginate_query(
        query.order_by(AILog.id.desc()),
        pagination,
        serializer=lambda log: AILogResponse.model_validate(log),
    )
