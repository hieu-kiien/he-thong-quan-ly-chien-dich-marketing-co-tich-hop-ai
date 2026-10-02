from typing import List, Dict, Any, Optional
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, or_, and_
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.entities import CampaignMetric, Campaign, MarketingChannel, User, CampaignMember, Workspace, WorkspaceMember, Task, MarketingContent
from app.schemas.schemas import (
    MetricCreate,
    MetricResponse,
    KPISummaryResponse,
    ChannelAttributionResponse,
    AIDoctorResponse,
    CommandCenterResponse,
    CommandCenterAttentionItem,
    CommandCenterMyWorkItem,
    CommandCenterCampaignHealth
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
    else:
        metrics = []
        campaigns_count = 0
        active_campaigns = 0

    # Chi phí theo từng chiến dịch. Bảng chiến dịch ở Dashboard và ở trang
    # Quản lý đều cần nhịp chi tiêu (đã chi / ngân sách); không có field này
    # thì giao diện buộc phải hiện "chưa ghi nhận chi phí" dù tổng chi phí ngay
    # phía trên đã tính ra — hai phần của cùng một màn hình nói hai sự thật khác nhau.
    # Tính ngay từ các dòng CampaignMetric đã nạp ở trên, không phát sinh truy vấn
    # thêm.
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
            "active": active_campaigns
        },
        # Chi phí thực đo theo từng chiến dịch (khoá là campaign_id dạng chuỗi vì
        # JSON object bắt buộc khoá chuỗi).
        "campaign_spend": campaign_spend,
        # Frontend đọc trực tiếp field này để vẽ biểu đồ attribution. Trước đây
        # response không có nó nên client rơi về `|| MOCK_CHANNEL_ATTRIBUTIONS`, tức là
        # production hiển thị số liệu bịa đặt.
        "channel_attributions": _aggregate_channel_attribution(db, allowed_ids),
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
    """Dùng đúng công thức attribution của AIDoctorEngine nhưng gộp nhiều chiến dịch.

    `AIDoctorEngine.compute_channel_attribution` chỉ nhận một campaign_id, nên gọi
    nó trong vòng lặp rồi cộng tay sẽ trả kết quả sai (thiếu phần doanh thu của
    các chiến dịch còn lại trên cùng kênh). Ở đây gộp trực tiếp từ CampaignMetric
    theo cùng định nghĩa chỉ số.
    """
    return _aggregate_channel_metrics(db, campaign_ids)


get_metrics_overview = get_global_dashboard


# --- COMMAND CENTER ENDPOINTS ---

@router.get("/analytics/command-center", response_model=CommandCenterResponse)
@router.get("/metrics/command-center", response_model=CommandCenterResponse)
def get_command_center(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Command Center điều phối vận hành chiến dịch Marketing theo thời gian thực:
    - What needs attention: Tác vụ quá hạn, nội dung chờ duyệt, cảnh báo ngân sách, hạn chót chiến dịch.
    - What's my work today: Tác vụ được giao cho người dùng hiện tại cần xử lý.
    - Active campaigns health: Đánh giá sức khỏe chiến dịch theo luật tất định (deterministic rules).
    """
    today_str = datetime.utcnow().strftime("%Y-%m-%d")

    # 1. Xác định phạm vi chiến dịch được truy cập
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

    # 2. Attention Items - Overdue Tasks
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

    # 3. Attention Items - Pending Approvals (Contents in IN_REVIEW, AI_DRAFT)
    #
    # Danh sách hiển thị bị giới hạn 15 bản ghi (để payload Command Center không
    # phình), nhưng `total_pending_approvals` phải là TỔNG số thực, không phải
    # `len(pending_contents)` — trước đây con số này âm thầm bị chặn ở 15 và bị
    # hiển thị cho người dùng như tổng số.
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

    # 4. Attention Items - Budget Overruns, Budget Risk & Proximity to Deadline
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

        # KPI Tracking
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

        # Budget Risk rule: budget_utilization > 80% AND kpi_achievement < 60%
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

        # Tính điểm sức khỏe chiến dịch tất định (Deterministic Health Score)
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

    # 5. My Work Today - Ngăn ngừa rò rỉ cross-tenant (chỉ lấy task trong campaign/workspace được cấp quyền)
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
