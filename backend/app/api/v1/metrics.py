from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.entities import CampaignMetric, Campaign, MarketingChannel, User
from app.schemas.schemas import MetricCreate, MetricResponse, KPISummaryResponse

router = APIRouter(prefix="", tags=["Chỉ số Hiệu quả & KPI Dashboard"])

@router.get("/campaigns/{campaign_id}/metrics", response_model=List[MetricResponse])
def get_campaign_metrics(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chiến dịch không tồn tại")

    metrics = db.query(CampaignMetric).filter(CampaignMetric.campaign_id == campaign_id).order_by(CampaignMetric.metric_date.desc()).all()
    return [MetricResponse.model_validate(m) for m in metrics]

@router.post("/campaigns/{campaign_id}/metrics", response_model=MetricResponse, status_code=status.HTTP_201_CREATED)
def record_campaign_metric(
    campaign_id: int,
    req: MetricCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chiến dịch không tồn tại")

    channel = db.query(MarketingChannel).filter(MarketingChannel.id == req.channel_id).first()
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kênh không tồn tại")

    # BUG-BE-03: Kiểm tra metric trùng lặp (campaign_id, channel_id, metric_date)
    existing_metric = db.query(CampaignMetric).filter(
        CampaignMetric.campaign_id == campaign_id,
        CampaignMetric.channel_id == req.channel_id,
        CampaignMetric.metric_date == req.metric_date
    ).first()
    if existing_metric:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Chỉ số cho chiến dịch {campaign_id}, kênh {req.channel_id} vào ngày {req.metric_date} đã tồn tại."
        )

    metric = CampaignMetric(
        campaign_id=campaign_id,
        channel_id=req.channel_id,
        metric_date=req.metric_date,
        views=req.views,
        clicks=req.clicks,
        conversions=req.conversions,
        cost=req.cost,
        revenue=req.revenue
    )
    db.add(metric)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Chỉ số cho chiến dịch, kênh và ngày này đã tồn tại."
        )
    db.refresh(metric)
    return MetricResponse.model_validate(metric)

@router.get("/campaigns/{campaign_id}/kpi", response_model=KPISummaryResponse)
def get_campaign_kpi(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chiến dịch không tồn tại")

    metrics = db.query(CampaignMetric).filter(CampaignMetric.campaign_id == campaign_id).all()
    
    total_views = sum(m.views for m in metrics)
    total_clicks = sum(m.clicks for m in metrics)
    total_conversions = sum(m.conversions for m in metrics)
    total_cost = sum(float(m.cost) for m in metrics)
    total_revenue = sum(float(m.revenue) for m in metrics)

    # Chống chia cho 0 an toàn (ZeroDivisionError Protection)
    ctr = (total_clicks / total_views * 100.0) if total_views > 0 else 0.0
    cpc = (total_cost / total_clicks) if total_clicks > 0 else 0.0
    cvr = (total_conversions / total_clicks * 100.0) if total_clicks > 0 else 0.0
    roi = ((total_revenue - total_cost) / total_cost * 100.0) if total_cost > 0 else 0.0

    return KPISummaryResponse(
        total_views=total_views,
        total_clicks=total_clicks,
        total_conversions=total_conversions,
        total_cost=round(total_cost, 2),
        total_revenue=round(total_revenue, 2),
        ctr_percent=round(ctr, 2),
        cpc_avg=round(cpc, 2),
        cvr_percent=round(cvr, 2),
        roi_percent=round(roi, 2)
    )

@router.get("/analytics/dashboard")
def get_global_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    metrics = db.query(CampaignMetric).all()
    total_views = sum(m.views for m in metrics)
    total_clicks = sum(m.clicks for m in metrics)
    total_conversions = sum(m.conversions for m in metrics)
    total_cost = sum(float(m.cost) for m in metrics)
    total_revenue = sum(float(m.revenue) for m in metrics)

    ctr = (total_clicks / total_views * 100.0) if total_views > 0 else 0.0
    cpc = (total_cost / total_clicks) if total_clicks > 0 else 0.0
    cvr = (total_conversions / total_clicks * 100.0) if total_clicks > 0 else 0.0
    roi = ((total_revenue - total_cost) / total_cost * 100.0) if total_cost > 0 else 0.0

    campaigns_count = db.query(Campaign).count()
    active_campaigns = db.query(Campaign).filter(Campaign.status == "ACTIVE").count()

    return {
        "kpi": {
            "total_views": total_views,
            "total_clicks": total_clicks,
            "total_conversions": total_conversions,
            "total_cost": round(total_cost, 2),
            "total_revenue": round(total_revenue, 2),
            "ctr_percent": round(ctr, 2),
            "cpc_avg": round(cpc, 2),
            "cvr_percent": round(cvr, 2),
            "roi_percent": round(roi, 2),
        },
        "campaigns_summary": {
            "total": campaigns_count,
            "active": active_campaigns
        }
    }
