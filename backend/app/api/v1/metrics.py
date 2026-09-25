from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.entities import CampaignMetric, Campaign, MarketingChannel, User, CampaignMember, Workspace, WorkspaceMember
from app.schemas.schemas import (
    MetricCreate,
    MetricResponse,
    KPISummaryResponse,
    ChannelAttributionResponse,
    AIDoctorResponse
)
from app.services.ai.ai_doctor import AIDoctorEngine

router = APIRouter(prefix="", tags=["Chỉ số Hiệu quả & KPI Dashboard"])

def check_campaign_access_for_metrics(campaign_id: int, user: User, db: Session) -> Campaign:
    """Xác thực phân quyền mức bản ghi và cách ly đa người thuê (Tenant Isolation):
    - User ADMIN có toàn quyền.
    - Kiểm tra Tenant Isolation đối với các workspace cụ thể (> 1):
      bắt buộc user phải là owner hoặc member của workspace đó.
    - User MANAGER / AGENCY_MANAGER:
      cho phép truy cập toàn bộ campaign trong workspace của mình.
    - User MARKETER hoặc role khác:
      chỉ được truy cập chiến dịch mình sở hữu (owner_id / created_by) hoặc là thành viên (CampaignMember).
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

@router.get("/campaigns/{campaign_id}/metrics", response_model=List[MetricResponse])
@router.get("/metrics/campaign/{campaign_id}", response_model=List[MetricResponse])
def get_campaign_metrics(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    campaign = check_campaign_access_for_metrics(campaign_id, current_user, db)

    metrics = db.query(CampaignMetric).filter(CampaignMetric.campaign_id == campaign_id).order_by(CampaignMetric.metric_date.desc()).all()
    return [MetricResponse.model_validate(m) for m in metrics]

@router.post("/campaigns/{campaign_id}/metrics", response_model=MetricResponse, status_code=status.HTTP_201_CREATED)
@router.post("/metrics/campaign/{campaign_id}", response_model=MetricResponse, status_code=status.HTTP_201_CREATED)
def record_campaign_metric(
    campaign_id: int,
    req: MetricCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    campaign = check_campaign_access_for_metrics(campaign_id, current_user, db)

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
@router.get("/metrics/campaign/{campaign_id}/kpi", response_model=KPISummaryResponse)
def get_campaign_kpi(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    campaign = check_campaign_access_for_metrics(campaign_id, current_user, db)

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
    roas = (total_revenue / total_cost) if total_cost > 0 else 0.0

    # Lấy phân rã kênh an toàn
    channel_metrics = AIDoctorEngine.compute_channel_attribution(campaign_id, db)

    return KPISummaryResponse(
        total_views=total_views,
        total_clicks=total_clicks,
        total_conversions=total_conversions,
        total_cost=round(total_cost, 2),
        total_revenue=round(total_revenue, 2),
        ctr_percent=round(ctr, 2),
        cpc_avg=round(cpc, 2),
        cvr_percent=round(cvr, 2),
        roi_percent=round(roi, 2),
        roas=round(roas, 2),
        channel_metrics=channel_metrics
    )

@router.get("/campaigns/{campaign_id}/attribution", response_model=List[ChannelAttributionResponse])
@router.get("/metrics/campaign/{campaign_id}/attribution", response_model=List[ChannelAttributionResponse])
def get_campaign_attribution(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lấy danh sách phân bổ hiệu quả chi tiết theo từng kênh tiếp thị."""
    campaign = check_campaign_access_for_metrics(campaign_id, current_user, db)
    return AIDoctorEngine.compute_channel_attribution(campaign_id, db)

@router.post("/campaigns/{campaign_id}/ai-doctor", response_model=AIDoctorResponse)
@router.get("/campaigns/{campaign_id}/ai-doctor", response_model=AIDoctorResponse)
@router.post("/metrics/campaign/{campaign_id}/ai-doctor", response_model=AIDoctorResponse)
@router.post("/ai/ai-doctor/{campaign_id}", response_model=AIDoctorResponse)
def diagnose_campaign_doctor(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Bác sĩ Chiến dịch AI (AI Doctor): Chẩn đoán điểm nghẽn và đưa ra khuyến nghị hành động tối ưu."""
    campaign = check_campaign_access_for_metrics(campaign_id, current_user, db)
    return AIDoctorEngine.diagnose_campaign(campaign_id, db, current_user)

@router.get("/analytics/dashboard")
@router.get("/metrics/dashboard")
def get_global_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role not in ("ADMIN", "MANAGER"):
        # Lọc theo phạm vi sở hữu của user nếu là Marketer
        allowed_campaign_ids = db.query(Campaign.id).filter(
            (Campaign.owner_id == current_user.id) |
            (Campaign.id.in_(db.query(CampaignMember.campaign_id).filter(CampaignMember.user_id == current_user.id)))
        ).all()
        allowed_ids = [c[0] for c in allowed_campaign_ids]
        metrics = db.query(CampaignMetric).filter(CampaignMetric.campaign_id.in_(allowed_ids)).all() if allowed_ids else []
        campaigns_count = len(allowed_ids)
        active_campaigns = db.query(Campaign).filter(
            Campaign.id.in_(allowed_ids),
            Campaign.status == "ACTIVE"
        ).count() if allowed_ids else 0
    else:
        metrics = db.query(CampaignMetric).all()
        campaigns_count = db.query(Campaign).count()
        active_campaigns = db.query(Campaign).filter(Campaign.status == "ACTIVE").count()

    total_views = sum(m.views for m in metrics)
    total_clicks = sum(m.clicks for m in metrics)
    total_conversions = sum(m.conversions for m in metrics)
    total_cost = sum(float(m.cost) for m in metrics)
    total_revenue = sum(float(m.revenue) for m in metrics)

    ctr = (total_clicks / total_views * 100.0) if total_views > 0 else 0.0
    cpc = (total_cost / total_clicks) if total_clicks > 0 else 0.0
    cvr = (total_conversions / total_clicks * 100.0) if total_clicks > 0 else 0.0
    roi = ((total_revenue - total_cost) / total_cost * 100.0) if total_cost > 0 else 0.0
    roas = (total_revenue / total_cost) if total_cost > 0 else 0.0

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
            "roas": round(roas, 2),
        },
        "campaigns_summary": {
            "total": campaigns_count,
            "active": active_campaigns
        }
    }
