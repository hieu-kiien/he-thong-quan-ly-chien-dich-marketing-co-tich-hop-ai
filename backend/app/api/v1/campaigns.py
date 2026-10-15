from typing import Optional, List
import hashlib
import json
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query, Header
from sqlalchemy.orm import Session
from sqlalchemy import and_, false, or_
from sqlalchemy.exc import IntegrityError
from app.core.database import get_db
from app.core.pagination import Page, PageParams, page_params, paginate_query
from app.core.security import RoleChecker, get_current_user
from app.services import quota
from app.services import campaign_lifecycle
from app.models.entities import Campaign, Product, User, CampaignMember, WorkspaceMember, Workspace, MarketingContent, CampaignBudgetAllocation, CampaignKPITarget, MarketingChannel, Task, CampaignMetric, CampaignPlanApplication
from app.schemas.schemas import (
    CampaignCreate,
    CampaignUpdate,
    CampaignResponse,
    ContentResponse,
    BudgetAllocationCreate,
    BudgetAllocationResponse,
    BudgetSummaryResponse,
    BudgetChannelSummary,
    KPITargetCreate,
    KPITargetResponse,
    KpiProgressResponse,
    KpiProgressTarget,
    PlanApplyRequest,
    PlanApplyResponse,
    CampaignGridSummaryResponse,
    CampaignBulkActionRequest,
    CampaignBulkActionResponse,
    SeedAngleMatrixRequest,
    SeedAngleMatrixResponse,
    PortfolioTriageResponse,
    WinningPatternsResponse,
)
from app.services.ai.ai_doctor import AIDoctorEngine
from app.services.ai.ai_service import ai_service


router = APIRouter(prefix="/campaigns", tags=["Quản lý Chiến dịch"])

# Khoá sắp xếp được phép (allowlist). `sort` là dữ liệu do client gửi nên không
# bao giờ nối thẳng vào ORDER BY — chỉ map sang cột đã biết ở đây.
_CAMPAIGN_SORT_KEYS = (
    "newest", "oldest", "name_asc", "name_desc",
    "budget_asc", "budget_desc", "start_date",
    "roas_desc", "roas_asc", "spend_desc",
)

# Khoá sắp xếp của danh sách NỘI DUNG. Khác `/_CAMPAIGN_SORT_KEYS`: bảng
# `marketing_contents` không có cột chi phí, nên sắp theo ngân sách là vô nghĩa
# và đã từng làm endpoint `/campaigns/{id}/contents` ném 500.
_CONTENT_SORT_KEYS = (
    "newest", "oldest", "name_asc", "name_desc", "status_asc", "updated_desc",
)

_SORT_DESCRIPTION = (
    "Thứ tự sắp xếp: " + " | ".join(_CAMPAIGN_SORT_KEYS) + " (mặc định newest)"
)


def campaign_page_params(
    page: int = Query(1, ge=1, description="Số trang, bắt đầu từ 1"),
    page_size: int = Query(20, ge=1, le=200, description="Số bản ghi mỗi trang (1..200)"),
) -> PageParams:
    """Dependency phân trang riêng cho Campaign Grid mật độ cao (tối đa 200 dòng/trang)."""
    return PageParams(page=page, page_size=page_size)


def _accessible_workspace_ids(user: User, db: Session) -> List[int]:
    """Danh sách workspace_id mà user thực sự có quyền: workspace họ làm chủ
    (Workspace.owner_id) hoặc họ là thành viên (WorkspaceMember).
    """
    owned_ids = [row[0] for row in db.query(Workspace.id).filter(Workspace.owner_id == user.id).all()]
    member_ids = [
        row[0]
        for row in db.query(WorkspaceMember.workspace_id)
        .filter(WorkspaceMember.user_id == user.id)
        .all()
    ]
    return sorted({int(ws_id) for ws_id in set(owned_ids) | set(member_ids) if ws_id is not None})


def _apply_tenant_scope(query, model, user: User, db: Session, null_owner_column):
    """Giới hạn truy vấn theo tenant thực sự của user (fail-closed)."""
    ws_ids = _accessible_workspace_ids(user, db)
    in_ws = model.workspace_id.in_(ws_ids) if ws_ids else false()
    return query.filter(
        or_(
            in_ws,
            and_(model.workspace_id.is_(None), null_owner_column == user.id),
        )
    )


def check_campaign_access(campaign: Campaign, user: User, db: Session):
    """Xác thực phân quyền mức bản ghi và cách ly đa người thuê (Tenant Isolation)."""
    if user.role == "ADMIN":
        return

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
            return

    if campaign.owner_id == user.id:
        return

    is_member = db.query(CampaignMember).filter(
        CampaignMember.campaign_id == campaign.id,
        CampaignMember.user_id == user.id
    ).first()
    if is_member:
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not authorized to access this resource"
    )


def resolve_effective_workspace_id(
    db: Session,
    current_user: User,
    workspace_id: Optional[int] = None,
    header_workspace_id: Optional[str] = None,
) -> Optional[int]:
    """Chốt workspace hiện hành của request, theo thứ tự ưu tiên."""
    if workspace_id is not None:
        return workspace_id
    if header_workspace_id:
        try:
            return int(header_workspace_id)
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Header X-Workspace-Id không phải là số nguyên hợp lệ",
            )
    return None


def get_workspace_filter(
    workspace_id: Optional[int] = Query(None, alias="workspace_id"),
    x_workspace_id: Optional[str] = Header(None, alias="X-Workspace-Id"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Optional[int]:
    """Dependency trả về workspace hiện hành, hoặc None nếu không yêu cầu lọc."""
    target = resolve_effective_workspace_id(db, current_user, workspace_id, x_workspace_id)
    if target is None:
        return None
    if current_user.role != "ADMIN":
        ws = db.query(Workspace).filter(Workspace.id == target).first()
        is_ws_owner = ws is not None and ws.owner_id == current_user.id
        is_ws_member = db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == target,
            WorkspaceMember.user_id == current_user.id
        ).first() is not None
        if not (is_ws_owner or is_ws_member):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access data in this workspace",
            )
    return target


def _bulk_task_progress(db: Session, campaign_ids: list[int]) -> dict[int, dict]:
    if not campaign_ids:
        return {}
    rows = (
        db.query(Task.campaign_id, Task.status)
        .filter(Task.campaign_id.in_(campaign_ids))
        .all()
    )
    out: dict[int, dict] = {cid: {"done": 0, "total": 0} for cid in campaign_ids}
    for cid, tstatus in rows:
        out[cid]["total"] += 1
        if (tstatus or "").upper() in ("DONE", "COMPLETED"):
            out[cid]["done"] += 1
    return out


def _bulk_content_and_metric_enrichment(
    db: Session, campaigns: list[Campaign]
) -> tuple[dict[int, dict], dict[int, dict]]:
    """Tổng hợp số lượng nội dung, kênh và chỉ số kinh tế (ROAS/Pacing/Fatigue) bằng truy vấn bulk không N+1."""
    campaign_ids = [c.id for c in campaigns]
    if not campaign_ids:
        return {}, {}

    content_info: dict[int, dict] = {
        cid: {"total": 0, "approved": 0, "channels": set()} for cid in campaign_ids
    }
    content_rows = (
        db.query(MarketingContent.campaign_id, MarketingContent.status, MarketingChannel.code)
        .outerjoin(MarketingChannel, MarketingContent.channel_id == MarketingChannel.id)
        .filter(MarketingContent.campaign_id.in_(campaign_ids))
        .all()
    )
    for cid, cstatus, ch_code in content_rows:
        if cid not in content_info:
            continue
        content_info[cid]["total"] += 1
        if (cstatus or "").upper() in ("APPROVED", "PUBLISHED"):
            content_info[cid]["approved"] += 1
        if ch_code:
            content_info[cid]["channels"].add(str(ch_code).lower())

    channel_code_by_id = {
        ch_id: str(ch_code).lower()
        for ch_id, ch_code in db.query(MarketingChannel.id, MarketingChannel.code).all()
        if ch_code
    }

    metric_rows = (
        db.query(CampaignMetric)
        .filter(CampaignMetric.campaign_id.in_(campaign_ids))
        .all()
    )
    metrics_by_cid: dict[int, list[CampaignMetric]] = {cid: [] for cid in campaign_ids}
    for m in metric_rows:
        if m.campaign_id in metrics_by_cid:
            metrics_by_cid[m.campaign_id].append(m)
            ch_code = channel_code_by_id.get(m.channel_id)
            if ch_code and m.campaign_id in content_info:
                content_info[m.campaign_id]["channels"].add(ch_code)

    metrics_summary_by_cid: dict[int, dict] = {}
    for camp in campaigns:
        cid = camp.id
        m_list = metrics_by_cid.get(cid, [])
        views = sum(int(m.views or 0) for m in m_list)
        clicks = sum(int(m.clicks or 0) for m in m_list)
        conversions = sum(int(m.conversions or 0) for m in m_list)
        cost = sum(float(m.cost or 0.0) for m in m_list)
        revenue = sum(float(m.revenue or 0.0) for m in m_list)

        ctr = round((clicks / views * 100.0) if views > 0 else 0.0, 2)
        cvr = round((conversions / clicks * 100.0) if clicks > 0 else 0.0, 2)
        cpc = round((cost / clicks) if clicks > 0 else 0.0, 2)
        cpa = round((cost / conversions) if conversions > 0 else 0.0, 2)
        roas = round((revenue / cost) if cost > 0 else 0.0, 2)
        budget_val = float(camp.budget or 0.0)
        budget_util = round((cost / budget_val * 100.0) if budget_val > 0 else 0.0, 2)

        pacing = AIDoctorEngine.compute_budget_pacing(camp, m_list, cost)
        fatigue = AIDoctorEngine.detect_creative_fatigue(m_list)
        funnel_stage = AIDoctorEngine.infer_funnel_stage(camp.objective, getattr(camp, "funnel_stage", None))

        is_tofu_non_rev = (funnel_stage == "ToFU" and revenue == 0)
        is_mofu_lead_gen = (funnel_stage == "MoFU" and revenue == 0 and conversions > 0)
        if not m_list or (views == 0 and cost == 0):
            health_status = "HEALTHY"
        elif not is_tofu_non_rev and not is_mofu_lead_gen and cost > 0 and roas < 1.0:
            health_status = "CRITICAL"
        elif fatigue.get("fatigue_detected") or pacing.get("pacing_status") == "OVER_PACING":
            health_status = "NEEDS_ATTENTION"
        else:
            health_status = "HEALTHY"

        metrics_summary_by_cid[cid] = {
            "views": views,
            "clicks": clicks,
            "conversions": conversions,
            "cost": round(cost, 2),
            "revenue": round(revenue, 2),
            "row_count": len(m_list),
            "total_views": views,
            "total_clicks": clicks,
            "total_conversions": conversions,
            "total_cost": round(cost, 2),
            "total_revenue": round(revenue, 2),
            "ctr": ctr,
            "cvr": cvr,
            "cpc": cpc,
            "cpa": cpa,
            "roas": roas,
            "budget_utilization_pct": budget_util,
            "pacing_ratio": pacing.get("pacing_ratio"),
            "pacing_status": pacing.get("pacing_status"),
            "fatigue_detected": bool(fatigue.get("fatigue_detected", False)),
            "health_status": health_status,
            "funnel_stage": funnel_stage,
        }

    return content_info, metrics_summary_by_cid


def _serialize_campaign_list(
    db: Session, campaigns: list[Campaign]
) -> list[CampaignResponse]:
    if not campaigns:
        return []
    progress = _bulk_task_progress(db, [c.id for c in campaigns])
    content_info, metrics_info = _bulk_content_and_metric_enrichment(db, campaigns)
    result: list[CampaignResponse] = []
    for c in campaigns:
        resp = CampaignResponse.model_validate(c)
        if not resp.funnel_stage:
            resp.funnel_stage = AIDoctorEngine.infer_funnel_stage(c.objective, getattr(c, "funnel_stage", None))
        counts = progress.get(c.id, {"done": 0, "total": 0})
        resp.progress_pct = campaign_lifecycle.compute_progress_pct(
            counts["done"], counts["total"]
        )
        c_meta = content_info.get(c.id, {"total": 0, "approved": 0, "channels": set()})
        resp.contents_count = c_meta["total"]
        resp.approved_contents_count = c_meta["approved"]
        resp.channels = sorted(list(c_meta["channels"]))
        resp.metrics_summary = metrics_info.get(c.id)
        result.append(resp)
    return result


def _with_progress(db: Session, campaign: Campaign) -> CampaignResponse:
    """Kèm progress_pct và metrics_summary tính từ bulk serializer."""
    return _serialize_campaign_list(db, [campaign])[0]


def _build_scoped_campaign_query(
    db: Session,
    current_user: User,
    workspace_id: Optional[int],
    include_archived: bool = False,
):
    query = db.query(Campaign)
    if not include_archived:
        query = query.filter(
            Campaign.status.notin_(list(campaign_lifecycle.HIDDEN_FROM_DEFAULT_LIST))
        )
    if current_user.role not in ("ADMIN", "MANAGER", "AGENCY_MANAGER"):
        member_campaign_ids = db.query(CampaignMember.campaign_id).filter(CampaignMember.user_id == current_user.id)
        query = query.filter(
            (Campaign.owner_id == current_user.id) |
            (Campaign.id.in_(member_campaign_ids))
        )
    if current_user.role != "ADMIN":
        query = _apply_tenant_scope(query, Campaign, current_user, db, Campaign.owner_id)
    if workspace_id is not None:
        query = query.filter(Campaign.workspace_id == workspace_id)
    return query


@router.get("", response_model=Page[CampaignResponse])
def get_campaigns(
    workspace_id: Optional[int] = Depends(get_workspace_filter),
    status_filter: Optional[str] = Query(None, alias="status"),
    channel_id: Optional[int] = Query(None, alias="channel_id"),
    channel: Optional[str] = Query(None, description="Lọc theo mã kênh (facebook, tiktok, google_ads, email, blog)"),
    funnel_stage: Optional[str] = Query(None, description="Lọc theo tầng phễu: ToFU | MoFU | BoFU"),
    health_filter: Optional[str] = Query(None, description="Lọc sức khỏe: over_pacing | under_pacing | fatigue | low_roas | critical | healthy"),
    tag: Optional[str] = Query(None, description="Lọc theo tag chiến dịch"),
    start_date: Optional[str] = Query(None, alias="start_date"),
    end_date: Optional[str] = Query(None, alias="end_date"),
    search: Optional[str] = Query(None),
    objective: Optional[str] = Query(
        None, description="Lọc theo mục tiêu chiến dịch (khớp chuỗi con)"
    ),
    sort: str = Query("newest", description=_SORT_DESCRIPTION),
    pagination: PageParams = Depends(campaign_page_params),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    want_archived = status_filter is not None and campaign_lifecycle.normalize_status(status_filter) == "ARCHIVED"
    query = _build_scoped_campaign_query(db, current_user, workspace_id, include_archived=want_archived)

    if status_filter:
        query = query.filter(Campaign.status == status_filter)
    if funnel_stage:
        query = query.filter(Campaign.funnel_stage == funnel_stage.strip())
    if tag:
        query = query.filter(Campaign.tags_json.ilike(f"%{tag.strip()}%"))
    if start_date:
        query = query.filter(Campaign.start_date >= start_date)
    if end_date:
        query = query.filter(Campaign.end_date <= end_date)
    if channel_id:
        query = query.join(MarketingContent).filter(MarketingContent.channel_id == channel_id).distinct()
    if channel:
        ch_obj = db.query(MarketingChannel).filter(MarketingChannel.code == channel.strip().lower()).first()
        if ch_obj:
            query = query.join(MarketingContent).filter(MarketingContent.channel_id == ch_obj.id).distinct()
        else:
            query = query.filter(false())
    if search:
        search_fmt = f"%{search}%"
        query = query.filter(
            (Campaign.name.ilike(search_fmt)) |
            (Campaign.objective.ilike(search_fmt)) |
            (Campaign.audience.ilike(search_fmt)) |
            (Campaign.campaign_code.ilike(search_fmt))
        )
    if objective:
        query = query.filter(Campaign.objective.ilike(f"%{objective}%"))

    sort_key = (sort or "newest").strip().lower()
    if sort_key not in _CAMPAIGN_SORT_KEYS:
        raise HTTPException(
            status_code=422,
            detail=f"Giá trị sort không hợp lệ. Chỉ nhận: {', '.join(_CAMPAIGN_SORT_KEYS)}.",
        )

    if health_filter or sort_key in ("roas_desc", "roas_asc", "spend_desc"):
        all_camps = query.order_by(Campaign.created_at.desc(), Campaign.id.desc()).all()
        serialized = _serialize_campaign_list(db, all_camps)
        if health_filter:
            hf = health_filter.strip().lower()
            filtered_items = []
            for item in serialized:
                ms = item.metrics_summary or {}
                if hf == "over_pacing" and ms.get("pacing_status") == "OVER_PACING":
                    filtered_items.append(item)
                elif hf == "under_pacing" and ms.get("pacing_status") == "UNDER_PACING":
                    filtered_items.append(item)
                elif hf == "fatigue" and ms.get("fatigue_detected"):
                    filtered_items.append(item)
                elif hf == "low_roas" and (ms.get("total_cost", 0) > 0 and ms.get("roas", 0) < 1.0):
                    filtered_items.append(item)
                elif hf == "critical" and ms.get("health_status") == "CRITICAL":
                    filtered_items.append(item)
                elif hf == "healthy" and ms.get("health_status") == "HEALTHY":
                    filtered_items.append(item)
            serialized = filtered_items

        if sort_key == "roas_desc":
            serialized.sort(key=lambda x: ((x.metrics_summary or {}).get("roas", 0.0), x.id), reverse=True)
        elif sort_key == "roas_asc":
            serialized.sort(key=lambda x: ((x.metrics_summary or {}).get("roas", 0.0), x.id))
        elif sort_key == "spend_desc":
            serialized.sort(key=lambda x: ((x.metrics_summary or {}).get("total_cost", 0.0), x.id), reverse=True)

        total = len(serialized)
        sliced = serialized[pagination.offset : pagination.offset + pagination.page_size]
        return Page.build(
            items=sliced,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )

    order_by = {
        "newest": (Campaign.created_at.desc(), Campaign.id.desc()),
        "oldest": (Campaign.created_at.asc(), Campaign.id.asc()),
        "name_asc": (Campaign.name.asc(), Campaign.id.asc()),
        "name_desc": (Campaign.name.desc(), Campaign.id.desc()),
        "budget_asc": (Campaign.budget.asc(), Campaign.id.asc()),
        "budget_desc": (Campaign.budget.desc(), Campaign.id.desc()),
        "start_date": (Campaign.start_date.desc(), Campaign.id.desc()),
    }[sort_key]

    page = paginate_query(query.order_by(*order_by), pagination)
    return Page.build(
        items=_serialize_campaign_list(db, page.items),
        total=page.total,
        page=page.page,
        page_size=page.page_size,
    )


@router.get("/grid-summary", response_model=CampaignGridSummaryResponse)
def get_campaigns_grid_summary(
    workspace_id: Optional[int] = Depends(get_workspace_filter),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Tổng hợp KPI toàn danh mục cho thanh điều khiển 1,000 chiến dịch (Grid Summary)."""
    query = _build_scoped_campaign_query(db, current_user, workspace_id, include_archived=False)
    campaigns = query.all()
    if not campaigns:
        return CampaignGridSummaryResponse(
            total_campaigns=0,
            status_counts={},
            funnel_counts={"ToFU": 0, "MoFU": 0, "BoFU": 0},
            total_budget=0.0,
            total_spent=0.0,
            total_revenue=0.0,
            overall_roas=0.0,
            anomaly_counts={"over_pacing": 0, "under_pacing": 0, "fatigue": 0, "low_roas": 0},
        )

    _, metrics_map = _bulk_content_and_metric_enrichment(db, campaigns)
    status_counts: dict[str, int] = {}
    funnel_counts: dict[str, int] = {"ToFU": 0, "MoFU": 0, "BoFU": 0}
    anomaly_counts: dict[str, int] = {"over_pacing": 0, "under_pacing": 0, "fatigue": 0, "low_roas": 0}
    total_budget = 0.0
    total_spent = 0.0
    total_revenue = 0.0

    for c in campaigns:
        st = (c.status or "DRAFT").upper()
        status_counts[st] = status_counts.get(st, 0) + 1
        fn = AIDoctorEngine.infer_funnel_stage(c.objective, getattr(c, "funnel_stage", None))
        funnel_counts[fn] = funnel_counts.get(fn, 0) + 1
        total_budget += float(c.budget or 0.0)

        ms = metrics_map.get(c.id, {})
        c_spent = float(ms.get("total_cost", 0.0))
        c_rev = float(ms.get("total_revenue", 0.0))
        total_spent += c_spent
        total_revenue += c_rev

        if ms.get("pacing_status") == "OVER_PACING":
            anomaly_counts["over_pacing"] += 1
        elif ms.get("pacing_status") == "UNDER_PACING":
            anomaly_counts["under_pacing"] += 1
        if ms.get("fatigue_detected"):
            anomaly_counts["fatigue"] += 1
        if c_spent > 0 and float(ms.get("roas", 0.0)) < 1.0 and fn == "BoFU":
            anomaly_counts["low_roas"] += 1

    overall_roas = round((total_revenue / total_spent) if total_spent > 0 else 0.0, 2)
    return CampaignGridSummaryResponse(
        total_campaigns=len(campaigns),
        status_counts=status_counts,
        funnel_counts=funnel_counts,
        total_budget=round(total_budget, 2),
        total_spent=round(total_spent, 2),
        total_revenue=round(total_revenue, 2),
        overall_roas=overall_roas,
        anomaly_counts=anomaly_counts,
    )


@router.post("/bulk-action", response_model=CampaignBulkActionResponse)
def bulk_campaign_action(
    req: CampaignBulkActionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Thao tác hàng loạt trên nhiều chiến dịch (PAUSE, ACTIVATE, ARCHIVE, COMPLETE, DELETE, ADJUST_BUDGET, SET_DAILY_CAP, ADD_TAGS/ADD_TAG/ASSIGN_TAGS)."""
    if current_user.role not in ("ADMIN", "MANAGER", "AGENCY_MANAGER", "MARKETER"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không có quyền thực hiện thao tác hàng loạt trên chiến dịch",
        )

    campaigns = db.query(Campaign).filter(Campaign.id.in_(req.campaign_ids)).all()
    camp_map = {c.id: c for c in campaigns}
    updated_ids: list[int] = []
    skipped_ids: list[int] = []
    deleted_count = 0
    warnings: list[str] = []

    for cid in req.campaign_ids:
        camp = camp_map.get(cid)
        if not camp:
            skipped_ids.append(cid)
            continue
        try:
            check_campaign_access(camp, current_user, db)
        except HTTPException:
            skipped_ids.append(cid)
            continue

        privileged = current_user.role in ("ADMIN", "MANAGER", "AGENCY_MANAGER")
        is_owner = camp.owner_id == current_user.id
        if not (privileged or is_owner):
            skipped_ids.append(cid)
            continue

        if req.action == "PAUSE":
            if camp.status in ("ACTIVE", "PLANNED", "DRAFT"):
                camp.status = "PAUSED"
                updated_ids.append(cid)
            else:
                skipped_ids.append(cid)
        elif req.action == "ACTIVATE":
            if camp.status in ("DRAFT", "PLANNED", "PAUSED"):
                camp.status = "ACTIVE"
                updated_ids.append(cid)
            else:
                skipped_ids.append(cid)
        elif req.action == "COMPLETE":
            if camp.status != "COMPLETED":
                camp.status = "COMPLETED"
                updated_ids.append(cid)
            else:
                skipped_ids.append(cid)
        elif req.action == "ARCHIVE":
            if camp.status != "ARCHIVED":
                camp.status = "ARCHIVED"
                updated_ids.append(cid)
            else:
                skipped_ids.append(cid)
        elif req.action == "DELETE":
            if camp.status == "ACTIVE":
                camp.status = "ARCHIVED"
                updated_ids.append(cid)
            else:
                db.delete(camp)
                deleted_count += 1
                updated_ids.append(cid)
        elif req.action == "ADJUST_BUDGET":
            old_b = float(camp.budget or 0.0)
            if req.budget_mode == "SET" and req.budget_value is not None:
                new_b = max(0.0, float(req.budget_value))
                if old_b > 0 and ((new_b - old_b) / old_b) * 100.0 > 25.0:
                    warnings.append(f"Chiến dịch #{cid}: Tăng ngân sách >25% có nguy cơ reset Giai đoạn Máy học (Learning Phase).")
                camp.budget = round(new_b, 2)
            else:
                delta = float(
                    req.budget_delta_pct
                    if req.budget_delta_pct is not None
                    else (req.budget_value or 0.0)
                )
                if delta > 25.0:
                    warnings.append(f"Chiến dịch #{cid}: Tăng ngân sách +{delta:.1f}% vượt ngưỡng 25%/ngày (Learning Phase Warning).")
                camp.budget = round(max(0.0, old_b * (1.0 + delta / 100.0)), 2)
            updated_ids.append(cid)
        elif req.action == "SET_DAILY_CAP":
            camp.daily_budget_cap = float(req.daily_budget_cap or 0.0)
            updated_ids.append(cid)
        elif req.action in ("ADD_TAGS", "ADD_TAG", "ASSIGN_TAGS"):
            existing_tags = []
            try:
                existing_tags = json.loads(camp.tags_json or "[]")
            except Exception:
                existing_tags = []
            incoming = list(req.tags or [])
            if req.tag:
                incoming.append(req.tag)
            merged = list(dict.fromkeys([str(t).strip() for t in (existing_tags + incoming) if str(t).strip()]))
            camp.tags_json = json.dumps(merged, ensure_ascii=False)
            updated_ids.append(cid)

    db.commit()
    return CampaignBulkActionResponse(
        status="ok",
        action=req.action,
        requested_count=len(req.campaign_ids),
        updated_count=len(updated_ids),
        deleted_count=deleted_count,
        updated_ids=updated_ids,
        skipped_ids=skipped_ids,
        warnings=warnings,
        message=f"Đã thực thi '{req.action}' thành công trên {len(updated_ids)}/{len(req.campaign_ids)} chiến dịch.",
    )


@router.get("/portfolio-triage", response_model=PortfolioTriageResponse)
def get_portfolio_triage(
    workspace_id: Optional[int] = Depends(get_workspace_filter),
    limit: int = Query(25, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Quét danh mục chiến dịch phát hiện sớm bất thường (OVER_PACING, ZERO_CONVERSION_BLEED, CREATIVE_FATIGUE, ROAS_CRITICAL)."""
    query = _build_scoped_campaign_query(db, current_user, workspace_id, include_archived=False)
    campaigns = query.all()
    return AIDoctorEngine.scan_portfolio_triage(db, campaigns, limit=limit)


@router.get("/winning-patterns", response_model=WinningPatternsResponse)
def get_winning_patterns(
    workspace_id: Optional[int] = Depends(get_workspace_filter),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Trích xuất quy luật chiến thắng (Top Channel, Top Creative Angle, Playbook) từ dữ liệu thực của Workspace."""
    eff_ws_id = workspace_id
    if eff_ws_id is None:
        ws_ids = _accessible_workspace_ids(current_user, db)
        eff_ws_id = ws_ids[0] if ws_ids else 1
    data = ai_service.extract_winning_patterns(db=db, workspace_id=eff_ws_id)
    return WinningPatternsResponse.model_validate(data)


@router.post("", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
def create_campaign(
    req: CampaignCreate,
    current_user: User = Depends(get_current_user),
    user_payload: dict = Depends(RoleChecker(allowed_roles=["MANAGER", "AGENCY_MANAGER", "MARKETER", "ADMIN"])),
    x_workspace_id: Optional[str] = Header(None, alias="X-Workspace-Id"),
    db: Session = Depends(get_db)
):
    if current_user.role not in ("MANAGER", "AGENCY_MANAGER", "MARKETER", "ADMIN"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản không có quyền tạo chiến dịch"
        )
    user_id = current_user.id

    product = db.query(Product).filter(Product.id == req.product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sản phẩm không tồn tại")

    target_ws_id: Optional[int] = req.workspace_id
    if target_ws_id is None and x_workspace_id:
        try:
            target_ws_id = int(x_workspace_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Header X-Workspace-Id không hợp lệ"
            )

    if target_ws_id is not None:
        if current_user.role != "ADMIN":
            ws = db.query(Workspace).filter(Workspace.id == target_ws_id).first()
            if not ws:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace không tồn tại")
            is_ws_owner = ws is not None and ws.owner_id == user_id
            is_ws_member = db.query(WorkspaceMember).filter(
                WorkspaceMember.workspace_id == target_ws_id,
                WorkspaceMember.user_id == user_id
            ).first() is not None
            if not (is_ws_owner or is_ws_member):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to access campaigns in this workspace"
                )
        ws_id = target_ws_id
    else:
        membership = db.query(WorkspaceMember).filter(WorkspaceMember.user_id == user_id).first()
        owned_ws = db.query(Workspace).filter(Workspace.owner_id == user_id).first()
        if membership:
            ws_id = membership.workspace_id
        elif owned_ws:
            ws_id = owned_ws.id
        elif current_user.role == "ADMIN":
            ws_id = 1
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Người dùng không thuộc bất kỳ workspace nào hoặc không có quyền truy cập."
            )

    quota.enforce(db, quota.LIMIT_CAMPAIGNS, user=current_user, workspace_id=ws_id)

    inferred_funnel = AIDoctorEngine.infer_funnel_stage(req.objective, req.funnel_stage)
    ym_str = (req.start_date or "2026-10")[:7].replace("-", "")
    existing_count = db.query(Campaign).filter(Campaign.workspace_id == ws_id).count()
    auto_code = req.campaign_code or f"CMP-{ym_str}-{inferred_funnel.upper()}-{existing_count + 1:03d}"
    tags_json_str = req.tags_json or "[]"
    if req.tags:
        tags_json_str = json.dumps([str(t).strip() for t in req.tags if str(t).strip()], ensure_ascii=False)

    campaign = Campaign(
        workspace_id=ws_id,
        product_id=req.product_id,
        owner_id=user_id,
        name=req.name,
        objective=req.objective,
        audience=req.audience,
        start_date=req.start_date,
        end_date=req.end_date,
        budget=req.budget,
        key_message=req.key_message,
        primary_cta=req.primary_cta,
        target_kpi_name=req.target_kpi_name,
        target_kpi_value=req.target_kpi_value,
        campaign_code=auto_code,
        funnel_stage=inferred_funnel,
        daily_budget_cap=req.daily_budget_cap,
        tags_json=tags_json_str,
        status=campaign_lifecycle.assert_create_status(req.status),
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    member = CampaignMember(campaign_id=campaign.id, user_id=user_id, member_role="OWNER")
    db.add(member)
    db.commit()

    return _with_progress(db, campaign)


@router.post("/{campaign_id}/seed-angle-matrix", response_model=SeedAngleMatrixResponse, status_code=status.HTTP_201_CREATED)
def seed_campaign_angle_matrix(
    campaign_id: int,
    req: SeedAngleMatrixRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Tự động khởi tạo ma trận bài viết (Psychological Angle × Hook Variants) kèm UTM chuẩn hóa cho chiến dịch."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chiến dịch không tồn tại")
    check_campaign_access(campaign, current_user, db)
    if current_user.role == "CLIENT_APPROVER":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Client Approver không có quyền tạo nội dung")

    product = db.query(Product).filter(Product.id == campaign.product_id).first()
    channels = db.query(MarketingChannel).all()
    ch_map = {c.id: c for c in channels}
    ch_by_code = {(c.code or "").lower(): c for c in channels}

    if req.channel_ids:
        target_channel_ids = req.channel_ids
    elif req.channel_id:
        target_channel_ids = [req.channel_id]
    elif req.channel_code and req.channel_code.lower() in ch_by_code:
        target_channel_ids = [ch_by_code[req.channel_code.lower()].id]
    else:
        target_channel_ids = [channels[0].id] if channels else [1]

    created_contents: list[MarketingContent] = []
    angles_used: set[str] = set()

    for ch_id in target_channel_ids:
        ch_obj = ch_map.get(ch_id)
        ch_code = ch_obj.code if ch_obj else (req.channel_code or "facebook")
        if req.variants:
            variants_list = req.variants
        else:
            matrix = ai_service.generate_angle_hook_matrix(
                db=db,
                user_id=current_user.id,
                campaign_id=campaign.id,
                context={
                    "workspace_id": campaign.workspace_id,
                    "campaign_name": campaign.name,
                    "objective": campaign.objective,
                    "funnel_stage": getattr(campaign, "funnel_stage", "BoFU"),
                    "audience": campaign.audience,
                    "product_name": product.name if product else campaign.name,
                    "product_usp": product.usp if product else (campaign.key_message or "Giải pháp đột phá"),
                    "channel": ch_code,
                    "angles": req.angles or ["PAIN_POINT", "SOCIAL_PROOF", "OFFER_FOMO"],
                    "hooks_per_angle": req.hooks_per_angle,
                    "provider": req.preferred_provider,
                    "model": req.preferred_model,
                },
            )
            variants_list = matrix.get("variants", [])

        for v in variants_list:
            ang = str(v.get("angle") or v.get("angle_code") or v.get("creative_angle") or "PAIN_POINT")
            h_type = str(v.get("hook_type") or v.get("hook_variant") or "Hook_A")
            h_3s = str(v.get("hook_3s") or v.get("hook_text") or "")
            raw_title = str(v.get("title") or h_3s or f"[{ang}] Biến thể A/B")[:255]
            raw_body = str(v.get("body") or h_3s)
            raw_cta = str(v.get("cta") or "Tìm hiểu thêm")[:255]
            utm_p = str(v.get("utm_params") or f"?utm_source={ch_code}&utm_medium=paid_social&utm_campaign={campaign.campaign_code or campaign.id}&utm_content={ang.lower()}")
            angles_used.add(ang)
            mc = MarketingContent(
                workspace_id=campaign.workspace_id,
                campaign_id=campaign.id,
                channel_id=ch_id,
                created_by=current_user.id,
                title=raw_title,
                body=raw_body,
                cta=raw_cta,
                status=req.target_status,
                version_no=1,
                creative_angle=ang,
                hook_variant=h_type,
                utm_params=utm_p,
                ai_metadata_json=json.dumps({
                    "ab_hypothesis": v.get("ab_hypothesis", ""),
                    "predicted_ctr_pct": v.get("predicted_ctr_pct", 2.5),
                    "predicted_cvr_pct": v.get("predicted_cvr_pct", 3.0),
                    "compliance_score": v.get("compliance_score", 96),
                }, ensure_ascii=False),
                source_ids_json='["angle_matrix"]',
                warnings_json="[]",
            )
            db.add(mc)
            created_contents.append(mc)

    db.commit()
    for mc in created_contents:
        db.refresh(mc)

    return SeedAngleMatrixResponse(
        status="ok",
        campaign_id=campaign.id,
        created_count=len(created_contents),
        content_ids=[mc.id for mc in created_contents],
        contents=[ContentResponse.model_validate(mc) for mc in created_contents],
        matrix_summary={
            "channels_seeded": len(target_channel_ids),
            "angles_used": sorted(list(angles_used)),
            "hooks_per_angle": req.hooks_per_angle,
        },
    )


@router.get("/{campaign_id}", response_model=CampaignResponse)
def get_campaign(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chiến dịch không tồn tại")
    check_campaign_access(campaign, current_user, db)
    return _with_progress(db, campaign)


@router.put("/{campaign_id}", response_model=CampaignResponse)
def update_campaign(
    campaign_id: int,
    req: CampaignUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chiến dịch không tồn tại")
    check_campaign_access(campaign, current_user, db)

    update_data = req.model_dump(exclude_unset=True)
    if "tags" in update_data:
        tags_val = update_data.pop("tags")
        if tags_val is not None:
            update_data["tags_json"] = json.dumps([str(t).strip() for t in tags_val if str(t).strip()], ensure_ascii=False)

    allowed_fields = {
        "name", "objective", "audience", "start_date", "end_date", "budget", "status",
        "key_message", "primary_cta", "target_kpi_name", "target_kpi_value",
        "campaign_code", "funnel_stage", "daily_budget_cap", "tags_json",
    }
    for field, value in update_data.items():
        if field not in allowed_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Không được cập nhật trường '{field}'.",
            )

    if ("status" in update_data or "budget" in update_data):
        privileged = current_user.role in ("ADMIN", "MANAGER", "AGENCY_MANAGER")
        is_owner = campaign.owner_id == current_user.id
        if not (privileged or is_owner):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Chỉ chủ sở hữu hoặc quản lý mới được thay đổi trạng thái/ngân sách chiến dịch",
            )

    if "status" in update_data:
        update_data["status"] = campaign_lifecycle.assert_transition(
            campaign.status, update_data["status"]
        )

    for field, value in update_data.items():
        setattr(campaign, field, value)

    if campaign.end_date < campaign.start_date:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Ngày kết thúc không được trước ngày bắt đầu")

    db.commit()
    db.refresh(campaign)
    return _with_progress(db, campaign)


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_campaign(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    user_payload=Depends(RoleChecker(allowed_roles=["MANAGER", "AGENCY_MANAGER"])),
    db: Session = Depends(get_db)
):
    """Soft-delete: chuyển sang ARCHIVED, giữ nguyên metrics/tasks/history."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chiến dịch không tồn tại")

    check_campaign_access(campaign, current_user, db)

    if campaign.status != "ARCHIVED":
        campaign.status = "ARCHIVED"
        db.commit()
    return None


@router.get("/{campaign_id}/contents", response_model=Page[ContentResponse])
def get_campaign_contents(
    campaign_id: int,
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    sort: str = Query("newest", description=_SORT_DESCRIPTION),
    pagination: PageParams = Depends(page_params),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Nội dung của một chiến dịch, có lọc + phân trang."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chiến dịch không tồn tại")
    check_campaign_access(campaign, current_user, db)

    query = db.query(MarketingContent).filter(MarketingContent.campaign_id == campaign_id)

    if current_user.role != "ADMIN":
        query = _apply_tenant_scope(query, MarketingContent, current_user, db, MarketingContent.created_by)

    if current_user.role not in ("ADMIN", "MANAGER", "AGENCY_MANAGER", "CLIENT_APPROVER"):
        if campaign.owner_id != current_user.id:
            query = query.filter(MarketingContent.created_by == current_user.id)

    if status_filter:
        query = query.filter(MarketingContent.status == status_filter)
    if search:
        search_fmt = f"%{search}%"
        query = query.filter(
            (MarketingContent.title.ilike(search_fmt)) |
            (MarketingContent.body.ilike(search_fmt))
        )

    sort_key = (sort or "newest").strip().lower()
    order_by = {
        "newest": (MarketingContent.created_at.desc(), MarketingContent.id.desc()),
        "oldest": (MarketingContent.created_at.asc(), MarketingContent.id.asc()),
        "name_asc": (MarketingContent.title.asc(), MarketingContent.id.asc()),
        "name_desc": (MarketingContent.title.desc(), MarketingContent.id.desc()),
        "status_asc": (MarketingContent.status.asc(), MarketingContent.id.desc()),
        "updated_desc": (MarketingContent.updated_at.desc(), MarketingContent.id.desc()),
    }.get(sort_key)
    if order_by is None:
        raise HTTPException(
            status_code=422,
            detail=f"Giá trị sort không hợp lệ. Chỉ nhận: {', '.join(_CONTENT_SORT_KEYS)}.",
        )

    return paginate_query(
        query.order_by(*order_by),
        pagination,
        serializer=lambda c: ContentResponse.model_validate(c),
    )


# --- BUDGET ALLOCATION ENDPOINTS ---

@router.get("/{campaign_id}/budget-allocations", response_model=List[BudgetAllocationResponse])
def get_campaign_budget_allocations(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lấy danh sách phân bổ ngân sách theo kênh của chiến dịch."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chiến dịch không tồn tại")
    check_campaign_access(campaign, current_user, db)

    allocations = db.query(CampaignBudgetAllocation).filter(
        CampaignBudgetAllocation.campaign_id == campaign_id
    ).all()
    return allocations


@router.put("/{campaign_id}/budget-allocations", response_model=List[BudgetAllocationResponse])
def update_campaign_budget_allocations(
    campaign_id: int,
    allocations_in: List[BudgetAllocationCreate],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cập nhật phân bổ ngân sách theo kênh (Owner, Manager, Admin)."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chiến dịch không tồn tại")
    check_campaign_access(campaign, current_user, db)

    if current_user.role not in ("ADMIN", "MANAGER", "AGENCY_MANAGER") and campaign.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Không có quyền phân bổ ngân sách")

    channel_ids = [a.channel_id for a in allocations_in]
    if channel_ids:
        existing_channels = db.query(MarketingChannel.id).filter(MarketingChannel.id.in_(channel_ids)).all()
        existing_ids = {c[0] for c in existing_channels}
        missing = set(channel_ids) - existing_ids
        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Các kênh tiếp thị không tồn tại: {list(missing)}"
            )

    if len(set(channel_ids)) != len(channel_ids):
        dupes = sorted({cid for cid in channel_ids if channel_ids.count(cid) > 1})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Kênh bị phân bổ trùng lặp: {dupes}",
        )

    total_planned = sum(float(a.planned_amount) for a in allocations_in)
    total_budget = float(campaign.budget or 0)
    if total_planned > total_budget + 1e-6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Tổng phân bổ {total_planned:,.0f} vượt ngân sách "
                f"{total_budget:,.0f}. Hãy giảm phân bổ hoặc tăng ngân sách chiến dịch."
            ),
        )

    db.query(CampaignBudgetAllocation).filter(CampaignBudgetAllocation.campaign_id == campaign_id).delete()

    created_allocations = []
    for a in allocations_in:
        item = CampaignBudgetAllocation(
            campaign_id=campaign_id,
            channel_id=a.channel_id,
            planned_amount=a.planned_amount
        )
        db.add(item)
        created_allocations.append(item)

    db.commit()
    for item in created_allocations:
        db.refresh(item)

    return created_allocations


@router.get("/{campaign_id}/budget-summary", response_model=BudgetSummaryResponse)
def get_campaign_budget_summary(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Tổng quan ngân sách: phân bổ kế hoạch vs chi phí thực tế (từ CampaignMetric)."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chiến dịch không tồn tại")
    check_campaign_access(campaign, current_user, db)

    allocations = db.query(CampaignBudgetAllocation).filter(
        CampaignBudgetAllocation.campaign_id == campaign_id
    ).all()

    spent_rows = (
        db.query(
            CampaignMetric.channel_id,
            CampaignMetric.cost,
        )
        .filter(CampaignMetric.campaign_id == campaign_id)
        .all()
    )
    spent_by_channel: dict = {}
    for ch_id, cost in spent_rows:
        spent_by_channel[ch_id] = spent_by_channel.get(ch_id, 0.0) + float(cost or 0.0)

    channel_names = {
        c.id: c.name
        for c in db.query(MarketingChannel).filter(
            MarketingChannel.id.in_(
                {a.channel_id for a in allocations} | set(spent_by_channel)
            )
        ).all()
    } if (allocations or spent_by_channel) else {}

    all_channel_ids = sorted({a.channel_id for a in allocations} | set(spent_by_channel))
    planned_by_channel = {a.channel_id: float(a.planned_amount or 0.0) for a in allocations}

    channels = [
        BudgetChannelSummary(
            channel_id=ch_id,
            channel_name=channel_names.get(ch_id),
            planned_amount=planned_by_channel.get(ch_id, 0.0),
            spent_amount=spent_by_channel.get(ch_id, 0.0),
        )
        for ch_id in all_channel_ids
    ]

    total_budget = float(campaign.budget or 0.0)
    total_allocated = sum(c.planned_amount for c in channels)
    total_spent = sum(c.spent_amount for c in channels)

    return BudgetSummaryResponse(
        campaign_id=campaign_id,
        total_budget=round(total_budget, 2),
        total_allocated=round(total_allocated, 2),
        total_spent=round(total_spent, 2),
        unallocated_amount=round(max(0.0, total_budget - total_allocated), 2),
        remaining_amount=round(total_budget - total_spent, 2),
        allocated_pct=round(100.0 * total_allocated / total_budget, 2) if total_budget > 0 else 0.0,
        spent_pct=round(100.0 * total_spent / total_budget, 2) if total_budget > 0 else 0.0,
        channels=channels,
    )


# --- KPI TARGETS ENDPOINTS ---

@router.get("/{campaign_id}/kpi-targets", response_model=List[KPITargetResponse])
def get_campaign_kpi_targets(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lấy danh sách mục tiêu KPI của chiến dịch."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chiến dịch không tồn tại")
    check_campaign_access(campaign, current_user, db)

    targets = db.query(CampaignKPITarget).filter(
        CampaignKPITarget.campaign_id == campaign_id
    ).all()
    return targets


@router.put("/{campaign_id}/kpi-targets", response_model=List[KPITargetResponse])
def update_campaign_kpi_targets(
    campaign_id: int,
    targets_in: List[KPITargetCreate],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cập nhật danh sách mục tiêu KPI của chiến dịch."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chiến dịch không tồn tại")
    check_campaign_access(campaign, current_user, db)

    if current_user.role not in ("ADMIN", "MANAGER", "AGENCY_MANAGER") and campaign.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Không có quyền cập nhật KPI mục tiêu")

    names = [t.metric_name.strip().lower() for t in targets_in]
    if len(set(names)) != len(names):
        dupes = sorted({n for n in names if names.count(n) > 1})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Chỉ tiêu KPI trùng lặp: {dupes}",
        )

    db.query(CampaignKPITarget).filter(CampaignKPITarget.campaign_id == campaign_id).delete()

    created_targets = []
    for t in targets_in:
        item = CampaignKPITarget(
            campaign_id=campaign_id,
            metric_name=t.metric_name,
            target_value=t.target_value,
            unit=t.unit
        )
        db.add(item)
        created_targets.append(item)

    db.commit()
    for item in created_targets:
        db.refresh(item)

    return created_targets


def _kpi_actual_value(metric_name: str, agg: dict) -> Optional[float]:
    """Map tên chỉ tiêu KPI → giá trị thực tế từ tổng hợp CampaignMetric."""
    name = metric_name.strip().lower()
    views = agg["views"]
    clicks = agg["clicks"]
    conv = agg["conversions"]
    cost = agg["cost"]
    rev = agg["revenue"]

    if name in ("ctr",):
        return round(100.0 * clicks / views, 2) if views > 0 else None
    if name in ("cvr", "conversion_rate"):
        return round(100.0 * conv / clicks, 2) if clicks > 0 else None
    if name in ("cpc",):
        return round(cost / clicks, 2) if clicks > 0 else None
    if name in ("cpa", "cpl", "cost_per_lead"):
        return round(cost / conv, 2) if conv > 0 else None
    if name in ("roas",):
        return round(rev / cost, 2) if cost > 0 else None
    if name in ("roi",):
        return round(100.0 * (rev - cost) / cost, 2) if cost > 0 else None
    if name in ("revenue", "doanh thu"):
        return round(rev, 2)
    if name in ("cost", "spend", "chi phí"):
        return round(cost, 2)
    if name in ("conversions", "leads", "conversion"):
        return float(conv)
    if name in ("clicks",):
        return float(clicks)
    if name in ("views", "impressions", "impression"):
        return float(views)
    return None


@router.get("/{campaign_id}/kpi-progress", response_model=KpiProgressResponse)
def get_campaign_kpi_progress(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """So sánh KPI mục tiêu với thực tế đã đo (SUM CampaignMetric)."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chiến dịch không tồn tại")
    check_campaign_access(campaign, current_user, db)

    targets = db.query(CampaignKPITarget).filter(
        CampaignKPITarget.campaign_id == campaign_id
    ).all()

    from sqlalchemy import func as sa_func
    row = db.query(
        sa_func.coalesce(sa_func.sum(CampaignMetric.views), 0),
        sa_func.coalesce(sa_func.sum(CampaignMetric.clicks), 0),
        sa_func.coalesce(sa_func.sum(CampaignMetric.conversions), 0),
        sa_func.coalesce(sa_func.sum(CampaignMetric.cost), 0),
        sa_func.coalesce(sa_func.sum(CampaignMetric.revenue), 0),
    ).filter(CampaignMetric.campaign_id == campaign_id).one()
    agg = {
        "views": int(row[0]),
        "clicks": int(row[1]),
        "conversions": int(row[2]),
        "cost": float(row[3]),
        "revenue": float(row[4]),
    }

    out_targets: List[KpiProgressTarget] = []
    achievable: List[float] = []
    for t in targets:
        actual = _kpi_actual_value(t.metric_name, agg)
        target_val = float(t.target_value)
        if actual is None or target_val <= 0:
            achieved = None
            measurable = False
        else:
            achieved = round(100.0 * actual / target_val, 2)
            measurable = True
            achievable.append(achieved)
        out_targets.append(KpiProgressTarget(
            target_id=t.id,
            metric_name=t.metric_name,
            unit=t.unit,
            target_value=target_val,
            actual_value=actual,
            achieved_pct=achieved,
            measurable=measurable,
        ))

    return KpiProgressResponse(
        campaign_id=campaign_id,
        targets=out_targets,
        overall_achieved_pct=round(sum(achievable) / len(achievable), 2) if achievable else None,
        measurable_count=len(achievable),
        total_count=len(out_targets),
    )


def _plan_apply_state_response(campaign_id: int, db: Session, deduplicated: bool) -> PlanApplyResponse:
    """Trạng thái hiện tại của chiến dịch, dùng cho nhánh dedup (không ghi gì)."""
    allocations = (
        db.query(CampaignBudgetAllocation)
        .filter(CampaignBudgetAllocation.campaign_id == campaign_id)
        .order_by(CampaignBudgetAllocation.id)
        .all()
    )
    kpis = (
        db.query(CampaignKPITarget)
        .filter(CampaignKPITarget.campaign_id == campaign_id)
        .order_by(CampaignKPITarget.id)
        .all()
    )
    return PlanApplyResponse(
        campaign_id=campaign_id,
        deduplicated=deduplicated,
        budget_allocations=allocations,
        kpi_targets=kpis,
        tasks_created=0,
        tasks_skipped=0,
    )


@router.post("/{campaign_id}/plan/apply", response_model=PlanApplyResponse)
def apply_campaign_plan(
    campaign_id: int,
    plan_in: PlanApplyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Áp dụng kế hoạch AI (từ POST /ai/plan hoặc POST /ai/jobs kind=plan) vào chiến dịch."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chiến dịch không tồn tại")
    check_campaign_access(campaign, current_user, db)

    if current_user.role not in ("ADMIN", "MANAGER", "AGENCY_MANAGER") and campaign.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Không có quyền áp dụng kế hoạch cho chiến dịch")

    if campaign.workspace_id is None and plan_in.tasks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chiến dịch chưa thuộc workspace nào; không thể tạo task từ kế hoạch.",
        )

    normalized_codes = [b.channel_code.strip().lower() for b in plan_in.budget_split]
    if len(set(normalized_codes)) != len(normalized_codes):
        dupes = sorted({c for c in normalized_codes if normalized_codes.count(c) > 1})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Kênh bị phân bổ trặp lặp: {dupes}",
        )
    channels = db.query(MarketingChannel).filter(
        MarketingChannel.code.in_(normalized_codes)
    ).all()
    channel_by_code = {c.code: c for c in channels if c.status == "ACTIVE"}
    missing = [c for c in normalized_codes if c not in channel_by_code]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Các kênh tiếp thị không tồn tại hoặc không hoạt động: {missing}",
        )

    total_planned = sum(float(b.planned_amount) for b in plan_in.budget_split)
    total_budget = float(campaign.budget or 0)
    if total_planned > total_budget + 1e-6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Tổng phân bổ {total_planned:,.0f} vượt ngân sách "
                f"{total_budget:,.0f}. Hãy giảm phân bổ hoặc tăng ngân sách chiến dịch."
            ),
        )

    kpi_names = [t.metric_name.strip().lower() for t in plan_in.kpi_targets]
    if len(set(kpi_names)) != len(kpi_names):
        dupes = sorted({n for n in kpi_names if kpi_names.count(n) > 1})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Chỉ tiêu KPI trùng lặp: {dupes}",
        )

    start_d = end_d = None
    try:
        start_d = datetime.strptime(campaign.start_date, "%Y-%m-%d").date()
        end_d = datetime.strptime(campaign.end_date, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        start_d = end_d = None
    for t in plan_in.tasks:
        if start_d is not None and end_d is not None:
            offset = t.due_offset_days
            if offset < 0 or start_d + timedelta(days=offset) > end_d:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Công việc “{t.title}” có ngày hoàn thành ngoài khoảng "
                        f"chiến dịch ({campaign.start_date} -> {campaign.end_date})."
                    ),
                )

    canonical = json.dumps(
        plan_in.model_dump(exclude={"idempotency_key"}),
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    plan_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    existing_app = (
        db.query(CampaignPlanApplication)
        .filter(
            CampaignPlanApplication.campaign_id == campaign_id,
            CampaignPlanApplication.idempotency_key == plan_in.idempotency_key,
        )
        .first()
    )
    if existing_app is not None:
        if existing_app.plan_hash == plan_hash:
            return _plan_apply_state_response(campaign_id, db, deduplicated=True)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Khóa idempotency đã được dùng cho một kế hoạch khác của chiến dịch này. Dùng khóa mới cho kế hoạch mới.",
        )

    try:
        db.add(CampaignPlanApplication(
            campaign_id=campaign_id,
            idempotency_key=plan_in.idempotency_key,
            plan_hash=plan_hash,
            plan_json=canonical,
            applied_by=current_user.id,
        ))

        db.query(CampaignBudgetAllocation).filter(
            CampaignBudgetAllocation.campaign_id == campaign_id
        ).delete(synchronize_session=False)
        for b in plan_in.budget_split:
            db.add(CampaignBudgetAllocation(
                campaign_id=campaign_id,
                channel_id=channel_by_code[b.channel_code.strip().lower()].id,
                planned_amount=b.planned_amount,
                is_ai_estimate=True,
            ))

        if plan_in.kpi_targets:
            db.query(CampaignKPITarget).filter(
                CampaignKPITarget.campaign_id == campaign_id
            ).delete(synchronize_session=False)
            for t in plan_in.kpi_targets:
                db.add(CampaignKPITarget(
                    campaign_id=campaign_id,
                    metric_name=t.metric_name,
                    target_value=t.target_value,
                    unit=t.unit,
                    is_ai_estimate=True,
                ))

        existing_titles = {
            (row[0] or "").strip().lower()
            for row in db.query(Task.title).filter(Task.campaign_id == campaign_id).all()
        }
        tasks_created = 0
        tasks_skipped = 0
        for t in plan_in.tasks:
            key = t.title.strip().lower()
            if key in existing_titles:
                tasks_skipped += 1
                continue
            existing_titles.add(key)
            due_date = None
            if start_d is not None:
                due_date = (start_d + timedelta(days=t.due_offset_days)).strftime("%Y-%m-%d")
            db.add(Task(
                campaign_id=campaign_id,
                workspace_id=campaign.workspace_id,
                title=t.title.strip(),
                description=t.description,
                task_type=t.task_type,
                priority=t.priority,
                status="TODO",
                creator_id=current_user.id,
                due_date=due_date,
            ))
            tasks_created += 1

        db.commit()
    except IntegrityError:
        db.rollback()
        existing_app = (
            db.query(CampaignPlanApplication)
            .filter(
                CampaignPlanApplication.campaign_id == campaign_id,
                CampaignPlanApplication.idempotency_key == plan_in.idempotency_key,
            )
            .first()
        )
        if existing_app is not None:
            if existing_app.plan_hash == plan_hash:
                return _plan_apply_state_response(campaign_id, db, deduplicated=True)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Khóa idempotency đã được dùng cho một kế hoạch khác của chiến dịch này. Dùng khóa mới cho kế hoạch mới.",
            )
        raise

    state = _plan_apply_state_response(campaign_id, db, deduplicated=False)
    state.tasks_created = tasks_created
    state.tasks_skipped = tasks_skipped
    return state
