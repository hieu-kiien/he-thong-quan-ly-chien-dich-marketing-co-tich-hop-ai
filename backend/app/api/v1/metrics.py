from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date, timezone
import csv
import io
import logging
import re
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, or_, and_
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.entities import (
    CampaignMetric, Campaign, MarketingChannel, User, CampaignMember,
    Workspace, WorkspaceMember, Task, MarketingContent, Product
)

logger = logging.getLogger(__name__)
from app.schemas.schemas import (
    MetricCreate,
    MetricResponse,
    KPISummaryResponse,
    ChannelAttributionResponse,
    AIDoctorResponse,
    CommandCenterResponse,
    CommandCenterAttentionItem,
    CommandCenterMyWorkItem,
    CommandCenterCampaignHealth,
    SmartCSVAnalyzeRequest,
    SmartCSVAnalyzeResponse,
    SmartCSVCommitRow,
    SmartCSVCommitRequest,
    SmartCSVCommitResponse,
)
from app.services.ai.ai_doctor import AIDoctorEngine
from app.api.v1.campaigns import _accessible_workspace_ids


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

    # Fail-closed: campaign không workspace thì không có ranh giới tenant để
    # tin cậy — mọi role (kể cả MANAGER) phải là owner hoặc CampaignMember.
    # Trước đây MANAGER toàn cục bypass nhánh này → đọc chéo tenant metrics.
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
        content_id=getattr(req, "content_id", None),
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
    cpa = (total_cost / total_conversions) if total_conversions > 0 else 0.0
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
        cpa_avg=round(cpa, 2),
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
@router.get("/metrics/overview")
def get_global_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Bảng điều khiển tổng hợp theo đúng phạm vi tenant của người gọi.

    Trước đây nhánh quản lý (`ADMIN`/`MANAGER`) gọi `db.query(...).all()` không lọc
    workspace, nên một MANAGER thấy doanh thu/chi phí gộp từ chiến dịch của cả
    agency khác. Toàn bộ endpoint list khác đều dùng `_apply_tenant_scope`; riêng
    aggregate này bị bỏ sót. Ngoài ra `AGENCY_MANAGER` thiếu trong nhánh quản lý
    nên bị hạ xuống tầm marketer ở riêng endpoint này.
    """
    if current_user.role == "ADMIN":
        base_query = db.query(Campaign)
    else:
        ws_ids = _accessible_workspace_ids(current_user, db)
        base_query = db.query(Campaign)
        if ws_ids:
            base_query = base_query.filter(
                or_(
                    Campaign.workspace_id.in_(ws_ids),
                    and_(Campaign.workspace_id.is_(None), Campaign.owner_id == current_user.id),
                )
            )
        else:
            base_query = base_query.filter(
                and_(Campaign.workspace_id.is_(None), Campaign.owner_id == current_user.id)
            )

        if current_user.role not in ("MANAGER", "AGENCY_MANAGER"):
            # Marketer: chỉ chiến dịch mình sở hữu hoặc được thêm vào.
            owned_or_member = or_(
                Campaign.owner_id == current_user.id,
                Campaign.id.in_(
                    db.query(CampaignMember.campaign_id).filter(CampaignMember.user_id == current_user.id)
                ),
            )
            base_query = base_query.filter(owned_or_member)

    allowed_ids = [row[0] for row in base_query.with_entities(Campaign.id).all()]

    if allowed_ids:
        metrics = db.query(CampaignMetric).filter(CampaignMetric.campaign_id.in_(allowed_ids)).all()
        campaigns_count = len(allowed_ids)
        active_campaigns = db.query(Campaign).filter(
            Campaign.id.in_(allowed_ids),
            Campaign.status == "ACTIVE"
        ).count()
        active_budget = float(db.query(func.coalesce(func.sum(Campaign.budget), 0)).filter(
            Campaign.id.in_(allowed_ids),
            Campaign.status == "ACTIVE",
        ).scalar() or 0)
    else:
        metrics = []
        campaigns_count = 0
        active_campaigns = 0
        active_budget = 0.0

    campaign_spend: Dict[str, float] = {}
    for m in metrics:
        key = str(m.campaign_id)
        campaign_spend[key] = round(campaign_spend.get(key, 0.0) + float(m.cost), 2)

    total_views = sum(m.views for m in metrics)
    total_clicks = sum(m.clicks for m in metrics)
    total_conversions = sum(m.conversions for m in metrics)
    total_cost = sum(float(m.cost) for m in metrics)
    total_revenue = sum(float(m.revenue) for m in metrics)

    ctr = (total_clicks / total_views * 100.0) if total_views > 0 else 0.0
    cpc = (total_cost / total_clicks) if total_clicks > 0 else 0.0
    cvr = (total_conversions / total_clicks * 100.0) if total_clicks > 0 else 0.0
    cpa = (total_cost / total_conversions) if total_conversions > 0 else 0.0
    roi = ((total_revenue - total_cost) / total_cost * 100.0) if total_cost > 0 else 0.0
    roas = (total_revenue / total_cost) if total_cost > 0 else 0.0

    seed_rows = 0
    unverified_rows = 0
    try:
        seed_rows = sum(1 for m in metrics if getattr(m, "source", None) == "seed")
        unverified_rows = sum(1 for m in metrics if getattr(m, "source", None) is None)
    except Exception:
        seed_rows = 0
        unverified_rows = 0
        logger.warning(
            "campaign_metrics.source khong doc duoc — bo qua canh bao du lieu mau. "
            "Kiem tra migration ALTER TABLE campaign_metrics ADD COLUMN source.",
            exc_info=True,
        )

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
            "cpa_avg": round(cpa, 2),
            "roi_percent": round(roi, 2),
            "roas": round(roas, 2),
            "channel_metrics": _aggregate_channel_metrics(db, allowed_ids),
        },
        "campaigns_summary": {
            "total": campaigns_count,
            "active": active_campaigns,
            "active_budget": round(active_budget, 2),
        },
        "campaign_spend": campaign_spend,
        "channel_attributions": _aggregate_channel_attribution(db, allowed_ids),
        "data_provenance": {
            "has_demo_data": seed_rows > 0,
            "has_unverified_data": unverified_rows > 0,
            "seed_rows": seed_rows,
            "unverified_rows": unverified_rows,
            "real_rows": len(metrics) - seed_rows - unverified_rows,
            "total_rows": len(metrics),
        },
    }


def _aggregate_channel_metrics(db: Session, campaign_ids: List[int]) -> List[Dict[str, Any]]:
    """Tổng hợp CampaignMetric theo kênh cho tập chiến dịch đã lọc."""
    if not campaign_ids:
        return []

    rows = (
        db.query(
            MarketingChannel.id.label("channel_id"),
            MarketingChannel.code.label("channel_code"),
            MarketingChannel.name.label("channel_name"),
            func.sum(CampaignMetric.views).label("views"),
            func.sum(CampaignMetric.clicks).label("clicks"),
            func.sum(CampaignMetric.conversions).label("conversions"),
            func.sum(CampaignMetric.cost).label("cost"),
            func.sum(CampaignMetric.revenue).label("revenue"),
        )
        .join(MarketingChannel, MarketingChannel.id == CampaignMetric.channel_id)
        .filter(CampaignMetric.campaign_id.in_(campaign_ids))
        .group_by(MarketingChannel.id, MarketingChannel.code, MarketingChannel.name)
        .all()
    )

    result: List[Dict[str, Any]] = []
    for r in rows:
        views = int(r.views or 0)
        clicks = int(r.clicks or 0)
        conversions = int(r.conversions or 0)
        cost = float(r.cost or 0)
        revenue = float(r.revenue or 0)
        result.append({
            "channel_id": r.channel_id,
            "channel_code": r.channel_code,
            "channel_name": r.channel_name,
            "views": views,
            "clicks": clicks,
            "conversions": conversions,
            "cost": round(cost, 2),
            "revenue": round(revenue, 2),
            "ctr_percent": round(clicks / views * 100.0, 2) if views > 0 else 0.0,
            "cpc_avg": round(cost / clicks, 2) if clicks > 0 else 0.0,
            "cvr_percent": round(conversions / clicks * 100.0, 2) if clicks > 0 else 0.0,
            "cpa_avg": round(cost / conversions, 2) if conversions > 0 else 0.0,
            "roi_percent": round((revenue - cost) / cost * 100.0, 2) if cost > 0 else 0.0,
            "roas": round(revenue / cost, 2) if cost > 0 else 0.0,
        })
    return result


def _aggregate_channel_attribution(db: Session, campaign_ids: List[int]) -> List[Dict[str, Any]]:
    return _aggregate_channel_metrics(db, campaign_ids)


get_metrics_overview = get_global_dashboard


# --- COMMAND CENTER ENDPOINTS ---

@router.get("/analytics/command-center", response_model=CommandCenterResponse)
@router.get("/metrics/command-center", response_model=CommandCenterResponse)
def get_command_center(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Command Center điều phối vận hành chiến dịch Marketing theo thời gian thực."""
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if current_user.role == "ADMIN":
        accessible_campaigns = db.query(Campaign).all()
    elif current_user.role in ("MANAGER", "AGENCY_MANAGER"):
        ws_ids = _accessible_workspace_ids(current_user, db)
        query = db.query(Campaign)
        if ws_ids:
            query = query.filter(
                (Campaign.workspace_id.in_(ws_ids)) |
                (Campaign.owner_id == current_user.id)
            )
        else:
            query = query.filter(Campaign.owner_id == current_user.id)
        accessible_campaigns = query.all()
    else:
        member_campaign_ids = [
            row[0] for row in db.query(CampaignMember.campaign_id)
            .filter(CampaignMember.user_id == current_user.id).all()
        ]
        accessible_campaigns = db.query(Campaign).filter(
            (Campaign.owner_id == current_user.id) |
            (Campaign.id.in_(member_campaign_ids))
        ).all()

    camp_map = {c.id: c for c in accessible_campaigns}
    camp_ids = list(camp_map.keys())

    attention_items: List[CommandCenterAttentionItem] = []
    my_work_today: List[CommandCenterMyWorkItem] = []
    campaigns_health: List[CommandCenterCampaignHealth] = []

    if not camp_ids:
        return CommandCenterResponse(
            attention_items=[],
            my_work_today=[],
            campaigns_health=[],
            summary_counts={
                "total_active_campaigns": 0,
                "total_my_tasks": 0,
                "total_overdue_tasks": 0,
                "total_pending_approvals": 0,
                "critical_issues": 0
            }
        )

    overdue_tasks = db.query(Task).filter(
        Task.campaign_id.in_(camp_ids),
        Task.due_date < today_str,
        Task.status.notin_(["DONE", "COMPLETED"])
    ).order_by(Task.due_date.asc()).all()

    for t in overdue_tasks:
        c_name = camp_map.get(t.campaign_id).name if t.campaign_id in camp_map else "Chiến dịch"
        severity = "CRITICAL" if t.priority == "URGENT" else "HIGH"
        attention_items.append(CommandCenterAttentionItem(
            id=f"overdue-task-{t.id}",
            type="OVERDUE_TASK",
            severity=severity,
            title=f"Quá hạn: {t.title}",
            message=f"Tác vụ '{t.title}' trong chiến dịch '{c_name}' đã quá hạn vào {t.due_date}.",
            campaign_id=t.campaign_id,
            campaign_name=c_name,
            link=f"/campaigns/{t.campaign_id}",
            due_date=t.due_date
        ))

    pending_filter = (
        MarketingContent.campaign_id.in_(camp_ids),
        MarketingContent.status.in_(["IN_REVIEW", "AI_DRAFT"]),
    )
    total_pending_approvals = db.query(func.count(MarketingContent.id)).filter(*pending_filter).scalar() or 0
    pending_contents = (
        db.query(MarketingContent)
        .filter(*pending_filter)
        .order_by(MarketingContent.id.desc())
        .limit(15)
        .all()
    )

    for cnt in pending_contents:
        c_name = camp_map.get(cnt.campaign_id).name if cnt.campaign_id in camp_map else "Chiến dịch"
        attention_items.append(CommandCenterAttentionItem(
            id=f"pending-content-{cnt.id}",
            type="PENDING_APPROVAL",
            severity="MEDIUM" if cnt.status == "AI_DRAFT" else "HIGH",
            title=f"Chờ duyệt: {cnt.title}",
            message=f"Nội dung '{cnt.title}' thuộc '{c_name}' đang ở trạng thái {cnt.status}.",
            campaign_id=cnt.campaign_id,
            campaign_name=c_name,
            link=f"/campaigns/{cnt.campaign_id}",
            due_date=None
        ))

    spent_by_campaign = {}
    actual_metrics_by_campaign = {}
    metrics_sums = db.query(
        CampaignMetric.campaign_id,
        func.sum(CampaignMetric.cost).label("total_cost"),
        func.sum(CampaignMetric.conversions).label("total_conversions"),
        func.sum(CampaignMetric.clicks).label("total_clicks"),
        func.sum(CampaignMetric.revenue).label("total_revenue"),
        func.sum(CampaignMetric.views).label("total_views")
    ).filter(CampaignMetric.campaign_id.in_(camp_ids)).group_by(CampaignMetric.campaign_id).all()

    for cid, total_cost, total_conv, total_clicks, total_rev, total_views in metrics_sums:
        spent_by_campaign[cid] = float(total_cost or 0.0)
        actual_metrics_by_campaign[cid] = {
            "conversions": float(total_conv or 0.0),
            "clicks": float(total_clicks or 0.0),
            "revenue": float(total_rev or 0.0),
            "views": float(total_views or 0.0),
        }

    all_campaign_tasks = db.query(Task).filter(Task.campaign_id.in_(camp_ids)).all()
    tasks_by_campaign: Dict[int, List[Task]] = {}
    for t in all_campaign_tasks:
        tasks_by_campaign.setdefault(t.campaign_id, []).append(t)

    for c in accessible_campaigns:
        c_budget = float(c.budget or 0.0)
        c_spent = spent_by_campaign.get(c.id, 0.0)
        c_tasks = tasks_by_campaign.get(c.id, [])
        c_overdue = sum(1 for t in c_tasks if t.due_date and t.due_date < today_str and t.status not in ("DONE", "COMPLETED"))
        c_completed = sum(1 for t in c_tasks if t.status in ("DONE", "COMPLETED"))
        c_total_tasks = len(c_tasks)

        budget_pct = (c_spent / c_budget * 100.0) if c_budget > 0 else 0.0

        c_kpi_target = float(c.target_kpi_value or 0.0)
        kpi_name_lower = (c.target_kpi_name or "conversions").lower()
        camp_metrics = actual_metrics_by_campaign.get(c.id, {})
        if "click" in kpi_name_lower:
            c_kpi_actual = camp_metrics.get("clicks", 0.0)
        elif "rev" in kpi_name_lower or "doanh thu" in kpi_name_lower:
            c_kpi_actual = camp_metrics.get("revenue", 0.0)
        elif "view" in kpi_name_lower or "xem" in kpi_name_lower:
            c_kpi_actual = camp_metrics.get("views", 0.0)
        else:
            c_kpi_actual = camp_metrics.get("conversions", 0.0)

        if c_kpi_target > 0:
            c_kpi_achievement_pct = round((c_kpi_actual / c_kpi_target) * 100.0, 1)
        else:
            c_kpi_achievement_pct = 100.0 if c_kpi_actual > 0 else 0.0

        is_budget_risk = (budget_pct > 80.0 and c_kpi_achievement_pct < 60.0)

        if c_budget > 0 and c_spent > c_budget:
            attention_items.append(CommandCenterAttentionItem(
                id=f"budget-overrun-{c.id}",
                type="BUDGET_OVERRUN",
                severity="CRITICAL",
                title=f"Vượt ngân sách: {c.name}",
                message=f"Đã chi ${c_spent:,.2f} trên tổng ngân sách ${c_budget:,.2f} ({budget_pct:.1f}%).",
                campaign_id=c.id,
                campaign_name=c.name,
                link=f"/campaigns/{c.id}",
                due_date=c.end_date
            ))
        elif is_budget_risk:
            attention_items.append(CommandCenterAttentionItem(
                id=f"budget-risk-{c.id}",
                type="BUDGET_RISK",
                severity="HIGH",
                title=f"Rủi ro ngân sách: {c.name}",
                message=f"Đã tiêu thụ {budget_pct:.1f}% ngân sách nhưng tiến độ KPI mới đạt {c_kpi_achievement_pct:.1f}%.",
                campaign_id=c.id,
                campaign_name=c.name,
                link=f"/campaigns/{c.id}",
                due_date=c.end_date
            ))
        elif c_budget > 0 and budget_pct >= 90.0:
            attention_items.append(CommandCenterAttentionItem(
                id=f"budget-warning-{c.id}",
                type="BUDGET_OVERRUN",
                severity="HIGH",
                title=f"Sắp chạm trần ngân sách: {c.name}",
                message=f"Đã tiêu thụ {budget_pct:.1f}% ngân sách (${c_spent:,.2f}/${c_budget:,.2f}).",
                campaign_id=c.id,
                campaign_name=c.name,
                link=f"/campaigns/{c.id}",
                due_date=c.end_date
            ))

        health_score = 100
        if c_overdue > 0:
            health_score -= min(45, c_overdue * 15)
        if c_budget > 0:
            if budget_pct > 100:
                health_score -= 30
            elif budget_pct > 90:
                health_score -= 15

        if is_budget_risk:
            health_score -= 20

        if c_total_tasks > 0 and (c_completed / c_total_tasks) < 0.2 and c.status == "ACTIVE":
            health_score -= 10

        health_score = max(0, min(100, health_score))
        if health_score >= 75:
            health_status = "ON_TRACK"
        elif health_score >= 50:
            health_status = "AT_RISK"
        else:
            health_status = "CRITICAL"

        if c.status in ("ACTIVE", "PLANNED"):
            campaigns_health.append(CommandCenterCampaignHealth(
                campaign_id=c.id,
                campaign_name=c.name,
                status=c.status,
                budget=c_budget,
                spent=c_spent,
                budget_utilization_pct=round(budget_pct, 1),
                total_tasks=c_total_tasks,
                completed_tasks=c_completed,
                overdue_tasks=c_overdue,
                health_status=health_status,
                health_score=health_score,
                start_date=c.start_date,
                end_date=c.end_date,
                kpi_target=c_kpi_target if c_kpi_target > 0 else None,
                kpi_actual=c_kpi_actual,
                kpi_achievement_pct=c_kpi_achievement_pct,
                budget_risk=is_budget_risk
            ))

    user_tasks_query = db.query(Task).filter(
        Task.assignee_id == current_user.id,
        Task.status.notin_(["DONE", "COMPLETED"])
    )
    if current_user.role != "ADMIN":
        user_tasks_query = user_tasks_query.filter(Task.campaign_id.in_(camp_ids))
    user_tasks = user_tasks_query.all()

    for ut in user_tasks:
        c_name = camp_map.get(ut.campaign_id).name if ut.campaign_id in camp_map else "Chiến dịch"
        is_ovd = bool(ut.due_date and ut.due_date < today_str)
        my_work_today.append(CommandCenterMyWorkItem(
            id=ut.id,
            task_type=ut.task_type,
            title=ut.title,
            status=ut.status,
            priority=ut.priority,
            due_date=ut.due_date,
            campaign_id=ut.campaign_id,
            campaign_name=c_name,
            is_overdue=is_ovd
        ))

    priority_order = {"URGENT": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    my_work_today.sort(key=lambda item: (
        0 if item.is_overdue else (1 if item.due_date == today_str else 2),
        priority_order.get(item.priority, 2),
        item.due_date or "9999-99-99"
    ))

    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2}
    attention_items.sort(key=lambda a: severity_order.get(a.severity, 2))

    summary_counts = {
        "total_active_campaigns": len(campaigns_health),
        "total_my_tasks": len(my_work_today),
        "total_overdue_tasks": len(overdue_tasks),
        "total_pending_approvals": int(total_pending_approvals),
        "critical_issues": sum(1 for a in attention_items if a.severity == "CRITICAL")
    }

    return CommandCenterResponse(
        attention_items=attention_items,
        my_work_today=my_work_today,
        campaigns_health=campaigns_health,
        summary_counts=summary_counts
    )


# ==============================================================================
# REAL ADS CSV IMPORTER, SMART CSV WIZARD, DATA VERIFICATION & AI MORNING BRIEFING
# ==============================================================================

class CSVMetricsImportRequest(BaseModel):
    csv_content: str = Field(..., min_length=5, description="Nội dung file CSV/TSV xuất từ Facebook Ads, TikTok Ads, Google Ads hoặc mẫu chuẩn")
    replace_seed_data: bool = Field(
        default=True,
        description="Nếu true, xóa các bản ghi dữ liệu mẫu (seed) của chiến dịch trước khi nạp dữ liệu thật"
    )


class VerifyRealDataRequest(BaseModel):
    mode: str = Field(
        default="mark_verified",
        description="'mark_verified' để xác nhận toàn bộ dữ liệu hiện tại là dữ liệu thật, hoặc 'purge_seed' để xóa sạch dòng dữ liệu mẫu"
    )
    campaign_id: Optional[int] = Field(default=None, description="ID chiến dịch cụ thể (tùy chọn)")


def _resolve_channel_from_label(db: Session, raw_label: str) -> MarketingChannel:
    """Ánh xạ linh hoạt tên kênh từ file báo cáo Facebook/TikTok/Google Ads sang MarketingChannel."""
    clean = (raw_label or "").strip().lower()
    all_channels = db.query(MarketingChannel).all()
    if not all_channels:
        ch = MarketingChannel(code="facebook", name="Facebook Ads", status="ACTIVE")
        db.add(ch)
        db.flush()
        return ch

    for ch in all_channels:
        if clean == (ch.code or "").lower() or clean == (ch.name or "").lower():
            return ch

    alias_map = {
        "facebook": ["fb", "meta", "facebook", "instagram", "ig", "fanpage"],
        "tiktok": ["tiktok", "tt", "douyin", "reels", "short"],
        "google": ["google", "sem", "adwords", "search", "gdn", "youtube"],
        "email": ["email", "mail", "edm", "newsletter", "crm"],
        "linkedin": ["linkedin", "b2b"],
        "zalo": ["zalo", "oa"],
        "blog": ["blog", "seo", "website", "web"],
    }
    for code_key, keywords in alias_map.items():
        if any(k in clean for k in keywords):
            for ch in all_channels:
                if code_key in (ch.code or "").lower() or code_key in (ch.name or "").lower():
                    return ch

    return all_channels[0]


def _parse_number(val: Any, is_float: bool = False) -> float:
    if val is None:
        return 0.0
    s = str(val).strip()
    s = re.sub(r"[₫đ$€£%\s]|vnd|usd", "", s, flags=re.IGNORECASE)
    if not s or s == "-":
        return 0.0
    # Xử lý định dạng tiền tệ Việt Nam "1.850.000" (nhiều dấu chấm hoặc chấm ngăn cách hàng nghìn)
    if s.count(".") > 1 and "," not in s:
        s = s.replace(".", "")
    elif "." in s and "," not in s:
        parts = s.split(".")
        if len(parts) == 2 and len(parts[1]) == 3 and len(parts[0]) >= 1:
            # Ví dụ "500.000" hoặc "12.500" trong báo cáo VND
            try:
                if int(parts[0]) >= 10:
                    s = s.replace(".", "")
            except ValueError:
                pass
    elif "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            # Định dạng 1.850.000,50
            s = s.replace(".", "").replace(",", ".")
        else:
            # Định dạng 1,850,000.50
            s = s.replace(",", "")
    else:
        s = s.replace(",", "")
    try:
        num = float(s)
        return num if is_float else float(int(round(num)))
    except ValueError:
        return 0.0


def _normalize_date_str(raw_val: Any, fallback_date: str) -> str:
    if not raw_val:
        return fallback_date
    s = str(raw_val).strip()[:10]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return fallback_date


def _detect_ads_platform_and_mapping(fieldnames: List[str]) -> Tuple[str, Dict[str, str]]:
    """Tự động nhận diện nền tảng quảng cáo và ánh xạ cột sang chuẩn hệ thống."""
    lower_map = {f.strip().lower(): f for f in fieldnames if f}
    lower_keys = set(lower_map.keys())

    platform = "Generic CSV"
    if any(k in lower_keys for k in ("reporting starts", "amount spent (vnd)", "amount spent", "purchases conversion value", "link clicks")):
        platform = "Facebook Ads"
    elif any(k in lower_keys for k in ("by day", "total cost", "total complete payment", "video views")):
        platform = "TikTok Ads"
    elif any(k in lower_keys for k in ("impr.", "conv. value", "avg. cpc", "search impr. share")):
        platform = "Google Ads"

    candidates = {
        "metric_date": ["metric_date", "date", "ngày", "ngay", "reporting starts", "by day", "day"],
        "campaign_code": ["campaign_code", "mã chiến dịch", "ma chien dich", "campaign id"],
        "campaign_name": ["campaign_name", "campaign", "tên chiến dịch", "ten chien dich", "chiến dịch"],
        "channel": ["channel", "channel_code", "platform", "kênh", "kenh", "source", "placement"],
        "views": ["views", "impressions", "impr.", "lượt hiển thị", "luot hien thi", "lượt xem", "luot xem", "reach", "video views"],
        "clicks": ["clicks", "link clicks", "clicks (all)", "lượt nhấp (tất cả)", "lượt nhấp", "luot nhap"],
        "conversions": ["conversions", "results", "purchases", "leads", "kết quả", "ket qua", "chuyển đổi", "chuyen doi", "total complete payment", "conv."],
        "cost": ["cost", "spend", "amount spent (vnd)", "amount spent", "total cost", "chi phí", "chi phi", "ngân sách đã chi"],
        "revenue": ["revenue", "purchases conversion value", "purchase conversion value", "conversion value", "conv. value", "giá trị chuyển đổi", "gia tri chuyen doi", "doanh thu"],
    }

    column_mapping: Dict[str, str] = {}
    for canonical, aliases in candidates.items():
        for alias in aliases:
            if alias in lower_map:
                column_mapping[canonical] = lower_map[alias]
                break

    return platform, column_mapping


def _accessible_campaigns_for_user(db: Session, user: User) -> List[Campaign]:
    if user.role == "ADMIN":
        return db.query(Campaign).all()
    ws_ids = _accessible_workspace_ids(user, db)
    q = db.query(Campaign)
    if ws_ids:
        q = q.filter(or_(Campaign.workspace_id.in_(ws_ids), Campaign.owner_id == user.id))
    else:
        q = q.filter(Campaign.owner_id == user.id)
    if user.role not in ("MANAGER", "AGENCY_MANAGER"):
        member_ids = [r[0] for r in db.query(CampaignMember.campaign_id).filter(CampaignMember.user_id == user.id).all()]
        q = q.filter(or_(Campaign.owner_id == user.id, Campaign.id.in_(member_ids)))
    return q.all()


def _parse_smart_csv_rows(
    csv_text: str,
    default_campaign_id: Optional[int],
    default_channel_code: str,
    accessible_campaigns: List[Campaign],
) -> Tuple[str, Dict[str, str], List[Dict[str, Any]], List[Dict[str, Any]], set, List[str]]:
    raw_text = (csv_text or "").strip().lstrip("\ufeff")
    if not raw_text:
        raise HTTPException(status_code=400, detail="Nội dung CSV trống.")
    first_line = raw_text.splitlines()[0]
    delimiter = "\t" if ("\t" in first_line and "," not in first_line) else (";" if (";" in first_line and "," not in first_line) else ",")
    reader = csv.DictReader(io.StringIO(raw_text), delimiter=delimiter)
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="File CSV không có dòng tiêu đề cột hợp lệ.")

    platform, col_map = _detect_ads_platform_and_mapping(list(reader.fieldnames))
    default_platform_channel = (
        "facebook" if platform == "Facebook Ads"
        else ("tiktok" if platform == "TikTok Ads" else ("google_ads" if platform == "Google Ads" else default_channel_code))
    )

    by_id = {c.id: c for c in accessible_campaigns}
    by_code = {(c.campaign_code or "").strip().lower(): c for c in accessible_campaigns if c.campaign_code}
    by_name = {(c.name or "").strip().lower(): c for c in accessible_campaigns if c.name}

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    parsed_rows: List[Dict[str, Any]] = []
    anomalies: List[Dict[str, Any]] = []
    matched_camp_ids = set()
    unmatched_names: List[str] = []

    for idx, row in enumerate(reader, start=1):
        norm = {str(k or "").strip().lower(): v for k, v in row.items() if k is not None}
        if not any(str(v or "").strip() for v in norm.values()):
            continue

        raw_date = row.get(col_map.get("metric_date", "")) if "metric_date" in col_map else (
            norm.get("metric_date") or norm.get("date") or norm.get("ngày") or norm.get("reporting starts")
        )
        m_date = _normalize_date_str(raw_date, today_str)

        raw_code = (row.get(col_map.get("campaign_code", "")) if "campaign_code" in col_map else norm.get("campaign_code")) or ""
        raw_name = (row.get(col_map.get("campaign_name", "")) if "campaign_name" in col_map else norm.get("campaign_name")) or ""
        raw_code_clean = str(raw_code).strip()
        raw_name_clean = str(raw_name).strip()

        matched_camp: Optional[Campaign] = None
        if raw_code_clean and raw_code_clean.lower() in by_code:
            matched_camp = by_code[raw_code_clean.lower()]
        elif raw_name_clean and raw_name_clean.lower() in by_name:
            matched_camp = by_name[raw_name_clean.lower()]
        elif raw_name_clean:
            # Tìm kiếm gần đúng theo substring
            for cname_lower, c_obj in by_name.items():
                if raw_name_clean.lower() in cname_lower or cname_lower in raw_name_clean.lower():
                    matched_camp = c_obj
                    break
        if matched_camp is None and default_campaign_id and default_campaign_id in by_id:
            matched_camp = by_id[default_campaign_id]

        raw_ch = (row.get(col_map.get("channel", "")) if "channel" in col_map else norm.get("channel")) or default_platform_channel

        raw_views = row.get(col_map.get("views", "")) if "views" in col_map else norm.get("views", 0)
        raw_clicks = row.get(col_map.get("clicks", "")) if "clicks" in col_map else norm.get("clicks", 0)
        raw_conv = row.get(col_map.get("conversions", "")) if "conversions" in col_map else norm.get("conversions", 0)
        raw_cost = row.get(col_map.get("cost", "")) if "cost" in col_map else norm.get("cost", 0)
        raw_rev = row.get(col_map.get("revenue", "")) if "revenue" in col_map else norm.get("revenue", 0)

        views = int(_parse_number(raw_views, is_float=False))
        clicks = int(_parse_number(raw_clicks, is_float=False))
        conversions = int(_parse_number(raw_conv, is_float=False))
        cost = _parse_number(raw_cost, is_float=True)
        revenue = _parse_number(raw_rev, is_float=True)

        row_anomalies: List[str] = []
        if matched_camp is None:
            label = raw_code_clean or raw_name_clean or f"Dòng #{idx}"
            row_anomalies.append(f"Không khớp được chiến dịch '{label}'")
            if label not in unmatched_names:
                unmatched_names.append(label)
        else:
            matched_camp_ids.add(matched_camp.id)

        if clicks > views and views > 0:
            row_anomalies.append(f"Lượt nhấp ({clicks}) lớn hơn lượt hiển thị ({views}) — sẽ tự động chuẩn hóa views = clicks.")
        if cost < 0:
            row_anomalies.append(f"Chi phí âm ({cost}) không hợp lệ.")
        if conversions > clicks and clicks > 0:
            row_anomalies.append(f"Lượt chuyển đổi ({conversions}) vượt số lượt nhấp ({clicks}).")

        if row_anomalies:
            anomalies.append({
                "row_index": idx,
                "issues": row_anomalies,
                "campaign_name": raw_name_clean or (matched_camp.name if matched_camp else None),
            })

        parsed_rows.append({
            "row_index": idx,
            "campaign_id": matched_camp.id if matched_camp else None,
            "campaign_code": matched_camp.campaign_code if matched_camp else (raw_code_clean or None),
            "campaign_name": matched_camp.name if matched_camp else (raw_name_clean or None),
            "channel_code": str(raw_ch).strip().lower() or default_platform_channel,
            "metric_date": m_date,
            "views": max(0, views),
            "clicks": max(0, clicks),
            "conversions": max(0, conversions),
            "cost": round(max(0.0, cost), 2),
            "revenue": round(max(0.0, revenue), 2),
            "has_anomaly": len(row_anomalies) > 0,
            "anomaly_notes": row_anomalies,
        })

    return platform, col_map, parsed_rows, anomalies, matched_camp_ids, unmatched_names


@router.post("/metrics/smart-import/analyze", response_model=SmartCSVAnalyzeResponse)
@router.post("/analytics/smart-import/analyze", response_model=SmartCSVAnalyzeResponse)
def analyze_smart_csv_import(
    req: SmartCSVAnalyzeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Smart CSV Importer — Bước 1 (Analyze & Column Mapping Preview):
    Tự động nhận diện định dạng báo cáo (Facebook Ads / TikTok Ads / Google Ads / Generic),
    chuẩn hóa tiền tệ & ngày tháng, đối sánh chiến dịch theo `campaign_code` hoặc `campaign_name`,
    và phát hiện dòng bất thường trước khi commit.
    """
    raw_csv = (req.csv_text or req.csv_content or "").strip()
    if len(raw_csv) < 5:
        raise HTTPException(status_code=400, detail="Nội dung CSV quá ngắn hoặc trống.")

    if req.default_campaign_id is not None:
        check_campaign_access_for_metrics(req.default_campaign_id, current_user, db)

    accessible_campaigns = _accessible_campaigns_for_user(db, current_user)
    platform, col_map, parsed_rows, anomalies, matched_ids, unmatched_names = _parse_smart_csv_rows(
        csv_text=raw_csv,
        default_campaign_id=req.default_campaign_id,
        default_channel_code=req.default_channel_code or "facebook",
        accessible_campaigns=accessible_campaigns,
    )

    by_id = {c.id: c for c in accessible_campaigns}
    grouped: Dict[str, Dict[str, Any]] = {}
    t_views = 0
    t_clicks = 0
    t_conv = 0
    t_cost = 0.0
    t_rev = 0.0

    for r in parsed_rows:
        t_views += int(r.get("views") or 0)
        t_clicks += int(r.get("clicks") or 0)
        t_conv += int(r.get("conversions") or 0)
        t_cost += float(r.get("cost") or 0.0)
        t_rev += float(r.get("revenue") or 0.0)

        key_name = str(r.get("campaign_name") or r.get("campaign_code") or f"Chiến dịch #{r.get('campaign_id') or 1}")
        if key_name not in grouped:
            cid = r.get("campaign_id")
            matched_obj = by_id.get(cid) if cid else None
            grouped[key_name] = {
                "csv_campaign_name": key_name,
                "matched_campaign_id": cid,
                "matched_campaign_name": matched_obj.name if matched_obj else None,
                "match_confidence": "EXACT" if cid else "NEW",
                "row_count": 0,
                "channels": [],
                "total_cost": 0.0,
                "total_revenue": 0.0,
                "total_conversions": 0,
                "total_clicks": 0,
                "total_views": 0,
            }
        g = grouped[key_name]
        g["row_count"] += 1
        ch_c = str(r.get("channel_code") or "facebook")
        if ch_c not in g["channels"]:
            g["channels"].append(ch_c)
        g["total_cost"] = round(g["total_cost"] + float(r.get("cost") or 0.0), 2)
        g["total_revenue"] = round(g["total_revenue"] + float(r.get("revenue") or 0.0), 2)
        g["total_conversions"] += int(r.get("conversions") or 0)
        g["total_clicks"] += int(r.get("clicks") or 0)
        g["total_views"] += int(r.get("views") or 0)

    campaign_matches = list(grouped.values())
    valid_rows = sum(1 for r in parsed_rows if r.get("campaign_id") is not None)
    ui_col_map = {
        **col_map,
        "report_date": col_map.get("metric_date") or "Date",
    }

    return SmartCSVAnalyzeResponse(
        status="ok",
        detected_platform=platform,
        total_rows=len(parsed_rows),
        valid_rows=valid_rows,
        valid_rows_count=valid_rows,
        anomaly_rows=len(anomalies),
        column_mapping=ui_col_map,
        detected_headers=[v for v in col_map.values() if v],
        preview_rows=parsed_rows[:100],
        sample_rows=parsed_rows[:20],
        anomalies=anomalies,
        matched_campaigns_count=len(matched_ids),
        matched_count=len(matched_ids),
        unmatched_count=len(unmatched_names),
        unmatched_campaigns=unmatched_names,
        campaign_matches=campaign_matches,
        summary={
            "total_views": t_views,
            "total_clicks": t_clicks,
            "total_conversions": t_conv,
            "total_cost": round(t_cost, 2),
            "total_revenue": round(t_rev, 2),
            "estimated_roas": round(t_rev / t_cost, 2) if t_cost > 0 else 0.0,
        },
    )


@router.post("/metrics/smart-import/commit", response_model=SmartCSVCommitResponse)
@router.post("/analytics/smart-import/commit", response_model=SmartCSVCommitResponse)
def commit_smart_csv_import(
    req: SmartCSVCommitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Smart CSV Importer — Bước 2 (Idempotent Bulk Upsert Commit):
    Lưu dữ liệu đã phân tích (hoặc parse trực tiếp từ `csv_text`/`csv_content`) vào bảng `campaign_metrics`.
    """
    if req.default_campaign_id is not None:
        check_campaign_access_for_metrics(req.default_campaign_id, current_user, db)

    accessible_campaigns = _accessible_campaigns_for_user(db, current_user)
    by_id = {c.id: c for c in accessible_campaigns}
    by_code = {(c.campaign_code or "").strip().lower(): c for c in accessible_campaigns if c.campaign_code}
    by_name = {(c.name or "").strip().lower(): c for c in accessible_campaigns if c.name}

    raw_csv = (req.csv_text or req.csv_content or "").strip()
    rows_to_commit: List[Dict[str, Any]] = []
    if req.rows:
        for r in req.rows:
            rows_to_commit.append(r.model_dump())
    elif raw_csv:
        _, _, parsed_rows, _, _, _ = _parse_smart_csv_rows(
            csv_text=raw_csv,
            default_campaign_id=req.default_campaign_id,
            default_channel_code=req.default_channel_code or "facebook",
            accessible_campaigns=accessible_campaigns,
        )
        rows_to_commit = parsed_rows
    else:
        raise HTTPException(status_code=400, detail="Cần truyền `rows` hoặc `csv_text`/`csv_content` để thực hiện import.")

    imported_count = 0
    updated_count = 0
    skipped_count = 0
    created_campaigns_count = 0
    replaced_seed_rows = 0
    affected_campaign_ids = set()
    errors: List[str] = []
    purged_campaigns = set()
    custom_map = req.campaign_mapping or {}

    default_ws_id = req.workspace_id
    if default_ws_id is None:
        ws_ids = _accessible_workspace_ids(current_user, db)
        default_ws_id = ws_ids[0] if ws_ids else (accessible_campaigns[0].workspace_id if accessible_campaigns else 1)
    first_prod = db.query(Product).first()
    default_prod_id = first_prod.id if first_prod else 1

    for idx, r in enumerate(rows_to_commit, start=1):
        camp: Optional[Campaign] = None
        cid = r.get("campaign_id")
        raw_cname = str(r.get("campaign_name") or "").strip()
        ccode = str(r.get("campaign_code") or "").strip().lower()
        cname = raw_cname.lower()

        if raw_cname and raw_cname in custom_map and custom_map[raw_cname] in by_id:
            camp = by_id[custom_map[raw_cname]]
        elif cid and cid in by_id:
            camp = by_id[cid]
        elif ccode and ccode in by_code:
            camp = by_code[ccode]
        elif cname and cname in by_name:
            camp = by_name[cname]
        elif req.default_campaign_id and req.default_campaign_id in by_id:
            camp = by_id[req.default_campaign_id]
        elif req.auto_create_campaigns and raw_cname:
            new_code = f"CMP-CSV-{len(by_id) + created_campaigns_count + 1:03d}"
            camp = Campaign(
                workspace_id=default_ws_id,
                product_id=default_prod_id,
                owner_id=current_user.id,
                name=raw_cname[:255],
                objective="Tối ưu chuyển đổi đa kênh (Imported from CSV)",
                funnel_stage="BoFU",
                campaign_code=new_code,
                budget=50000000.0,
                status="ACTIVE",
                tags_json='["csv-auto-created"]',
            )
            db.add(camp)
            db.flush()
            by_id[camp.id] = camp
            by_name[cname] = camp
            created_campaigns_count += 1

        if camp is None:
            skipped_count += 1
            errors.append(f"Dòng #{idx}: Không xác định được chiến dịch hợp lệ.")
            continue

        if req.replace_seed_data and camp.id not in purged_campaigns:
            deleted_n = db.query(CampaignMetric).filter(
                CampaignMetric.campaign_id == camp.id,
                or_(CampaignMetric.source == "seed", CampaignMetric.source.is_(None)),
            ).delete(synchronize_session=False)
            replaced_seed_rows += int(deleted_n or 0)
            purged_campaigns.add(camp.id)
            db.flush()

        channel_obj = _resolve_channel_from_label(db, str(r.get("channel_code") or r.get("channel_name") or "facebook"))
        m_date = _normalize_date_str(r.get("metric_date"), datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        views = max(0, int(r.get("views") or 0))
        clicks = max(0, int(r.get("clicks") or 0))
        conversions = max(0, int(r.get("conversions") or 0))
        cost = round(max(0.0, float(r.get("cost") or 0.0)), 2)
        revenue = round(max(0.0, float(r.get("revenue") or 0.0)), 2)

        if clicks > views:
            views = clicks

        existing = db.query(CampaignMetric).filter(
            CampaignMetric.campaign_id == camp.id,
            CampaignMetric.channel_id == channel_obj.id,
            CampaignMetric.metric_date == m_date,
        ).first()

        if existing:
            existing.views = views
            existing.clicks = clicks
            existing.conversions = conversions
            existing.cost = cost
            existing.revenue = revenue
            existing.source = "csv_import"
            if r.get("content_id"):
                existing.content_id = r.get("content_id")
            updated_count += 1
        else:
            db.add(
                CampaignMetric(
                    campaign_id=camp.id,
                    channel_id=channel_obj.id,
                    content_id=r.get("content_id"),
                    metric_date=m_date,
                    views=views,
                    clicks=clicks,
                    conversions=conversions,
                    cost=cost,
                    revenue=revenue,
                    source="csv_import",
                )
            )
            imported_count += 1

        affected_campaign_ids.add(camp.id)

    db.commit()
    sorted_affected = sorted(affected_campaign_ids)
    return SmartCSVCommitResponse(
        status="success",
        imported_rows=imported_count,
        updated_rows=updated_count,
        skipped_rows=skipped_count,
        inserted_or_updated=imported_count + updated_count,
        skipped_count=skipped_count,
        updated_campaigns_count=len(sorted_affected),
        created_campaigns_count=created_campaigns_count,
        replaced_seed_rows=replaced_seed_rows,
        affected_campaign_ids=sorted_affected,
        campaigns_touched=sorted_affected,
        errors=errors,
        message=f"Đã đồng bộ {imported_count + updated_count} dòng dữ liệu cho {len(sorted_affected)} chiến dịch.",
    )


@router.get("/campaigns/{campaign_id}/metrics/sample-csv")
@router.get("/metrics/campaign/{campaign_id}/sample-csv")
def get_campaign_sample_ads_csv(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sinh file CSV mẫu chuẩn xuất từ trình quản lý quảng cáo (Facebook/TikTok/Google/Email) cho chiến dịch."""
    campaign = check_campaign_access_for_metrics(campaign_id, current_user, db)
    base_budget = max(float(campaign.budget or 50000000.0), 10000000.0)
    daily_unit = round(base_budget / 15.0, 0)
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    sample_rows = [
        ["metric_date", "channel", "views", "clicks", "conversions", "cost", "revenue"],
        [today_str, "facebook", "48500", "2420", "145", str(int(daily_unit * 1.1)), str(int(daily_unit * 4.2))],
        [today_str, "tiktok", "92400", "4150", "210", str(int(daily_unit * 1.25)), str(int(daily_unit * 5.6))],
        [today_str, "email", "18200", "1640", "98", str(int(daily_unit * 0.25)), str(int(daily_unit * 2.8))],
    ]
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerows(sample_rows)
    return {
        "campaign_id": campaign.id,
        "campaign_name": campaign.name,
        "filename": f"ads_report_campaign_{campaign.id}.csv",
        "csv_content": buf.getvalue(),
    }


@router.post("/campaigns/{campaign_id}/metrics/import-csv")
@router.post("/metrics/campaign/{campaign_id}/import-csv")
def import_campaign_metrics_csv(
    campaign_id: int,
    req: CSVMetricsImportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Import trực tiếp file CSV/TSV báo cáo quảng cáo thực tế (Facebook Ads, TikTok Ads, Google Ads) vào CSDL."""
    campaign = check_campaign_access_for_metrics(campaign_id, current_user, db)

    raw_text = req.csv_content.strip().lstrip("\ufeff")
    delimiter = "\t" if ("\t" in raw_text.splitlines()[0] and "," not in raw_text.splitlines()[0]) else ","
    reader = csv.DictReader(io.StringIO(raw_text), delimiter=delimiter)

    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="File CSV không có dòng tiêu đề cột hợp lệ.")

    purged_seed_count = 0
    if req.replace_seed_data:
        seed_q = db.query(CampaignMetric).filter(
            CampaignMetric.campaign_id == campaign.id,
            or_(CampaignMetric.source == "seed", CampaignMetric.source.is_(None)),
        )
        purged_seed_count = seed_q.count()
        seed_q.delete(synchronize_session=False)
        db.flush()

    imported_count = 0
    updated_count = 0
    today_fallback = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    for row in reader:
        norm = {str(k or "").strip().lower(): v for k, v in row.items() if k is not None}
        if not any(norm.values()):
            continue

        m_date = (
            norm.get("metric_date")
            or norm.get("date")
            or norm.get("ngày")
            or norm.get("ngay")
            or norm.get("reporting starts")
            or norm.get("day")
            or today_fallback
        )
        m_date = _normalize_date_str(m_date, today_fallback)

        ch_label = (
            norm.get("channel")
            or norm.get("channel_code")
            or norm.get("platform")
            or norm.get("kênh")
            or norm.get("kenh")
            or norm.get("source")
            or "facebook"
        )
        channel_obj = _resolve_channel_from_label(db, str(ch_label))

        views = int(_parse_number(norm.get("views") or norm.get("impressions") or norm.get("lượt xem") or norm.get("reach") or 0))
        clicks = int(_parse_number(norm.get("clicks") or norm.get("link clicks") or norm.get("lượt nhấp") or 0))
        conversions = int(_parse_number(norm.get("conversions") or norm.get("results") or norm.get("purchases") or norm.get("leads") or norm.get("chuyển đổi") or 0))
        cost = _parse_number(norm.get("cost") or norm.get("spend") or norm.get("amount spent") or norm.get("chi phí") or 0, is_float=True)
        revenue = _parse_number(norm.get("revenue") or norm.get("purchase conversion value") or norm.get("conversion value") or norm.get("doanh thu") or 0, is_float=True)

        if clicks > views:
            views = clicks

        existing = db.query(CampaignMetric).filter(
            CampaignMetric.campaign_id == campaign.id,
            CampaignMetric.channel_id == channel_obj.id,
            CampaignMetric.metric_date == m_date,
        ).first()

        if existing:
            existing.views = views
            existing.clicks = clicks
            existing.conversions = conversions
            existing.cost = cost
            existing.revenue = revenue
            existing.source = "csv_import"
            updated_count += 1
        else:
            db.add(
                CampaignMetric(
                    campaign_id=campaign.id,
                    channel_id=channel_obj.id,
                    metric_date=m_date,
                    views=views,
                    clicks=clicks,
                    conversions=conversions,
                    cost=cost,
                    revenue=revenue,
                    source="csv_import",
                )
            )
            imported_count += 1

    if imported_count == 0 and updated_count == 0:
        db.rollback()
        raise HTTPException(status_code=400, detail="Không tìm thấy dòng dữ liệu hợp lệ nào trong file CSV.")

    db.commit()
    return {
        "status": "success",
        "campaign_id": campaign.id,
        "campaign_name": campaign.name,
        "imported_rows": imported_count,
        "updated_rows": updated_count,
        "purged_seed_rows": purged_seed_count,
        "source_tag": "csv_import",
    }


@router.post("/metrics/verify-real-data")
@router.post("/analytics/verify-real-data")
def verify_or_purge_demo_metrics(
    req: VerifyRealDataRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Chuyển đổi trạng thái dữ liệu từ Dữ liệu Mẫu (Seed) sang Đã Xác Thực Thực Tế (Verified Real Data)."""
    if req.campaign_id is not None:
        camp = check_campaign_access_for_metrics(req.campaign_id, current_user, db)
        allowed_ids = [camp.id]
    elif current_user.role == "ADMIN":
        allowed_ids = [r[0] for r in db.query(Campaign.id).all()]
    else:
        ws_ids = _accessible_workspace_ids(current_user, db)
        q = db.query(Campaign.id)
        if ws_ids:
            q = q.filter(or_(Campaign.workspace_id.in_(ws_ids), Campaign.owner_id == current_user.id))
        else:
            q = q.filter(Campaign.owner_id == current_user.id)
        allowed_ids = [r[0] for r in q.all()]

    if not allowed_ids:
        return {"status": "noop", "affected_rows": 0}

    q_metrics = db.query(CampaignMetric).filter(
        CampaignMetric.campaign_id.in_(allowed_ids),
        or_(CampaignMetric.source == "seed", CampaignMetric.source.is_(None)),
    )
    affected = q_metrics.count()
    if req.mode == "purge_seed":
        q_metrics.delete(synchronize_session=False)
    else:
        q_metrics.update({CampaignMetric.source: "verified_ads"}, synchronize_session=False)
    db.commit()
    return {
        "status": "success",
        "mode": req.mode,
        "affected_rows": affected,
        "campaigns_count": len(allowed_ids),
    }


@router.get("/analytics/morning-briefing")
@router.get("/metrics/morning-briefing")
def get_ai_morning_briefing(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """AI Morning Briefing & Anomaly Detector:
    Phân tích toàn bộ dữ liệu thực tế mỗi sáng, phát hiện kênh hiệu quả nhất, cảnh báo điểm nghẽn CPA/ROAS,
    và chuẩn bị sẵn lệnh tái phân bổ ngân sách 1-Click qua MCP cho chiến dịch có mức độ ưu tiên tối ưu cao nhất.
    """
    dash = get_global_dashboard(current_user=current_user, db=db)
    kpi = dash.get("kpi") or {}
    channels = kpi.get("channel_metrics") or []
    spend_map = dash.get("campaign_spend") or {}

    if current_user.role == "ADMIN":
        camps = db.query(Campaign).filter(Campaign.status != "ARCHIVED").order_by(Campaign.id.asc()).all()
    else:
        ws_ids = _accessible_workspace_ids(current_user, db)
        q = db.query(Campaign).filter(Campaign.status != "ARCHIVED")
        if ws_ids:
            q = q.filter(or_(Campaign.workspace_id.in_(ws_ids), Campaign.owner_id == current_user.id))
        else:
            q = q.filter(Campaign.owner_id == current_user.id)
        camps = q.order_by(Campaign.id.asc()).all()

    # Chọn chiến dịch ưu tiên tối ưu hóa cao nhất (thay vì luôn chọn camps[0]):
    # Ưu tiên chiến dịch ACTIVE có chi tiêu cao nhưng ROAS thấp hoặc tổng chi tiêu lớn nhất.
    primary_camp = None
    if camps:
        camp_ids = [c.id for c in camps]
        rev_rows = (
            db.query(
                CampaignMetric.campaign_id,
                func.sum(CampaignMetric.cost).label("cost"),
                func.sum(CampaignMetric.revenue).label("rev"),
            )
            .filter(CampaignMetric.campaign_id.in_(camp_ids))
            .group_by(CampaignMetric.campaign_id)
            .all()
        )
        perf_by_camp = {
            r.campaign_id: (float(r.cost or 0.0), float(r.rev or 0.0))
            for r in rev_rows
        }

        def _urgency_key(c: Campaign):
            is_active = 1 if c.status == "ACTIVE" else 0
            cost_val, rev_val = perf_by_camp.get(c.id, (float(spend_map.get(str(c.id), 0.0)), 0.0))
            roas_val = (rev_val / cost_val) if cost_val > 0 else 99.0
            needs_rescue = 1 if (cost_val > 0 and roas_val < 2.0) else 0
            return (is_active, needs_rescue, cost_val, float(c.budget or 0.0))

        primary_camp = max(camps, key=_urgency_key)

    top_channel = max(channels, key=lambda c: float(c.get("roas") or 0.0)) if channels else None
    weak_channel = min(channels, key=lambda c: float(c.get("roas") or 999.0)) if len(channels) > 1 else None

    anomalies: List[Dict[str, Any]] = []
    if weak_channel and top_channel and weak_channel.get("channel_code") != top_channel.get("channel_code"):
        w_roas = float(weak_channel.get("roas") or 0.0)
        t_roas = float(top_channel.get("roas") or 0.0)
        w_cost = float(weak_channel.get("cost") or 0.0)
        shift_amount = round(w_cost * 0.30, 0) if w_cost > 0 else 5000000.0
        anomalies.append({
            "id": f"anomaly-{weak_channel.get('channel_code')}",
            "severity": "HIGH" if w_roas < 2.0 else "MEDIUM",
            "channel_name": weak_channel.get("channel_name"),
            "title": f"Hiệu suất kênh {weak_channel.get('channel_name')} thấp hơn trung bình (ROAS {w_roas:.2f}x)",
            "detail": (
                f"Kênh {weak_channel.get('channel_name')} đã chi {w_cost:,.0f} đ với CPA {float(weak_channel.get('cpa_avg') or 0):,.0f} đ/chuyển đổi, "
                f"trong khi {top_channel.get('channel_name')} đạt ROAS {t_roas:.2f}x (CVR {float(top_channel.get('cvr_percent') or 0):.2f}%)."
            ),
            "recommendation": (
                f"Khuyến nghị điều chuyển {shift_amount:,.0f} đ từ {weak_channel.get('channel_name')} "
                f"sang {top_channel.get('channel_name')} để tăng hiệu suất ROAS tổng thể thêm ~18-24%."
            ),
            "shift_amount_vnd": shift_amount,
        })

    total_rev = float(kpi.get("total_revenue") or 0.0)
    total_cost = float(kpi.get("total_cost") or 0.0)
    overall_roas = float(kpi.get("roas") or 0.0)

    headline = (
        f"Tổng doanh thu ghi nhận đạt {total_rev:,.0f} đ trên chi phí {total_cost:,.0f} đ (ROAS {overall_roas:.2f}x). "
        + (
            f"Kênh dẫn đầu: {top_channel.get('channel_name')} (ROAS {float(top_channel.get('roas') or 0):.2f}x)."
            if top_channel
            else "Hãy nạp báo cáo CSV Ads để AI bắt đầu phân tích phễu kênh."
        )
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat() + "Z",
        "headline": headline,
        "overall_roas": overall_roas,
        "top_performer": top_channel,
        "weakest_performer": weak_channel,
        "anomalies": anomalies,
        "rebalance_action": {
            "available": primary_camp is not None and len(channels) > 0,
            "campaign_id": primary_camp.id if primary_camp else None,
            "campaign_name": primary_camp.name if primary_camp else None,
            "budget": float(primary_camp.budget or 0.0) if primary_camp else 0.0,
            "button_label": (
                f"Tự động Tái phân bổ Ngân sách '{primary_camp.name}' theo ROAS (MCP)"
                if primary_camp
                else "Tái phân bổ Ngân sách (MCP)"
            ),
        },
    }
