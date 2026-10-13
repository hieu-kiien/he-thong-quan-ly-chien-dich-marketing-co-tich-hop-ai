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
from app.schemas.schemas import CampaignCreate, CampaignUpdate, CampaignResponse, ContentResponse, BudgetAllocationCreate, BudgetAllocationResponse, BudgetSummaryResponse, BudgetChannelSummary, KPITargetCreate, KPITargetResponse, KpiProgressResponse, KpiProgressTarget, PlanApplyRequest, PlanApplyResponse


router = APIRouter(prefix="/campaigns", tags=["Quản lý Chiến dịch"])

# Khoá sắp xếp được phép (allowlist). `sort` là dữ liệu do client gửi nên không
# bao giờ nối thẳng vào ORDER BY — chỉ map sang cột đã biết ở đây.
_CAMPAIGN_SORT_KEYS = (
    "newest", "oldest", "name_asc", "name_desc",
    "budget_asc", "budget_desc", "start_date",
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


def _accessible_workspace_ids(user: User, db: Session) -> List[int]:
    """Danh sách workspace_id mà user thực sự có quyền: workspace họ làm chủ
    (Workspace.owner_id) hoặc họ là thành viên (WorkspaceMember).

    Dùng chung cho các endpoint list (campaigns/contents) để vai trò MANAGER /
    AGENCY_MANAGER KHÔNG còn bỏ qua mọi lọc bản ghi và nhìn thấy dữ liệu của
    tenant khác. Chỉ ADMIN mới được phạm vi toàn cục.
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
    """Giới hạn truy vấn theo tenant thực sự của user (fail-closed).

    - Bản ghi có workspace_id: chỉ thấy nếu workspace đó user là owner/member.
    - Bản ghi legacy workspace_id IS NULL: chỉ thấy nếu chính user là người tạo
      (null_owner_column), tránh mất dữ liệu của chính mình trong lúc dữ liệu
      legacy chưa được migration gán workspace.
    """
    ws_ids = _accessible_workspace_ids(user, db)
    in_ws = model.workspace_id.in_(ws_ids) if ws_ids else false()
    return query.filter(
        or_(
            in_ws,
            and_(model.workspace_id.is_(None), null_owner_column == user.id),
        )
    )

def check_campaign_access(campaign: Campaign, user: User, db: Session):
    """Xác thực phân quyền mức bản ghi và cách ly đa người thuê (Tenant Isolation):
    - User ADMIN có quyền truy cập tất cả tài nguyên.
    - User MANAGER / AGENCY_MANAGER:
      + Phải là owner hoặc member của workspace chứa campaign.
    - User MARKETER / các role khác:
      + Phải là owner hoặc member của workspace chứa campaign.
      + Đồng thời user chỉ được thao tác trên tài nguyên mà họ sở hữu (owner_id) HOẶC là thành viên chiến dịch (CampaignMember).
    """
    if user.role == "ADMIN":
        return

    # Kiểm tra Tenant Isolation đối với các workspace cụ thể
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

    # Fail-closed: campaign không thuộc workspace nào thì không có ranh giới tenant để tin cậy,
    # mọi role (kể cả MANAGER/AGENCY_MANAGER) đều phải là owner hoặc CampaignMember.
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
    """Chốt workspace hiện hành của request, theo thứ tự ưu tiên:

    1. Query param `workspace_id` (gọi API trực tiếp, rõ ý định nhất).
    2. Header `X-Workspace-Id` — đây là header mà frontend gửi tự động từ
       workspace người dùng đang chọn trên `WorkspaceSwitcher` (xem
       interceptor trong frontend/src/services/api.ts).
    3. `None` = không lọc theo workspace cụ thể (endpoint tự áp tenant scope
       rộng hơn, ví dụ dashboard tổng hợp).

    Vì sao cần hàm dùng chung: trước đây header chỉ được `POST /campaigns` đọc.
    Các endpoint LIST (`GET /campaigns`, `GET /contents`, ...) bỏ qua nó, nên khi
    người dùng đổi workspace trên UI, màn hình vẫn hiện dữ liệu của workspace đầu
    tiên — bộ chuyển workspace trông như hoạt động nhưng không có tác dụng gì.
    """
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
    """Dependency trả về workspace hiện hành, hoặc None nếu không yêu cầu lọc.

    Dùng cho endpoint list. Giá trị trả về đã được kiểm tra quyền: người dùng
    chỉ được chỉ định workspace mà mình là owner hoặc thành viên (ADMIN thì tự do).
    Endpoint vẫn tự áp `_apply_tenant_scope` phía sau, nên thiếu hoặc sai header
    cũng không thể vượt qua ranh giới tenant.
    """
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


def _with_progress(db: Session, campaign: Campaign) -> CampaignResponse:
    """Kèm progress_pct tính từ task; None khi chưa có task."""
    resp = CampaignResponse.model_validate(campaign)
    counts = db.query(Task.status).filter(Task.campaign_id == campaign.id).all()
    done = sum(1 for (s,) in counts if (s or "").upper() in ("DONE", "COMPLETED"))
    resp.progress_pct = campaign_lifecycle.compute_progress_pct(done, len(counts))
    return resp


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


def _serialize_campaign_list(
    db: Session, campaigns: list[Campaign]
) -> list[CampaignResponse]:
    progress = _bulk_task_progress(db, [c.id for c in campaigns])
    result: list[CampaignResponse] = []
    for c in campaigns:
        resp = CampaignResponse.model_validate(c)
        counts = progress.get(c.id, {"done": 0, "total": 0})
        resp.progress_pct = campaign_lifecycle.compute_progress_pct(
            counts["done"], counts["total"]
        )
        result.append(resp)
    return result


@router.get("", response_model=Page[CampaignResponse])
def get_campaigns(
    workspace_id: Optional[int] = Depends(get_workspace_filter),
    status_filter: Optional[str] = Query(None, alias="status"),
    channel_id: Optional[int] = Query(None, alias="channel_id"),
    start_date: Optional[str] = Query(None, alias="start_date"),
    end_date: Optional[str] = Query(None, alias="end_date"),
    search: Optional[str] = Query(None),
    objective: Optional[str] = Query(
        None, description="Lọc theo mục tiêu chiến dịch (khớp chuỗi con)"
    ),
    sort: str = Query("newest", description=_SORT_DESCRIPTION),
    pagination: PageParams = Depends(page_params),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Campaign)

    # Soft-delete: ẩn ARCHIVED khỏi list mặc định. Client lọc status=ARCHIVED
    # khi cần xem thùng rác thì giữ nguyên (không áp hidden filter).
    want_archived = status_filter is not None and campaign_lifecycle.normalize_status(status_filter) == "ARCHIVED"
    if not want_archived:
        query = query.filter(
            Campaign.status.notin_(list(campaign_lifecycle.HIDDEN_FROM_DEFAULT_LIST))
        )

    # Phân quyền record-level: Marketer chỉ xem được chiến dịch của mình hoặc mình là thành viên
    if current_user.role not in ("ADMIN", "MANAGER", "AGENCY_MANAGER"):
        member_campaign_ids = db.query(CampaignMember.campaign_id).filter(CampaignMember.user_id == current_user.id)
        query = query.filter(
            (Campaign.owner_id == current_user.id) |
            (Campaign.id.in_(member_campaign_ids))
        )

    # Tenant scope fail-closed: chỉ MANAGER/AGENCY_MANAGER có filter workspace_id
    # tường minh là chưa đủ — thiếu filter thì MỌI dòng (kể cả workspace_id NULL
    # hay workspace tenant khác) đều lọt vào trang trả về. `_apply_tenant_scope`
    # chốt lại tập được phép xem ở tầng query bất kể client có gửi filter hay không.
    if current_user.role != "ADMIN":
        query = _apply_tenant_scope(query, Campaign, current_user, db, Campaign.owner_id)

    # `workspace_id` tới đây đã được phân giải + kiểm tra quyền trong dependency
    # `get_workspace_filter` (đọc cả query param lẫn header X-Workspace-Id).
    if workspace_id is not None:
        query = query.filter(Campaign.workspace_id == workspace_id)
    if status_filter:
        query = query.filter(Campaign.status == status_filter)
    if start_date:
        query = query.filter(Campaign.start_date >= start_date)
    if end_date:
        query = query.filter(Campaign.end_date <= end_date)
    if channel_id:
        from app.models.entities import MarketingContent
        query = query.join(MarketingContent).filter(MarketingContent.channel_id == channel_id).distinct()
    if search:
        search_fmt = f"%{search}%"
        query = query.filter(
            (Campaign.name.ilike(search_fmt)) |
            (Campaign.objective.ilike(search_fmt)) |
            (Campaign.audience.ilike(search_fmt))
        )
    if objective:
        # Trước đây bộ lọc "mục tiêu" chỉ tồn tại ở client (so khớp chuỗi con với
        # `objective`). Đưa xuống đây để phân trang ở server cho đúng: nếu vẫn lọc
        # ở client, mỗi trang chỉ chứa phần đã lọc của riêng trang đó và `total`
        # của envelope sẽ mâu thuẫn với những gì người dùng thấy.
        query = query.filter(Campaign.objective.ilike(f"%{objective}%"))

    # Sắp xếp sau khi lọc, trước khi cắt trang. Mỗi nhánh đều kèm `Campaign.id`
    # làm khoá phá thế hoàn toàn: trang 2 không được trả lặp/mất dòng khi hai
    # chiến dịch trùng giá trị sắp xếp.
    sort_key = (sort or "newest").strip().lower()
    order_by = {
        "newest": (Campaign.created_at.desc(), Campaign.id.desc()),
        "oldest": (Campaign.created_at.asc(), Campaign.id.asc()),
        "name_asc": (Campaign.name.asc(), Campaign.id.asc()),
        "name_desc": (Campaign.name.desc(), Campaign.id.desc()),
        "budget_asc": (Campaign.budget.asc(), Campaign.id.asc()),
        "budget_desc": (Campaign.budget.desc(), Campaign.id.desc()),
        "start_date": (Campaign.start_date.desc(), Campaign.id.desc()),
    }.get(sort_key)
    if order_by is None:
        # Allowlist: khoá sắp xếp là dữ liệu do client gửi, không nối thẳng vào
        # ORDER BY. Sai thì trả 422 chứ không phải 500 do SQL.
        raise HTTPException(
            status_code=422,
            detail=f"Giá trị sort không hợp lệ. Chỉ nhận: {', '.join(_CAMPAIGN_SORT_KEYS)}.",
        )

    page = paginate_query(query.order_by(*order_by), pagination)
    # Bulk progress (không N+1): một query task cho cả trang.
    return Page.build(
        items=_serialize_campaign_list(db, page.items),
        total=page.total,
        page=page.page,
        page_size=page.page_size,
    )

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

    # Kiểm tra product_id tồn tại
    product = db.query(Product).filter(Product.id == req.product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sản phẩm không tồn tại")

    # Phân giải workspace_id nghiêm ngặt: X-Workspace-Id hoặc req.workspace_id hoặc membership
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
        # Nếu không truyền workspace_id hay header, tìm active workspace của user
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

    # Hạn mức sản phẩm: số chiến dịch của workspace này. Kiểm tra SAU khi đã
    # chốt được tenant và SAU khi đã xác thực quyền — nếu kiểm tra sớm hơn thì
    # một workspace khác trả lỗi 429 thay vì 403, tức lộ trạng thái hạn mức của
    # tenant mà người gọi không thuộc về.
    quota.enforce(db, quota.LIMIT_CAMPAIGNS, user=current_user, workspace_id=ws_id)

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
        status=campaign_lifecycle.assert_create_status(req.status),
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    # Gán người tạo làm OWNER trong campaign_members
    member = CampaignMember(campaign_id=campaign.id, user_id=user_id, member_role="OWNER")
    db.add(member)
    db.commit()

    return _with_progress(db, campaign)


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

    # Allowlist tường minh: chỉ cho sửa các trường nghiệp vụ, không cho set owner_id/workspace_id.
    update_data = req.model_dump(exclude_unset=True)
    allowed_fields = {
        "name", "objective", "audience", "start_date", "end_date", "budget", "status",
        "key_message", "primary_cta", "target_kpi_name", "target_kpi_value"
    }
    for field, value in update_data.items():
        if field not in allowed_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Không được cập nhật trường '{field}'.",
            )

    # Sửa `status` hoặc `budget` là hành động quản trị, không phải thao tác
    # nội dung. Trước đây endpoint này chỉ kiểm tra "có quyền đọc campaign" nên
    # CLIENT_APPROVER (và cả marketer không sở hữu) cũng đổi được trạng thái và
    # ngân sách — chính là đường để tăng ngân sách 20% bằng một cú bấm.
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

    # Validate lại ngày nếu có cập nhật
    if campaign.end_date < campaign.start_date:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Ngày kết thúc không được trước ngày bắt đầu")

    db.commit()
    db.refresh(campaign)
    return _with_progress(db, campaign)

@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_campaign(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    user_payload=Depends(RoleChecker(allowed_roles=["MANAGER", "AGENCY_MANAGER"])), # Chỉ quản lý/agency manager mới được xóa!
    db: Session = Depends(get_db)
):
    """Soft-delete: chuyển sang ARCHIVED, giữ nguyên metrics/tasks/history.

    Hard-delete cascade từng làm mất lịch sử KPI. ARCHIVED ẩn khỏi list mặc
    định; manager/ADMIN vẫn GET được theo id nếu cần đối soát.
    """
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chiến dịch không tồn tại")

    # Xác thực quyền truy cập đối tượng và cô lập Tenant Isolation
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
    """Nội dung của một chiến dịch, có lọc + phân trang.

    Quyền truy cập được chốt ở CẤP CHIẾN DỊCH trước (`check_campaign_access`) rồi
    mới cắt trang, nên phân trang không thể biến một lần gọi hợp lệ thành đường đọc
    chéo tenant: `offset` chỉ dịch vị trong tập đã lọc, không mở rộng tập đó.
    """
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chiến dịch không tồn tại")
    check_campaign_access(campaign, current_user, db)

    query = db.query(MarketingContent).filter(MarketingContent.campaign_id == campaign_id)

    # Tenant scope (fail-closed): check_campaign_access đã chặn ở cấp chiến dịch, nhưng
    # các dòng nội dung gắn nhầm workspace khác (legacy/sai dữ liệu) vẫn phải bị lọc.
    if current_user.role != "ADMIN":
        query = _apply_tenant_scope(query, MarketingContent, current_user, db, MarketingContent.created_by)

    # Record-level authorization cho Marketer
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

    # Chỉ owner hoặc manager/admin được phân bổ ngân sách
    if current_user.role not in ("ADMIN", "MANAGER", "AGENCY_MANAGER") and campaign.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Không có quyền phân bổ ngân sách")

    # Xác thực các kênh tiếp thị tồn tại
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

    # Mỗi kênh chỉ được phân bổ 1 lần (DB có unique constraint — bắt sớm để
    # trả 400 thay vì 500 IntegrityError).
    if len(set(channel_ids)) != len(channel_ids):
        dupes = sorted({cid for cid in channel_ids if channel_ids.count(cid) > 1})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Kênh bị phân bổ trùng lặp: {dupes}",
        )

    # Tổng phân bổ không được vượt ngân sách chiến dịch.
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

    # Xóa phân bổ cũ và tạo mới
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
    """Tổng quan ngân sách: phân bổ kế hoạch vs chi phí thực tế (từ CampaignMetric).

    Trước đây không có endpoint này; UI chỉ có planned và tự bịa phần "đã chi".
    """
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chiến dịch không tồn tại")
    check_campaign_access(campaign, current_user, db)

    allocations = db.query(CampaignBudgetAllocation).filter(
        CampaignBudgetAllocation.campaign_id == campaign_id
    ).all()

    # Chi phí thực tế theo kênh (SUM cost từ metrics đã ghi nhận).
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

    # Gộp: kênh có phân bổ hoặc có chi phí (kênh chỉ chi mà chưa phân bổ vẫn hiện).
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

    # metric_name unique theo DB (uq_campaign_metric_target) — bắt sớm để 400 thay vì 500.
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
    """Map tên chỉ tiêu KPI → giá trị thực tế từ tổng hợp CampaignMetric.

    Trả None khi không map được (metric lạ) → caller hiển thị "chưa đo lường".
    """
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
    """So sánh KPI mục tiêu với thực tế đã đo (SUM CampaignMetric).

    Trước đây UI chỉ có target hoặc chỉ có actual, không chỗ nào ghép cặp
    để biết "đạt bao nhiêu %".
    """
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
    """Áp dụng kế hoạch AI (từ POST /ai/plan hoặc POST /ai/jobs kind=plan) vào chiến dịch.

    BẢO MẬT TÍNH TOÁN TOÀN BỘ TRƯỚC, GHI SAU: toàn bộ payload (kênh resolve
    được, tổng phân bổ ≤ ngân sách, KPI không trùng, task nằm trong khoảng
    chiến dịch) được kiểm tra xong MỚI chạm vào CSDL — request lỗi không bao
    giờ để lại "nửa kế hoạch".

    Idempotency BẮT BUỘC: khoá (campaign_id, idempotency_key) là UNIQUE ở tầng
    CSDL nên double-click/retry không thể áp kế hoạch hai lần. Khoá lặp lại với
    CÙNG kế hoạch -> 200 deduplicated=True (không ghi gì); khoá lặp lại với kế
    hoạch KHÁC -> 409 (tái sử dụng khoá im lặng sẽ trả kết quả cũ mà người dùng
    không biết).
    """
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chiến dịch không tồn tại")
    check_campaign_access(campaign, current_user, db)

    # Chỉ owner hoặc manager/admin được áp kế hoạch (cùng ranh giới với phân bổ
    # ngân sách / KPI ở hai endpoint phía trên).
    if current_user.role not in ("ADMIN", "MANAGER", "AGENCY_MANAGER") and campaign.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Không có quyền áp dụng kế hoạch cho chiến dịch")

    # Task bắt buộc có workspace_id NOT NULL — fail-closed trước khi ghi gì.
    if campaign.workspace_id is None and plan_in.tasks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chiến dịch chưa thuộc workspace nào; không thể tạo task từ kế hoạch.",
        )

    # --- Validate 1: kênh — chuẩn hoá code (lower/trim), không trùng, phải tồn tại & ACTIVE.
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

    # --- Validate 2: tổng phân bổ không vượt ngân sách (cùng ngưỡng với PUT budget).
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

    # --- Validate 3: KPI không trùng metric_name (DB unique campaign_id+metric_name).
    kpi_names = [t.metric_name.strip().lower() for t in plan_in.kpi_targets]
    if len(set(kpi_names)) != len(kpi_names):
        dupes = sorted({n for n in kpi_names if kpi_names.count(n) > 1})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Chỉ tiêu KPI trùng lặp: {dupes}",
        )

    # --- Validate 4: task nằm trong khoảng thời gian chiến dịch.
    start_d = end_d = None
    try:
        start_d = datetime.strptime(campaign.start_date, "%Y-%m-%d").date()
        end_d = datetime.strptime(campaign.end_date, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        start_d = end_d = None  # dữ liệu ngày lạ -> bỏ qua kiểm tra khoảng, due_date=None
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

    # --- Idempotency: hash CỦA KẾ HOẠCH (không gồm khoá) — khoá giống + kế hoạch
    # giống -> dedup; khoá giống + kế hoạch khác -> 409.
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

    # --- Ghi (1 transaction): nhật ký + phân bổ + KPI + task.
    try:
        db.add(CampaignPlanApplication(
            campaign_id=campaign_id,
            idempotency_key=plan_in.idempotency_key,
            plan_hash=plan_hash,
            plan_json=canonical,
            applied_by=current_user.id,
        ))

        # Thay TOÀN BỘ phân bổ (cùng semantics với PUT budget-allocations), dòng
        # mới luôn gắn is_ai_estimate=True để UI gắn nhãn "Ước tính AI".
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

        # KPI: chỉ thay khi kế hoạch ĐỀ XUẤT KPI (list rỗng = không đổi gì —
        # tránh xoá mất chỉ tiêu người dùng đã khai tay).
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

        # Task: bỏ qua title đã tồn tại (dedup theo campaign) thay vì tạo trùng.
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
        # Request song song thứ hai chèn khoá idempotency trước: rollback rồi
        # đọc lại trạng thái để trả dedup hoặc 409 đúng bản chất xung đột.
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



