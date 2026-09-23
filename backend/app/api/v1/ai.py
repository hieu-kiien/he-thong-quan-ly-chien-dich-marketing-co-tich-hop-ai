from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.entities import Campaign, MarketingChannel, Product, CampaignMetric, AILog, User
from app.schemas.schemas import (
    AIIdeaRequest, AIIdeaResponse,
    AIDraftRequest, AIDraftResponse,
    AISummaryRequest, AISummaryResponse
)
from app.services.ai.ai_service import ai_service

router = APIRouter(prefix="/ai", tags=["Tính năng Trí Tuệ Nhân Tạo (AI Engine)"])

@router.post("/ideas", response_model=AIIdeaResponse)
def generate_ideas(
    req: AIIdeaRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user_id = current_user.id
    cid = req.campaign_id

    if cid is not None:
        campaign = db.query(Campaign).filter(Campaign.id == cid).first()
        if not campaign:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chiến dịch không tồn tại")
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
def generate_draft(
    req: AIDraftRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user_id = current_user.id
    cid = req.campaign_id

    if cid is not None:
        campaign = db.query(Campaign).filter(Campaign.id == cid).first()
        if not campaign:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chiến dịch không tồn tại")
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
def generate_summary(
    req: AISummaryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user_id = current_user.id

    campaign = db.query(Campaign).filter(Campaign.id == req.campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chiến dịch không tồn tại")

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

@router.get("/logs")
def get_ai_logs(
    campaign_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(AILog)
    if campaign_id:
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
