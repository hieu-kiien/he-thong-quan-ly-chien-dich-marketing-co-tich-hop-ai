from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, Header
from sqlalchemy.orm import Session
from sqlalchemy import and_, false, or_
from app.core.database import get_db
from app.core.security import RoleChecker, get_current_user
from app.models.entities import Campaign, Product, User, CampaignMember, WorkspaceMember, Workspace, MarketingContent, CampaignBudgetAllocation, CampaignKPITarget, MarketingChannel
from app.schemas.schemas import CampaignCreate, CampaignUpdate, CampaignResponse, ContentResponse, BudgetAllocationCreate, BudgetAllocationResponse, KPITargetCreate, KPITargetResponse


router = APIRouter(prefix="/campaigns", tags=["Quản lý Chiến dịch"])


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

@router.get("", response_model=List[CampaignResponse])
def get_campaigns(
    workspace_id: Optional[int] = Query(None, alias="workspace_id"),
    status_filter: Optional[str] = Query(None, alias="status"),
    channel_id: Optional[int] = Query(None, alias="channel_id"),
    start_date: Optional[str] = Query(None, alias="start_date"),
    end_date: Optional[str] = Query(None, alias="end_date"),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Campaign)

    # Tenant scope (fail-closed): mọi role trừ ADMIN chỉ thấy campaign thuộc workspace
    # họ thực sự có quyền, cộng campaign legacy workspace_id IS NULL do chính họ sở hữu.
    if current_user.role != "ADMIN":
        query = _apply_tenant_scope(query, Campaign, current_user, db, Campaign.owner_id)

    # Phân quyền record-level: Marketer chỉ xem được chiến dịch của mình hoặc mình là thành viên
    if current_user.role not in ("ADMIN", "MANAGER", "AGENCY_MANAGER"):
        member_campaign_ids = db.query(CampaignMember.campaign_id).filter(CampaignMember.user_id == current_user.id)
        query = query.filter(
            (Campaign.owner_id == current_user.id) |
            (Campaign.id.in_(member_campaign_ids))
        )

    if workspace_id is not None:
        if current_user.role != "ADMIN":
            ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
            is_ws_owner = ws is not None and ws.owner_id == current_user.id
            is_ws_member = db.query(WorkspaceMember).filter(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == current_user.id
            ).first() is not None
            if not (is_ws_owner or is_ws_member):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to access campaigns in this workspace"
                )
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
    return [CampaignResponse.model_validate(c) for c in query.order_by(Campaign.id.desc()).all()]

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
        status="DRAFT"
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    # Gán người tạo làm OWNER trong campaign_members
    member = CampaignMember(campaign_id=campaign.id, user_id=user_id, member_role="OWNER")
    db.add(member)
    db.commit()

    return CampaignResponse.model_validate(campaign)


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
    return CampaignResponse.model_validate(campaign)

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
    allowed_fields = {"name", "objective", "audience", "start_date", "end_date", "budget", "status"}
    for field, value in update_data.items():
        if field not in allowed_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Không được cập nhật trường '{field}'.",
            )
        setattr(campaign, field, value)

    # Validate lại ngày nếu có cập nhật
    if campaign.end_date < campaign.start_date:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Ngày kết thúc không được trước ngày bắt đầu")

    db.commit()
    db.refresh(campaign)
    return CampaignResponse.model_validate(campaign)

@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_campaign(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    user_payload=Depends(RoleChecker(allowed_roles=["MANAGER", "AGENCY_MANAGER"])), # Chỉ quản lý/agency manager mới được xóa!
    db: Session = Depends(get_db)
):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chiến dịch không tồn tại")
    
    # Xác thực quyền truy cập đối tượng và cô lập Tenant Isolation
    check_campaign_access(campaign, current_user, db)
    
    db.delete(campaign)
    db.commit()
    return None

@router.get("/{campaign_id}/contents", response_model=List[ContentResponse])
def get_campaign_contents(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lấy danh sách toàn bộ nội dung của chiến dịch (phục vụ xem tổng quan và xuất file Excel/PDF)."""
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

    contents = query.order_by(MarketingContent.id.desc()).all()
    return [ContentResponse.model_validate(c) for c in contents]


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


