from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import RoleChecker, get_current_user
from app.models.entities import Campaign, Product, User, CampaignMember
from app.schemas.schemas import CampaignCreate, CampaignUpdate, CampaignResponse

router = APIRouter(prefix="/campaigns", tags=["Quản lý Chiến dịch"])

@router.get("", response_model=List[CampaignResponse])
def get_campaigns(
    status_filter: Optional[str] = Query(None, alias="status"),
    channel_id: Optional[int] = Query(None, alias="channel_id"),
    start_date: Optional[str] = Query(None, alias="start_date"),
    end_date: Optional[str] = Query(None, alias="end_date"),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Campaign)
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
    db: Session = Depends(get_db)
):
    user_id = current_user.id

    # Kiểm tra product_id tồn tại
    product = db.query(Product).filter(Product.id == req.product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sản phẩm không tồn tại")

    campaign = Campaign(
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
    user_payload=Depends(RoleChecker(allowed_roles=["MANAGER"])), # Chỉ MANAGER mới được xóa!
    db: Session = Depends(get_db)
):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chiến dịch không tồn tại")
    
    db.delete(campaign)
    db.commit()
    return None
