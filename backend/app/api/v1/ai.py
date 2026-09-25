from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.entities import Campaign, MarketingChannel, Product, CampaignMetric, AILog, User, CampaignMember, BrandKit, Workspace, WorkspaceMember
from app.schemas.schemas import (
    AIIdeaRequest, AIIdeaResponse,
    AIDraftRequest, AIDraftResponse,
    AISummaryRequest, AISummaryResponse,
    OmnichannelRequest, OmnichannelResponse
)
from app.services.ai.ai_service import ai_service

router = APIRouter(prefix="/ai", tags=["Tính năng Trí Tuệ Nhân Tạo (AI Engine)"])

def check_campaign_access_for_ai(campaign_id: int, user: User, db: Session) -> Campaign:
    """Xác thực phân quyền mức bản ghi và cách ly đa người thuê (Tenant Isolation):
    - User ADMIN có toàn quyền truy cập AI Context của bất kỳ chiến dịch nào.
    - User MANAGER / AGENCY_MANAGER:
      + Nếu campaign.workspace_id is None hoặc <= 1: cho qua (tương thích ngược legacy tests).
      + Nếu campaign.workspace_id > 1: bắt buộc user phải là owner hoặc member của workspace đó.
    - User MARKETER hoặc role khác:
      + Nếu campaign.workspace_id > 1: kiểm tra workspace isolation.
      + Đồng thời user chỉ được thao tác trên campaign mà họ sở hữu (owner_id) HOẶC là thành viên chiến dịch (CampaignMember).
    """
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chiến dịch không tồn tại")

    if user.role == "ADMIN":
        return campaign

    # Kiểm tra Tenant Isolation đối với các workspace cụ thể (> 1)
    if campaign.workspace_id is not None and campaign.workspace_id > 1:
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

@router.post("/ideas", response_model=AIIdeaResponse)
def generate_ideas(
    req: AIIdeaRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user_id = current_user.id
    cid = req.campaign_id

    if cid is not None:
        campaign = check_campaign_access_for_ai(cid, current_user, db)
        product = db.query(Product).filter(Product.id == campaign.product_id).first()
        channel = db.query(MarketingChannel).filter(MarketingChannel.code == req.channel_code).first()
        campaign_name = campaign.name
        objective = campaign.objective
        audience = campaign.audience
        product_name = product.name if product else "Sản phẩm"
        product_usp = product.usp if product else "Chất lượng vượt trội"
    else:
        channel = db.query(MarketingChannel).filter(MarketingChannel.code == req.channel_code).first()
        campaign_name = req.custom_topic or "Chiến dịch Tiếp thị Tự do"
        objective = "Thu hút khách hàng tiềm năng và tối ưu hóa chuyển đổi"
        audience = "Khách hàng mục tiêu trên kênh kỹ thuật số"
        product_name = req.custom_product or req.custom_topic or "Sản phẩm Tiếp thị"
        product_usp = req.custom_usp or "Chất lượng vượt trội, ưu đãi hấp dẫn"

    campaign_brief = f"{campaign_name} - Mục tiêu: {objective} - Đối tượng: {audience} - Sản phẩm: {product_name}"
    context = {
        "campaign_name": campaign_name,
        "campaign_brief": campaign_brief,
        "objective": objective,
        "audience": audience,
        "product_name": product_name,
        "product_usp": product_usp,
        "channel_name": channel.name if channel else req.channel_code,
        "tone": req.tone
    }

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

@router.post("/draft", response_model=AIDraftResponse)
@router.post("/generate", response_model=AIDraftResponse)
def generate_draft(
    req: AIDraftRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user_id = current_user.id
    cid = req.campaign_id

    if cid is not None:
        campaign = check_campaign_access_for_ai(cid, current_user, db)
        product = db.query(Product).filter(Product.id == campaign.product_id).first()
        channel = db.query(MarketingChannel).filter(MarketingChannel.code == req.channel_code).first()
        campaign_name = campaign.name
        product_name = product.name if product else "Sản phẩm"
        product_usp = product.usp if product else "Chất lượng vượt trội"
    else:
        channel = db.query(MarketingChannel).filter(MarketingChannel.code == req.channel_code).first()
        campaign_name = "Chiến dịch Tiếp thị Tự do"
        product_name = req.custom_product or "Sản phẩm Tiếp thị"
        product_usp = req.custom_usp or "Chất lượng vượt trội, ưu đãi hấp dẫn"

    campaign_brief = f"{campaign_name} - Sản phẩm: {product_name} - USP: {product_usp}"
    context = {
        "campaign_name": campaign_name,
        "campaign_brief": campaign_brief,
        "product_name": product_name,
        "product_usp": product_usp,
        "channel_name": channel.name if channel else req.channel_code,
        "channel_rules": channel.format_rules if channel else "Viết hấp dẫn, súc tích",
        "selected_idea": req.selected_idea
    }

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

@router.post("/summary", response_model=AISummaryResponse)
@router.post("/summarize", response_model=AISummaryResponse)
def generate_summary(
    req: AISummaryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
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

@router.post("/omnichannel", response_model=OmnichannelResponse, response_model_exclude_none=True)
def generate_omnichannel(
    req: OmnichannelRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deep 3-Channel AI Creative Engine (R2):
    Sinh trọn bộ tài sản tiếp thị Facebook, TikTok và Email từ 1 brief duy nhất,
    kế thừa Brand Kit (USP, Tone, Banned Keywords) của Workspace.
    """
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
        brand_kit = db.query(BrandKit).filter(BrandKit.id == req.brand_kit_id).first()

    if not brand_kit:
        brand_kit = db.query(BrandKit).first()

    # Kế thừa thông số Brand Kit
    brand_name = brand_kit.brand_name if brand_kit else (product.name if product else "MarketFlow AI")
    usp = req.product_usp or (brand_kit.usp if brand_kit and brand_kit.usp else (product.usp if product else "Nền tảng Tiếp thị Đột phá"))
    tone_of_voice = req.tone or (brand_kit.tone_of_voice if brand_kit and brand_kit.tone_of_voice else "Chuyên nghiệp, hiện đại, tin cậy")

    import json
    banned_keywords = []
    if brand_kit and brand_kit.banned_keywords_json:
        try:
            banned_keywords = json.loads(brand_kit.banned_keywords_json)
        except Exception:
            banned_keywords = []

    target_audience = req.target_audience or (campaign.audience if campaign else "Đại chúng")
    product_name = req.product_name or (product.name if product else (campaign.name if campaign else "Sản phẩm Tiếp thị"))
    campaign_name = campaign.name if campaign else "Chiến dịch Tiếp thị Đa kênh"

    requested_channels = req.channels if req.channels else ["facebook", "tiktok", "email"]

    context = {
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

    def filter_channels(data: dict) -> dict:
        res = dict(data)
        if "facebook" not in requested_channels:
            res["facebook"] = None
        if "tiktok" not in requested_channels:
            res["tiktok"] = None
        if "email" not in requested_channels:
            res["email"] = None
        res["campaign_id"] = cid
        res["model_used"] = "gemini-2.5-flash"
        res["prompt_version"] = req.prompt_version
        res["task_type"] = "OMNICHANNEL"
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
            fallback["model_used"] = "gemini-2.5-flash"
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
            fallback["model_used"] = "gemini-2.5-flash"
            fallback["prompt_version"] = req.prompt_version
            fallback["task_type"] = "OMNICHANNEL"
            fallback.setdefault("warnings", []).append(f"Dịch vụ AI gặp sự cố ({str(e)}), đã kích hoạt Smart Fallback.")
            filtered_fallback = filter_channels(fallback)
            return OmnichannelResponse.model_validate(filtered_fallback)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Lỗi dịch vụ AI: {str(e)}")

@router.get("/logs")
def get_ai_logs(
    campaign_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(AILog)
    if campaign_id:
        if current_user.role not in ("ADMIN", "MANAGER"):
            check_campaign_access_for_ai(campaign_id, current_user, db)
        query = query.filter(AILog.campaign_id == campaign_id)
    logs = query.order_by(AILog.id.desc()).limit(50).all()
    return [
        {
            "id": l.id,
            "task_type": l.task_type,
            "model": l.model,
            "prompt_version": l.prompt_version,
            "result_status": l.result_status,
            "latency_ms": l.latency_ms,
            "error_code": l.error_code,
            "created_at": l.created_at.isoformat() if l.created_at else None
        }
        for l in logs
    ]
