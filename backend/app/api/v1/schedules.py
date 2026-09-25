from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.entities import MarketingSchedule, MarketingContent, User, Workspace, WorkspaceMember, Campaign, CampaignMember
from app.schemas.schemas import ScheduleCreate, ScheduleResponse
from app.api.v1.contents import check_content_access

router = APIRouter(tags=["Quản lý Lịch đăng"])

@router.get("/schedules", response_model=List[ScheduleResponse])
def get_schedules(
    workspace_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(MarketingSchedule).join(MarketingContent, MarketingSchedule.content_id == MarketingContent.id)

    if workspace_id is not None:
        if current_user.role != "ADMIN" and workspace_id > 1:
            ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
            is_owner = ws is not None and ws.owner_id == current_user.id
            is_member = db.query(WorkspaceMember).filter(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == current_user.id
            ).first() is not None
            if not (is_owner or is_member):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to access schedules in this workspace"
                )
        query = query.filter(MarketingContent.workspace_id == workspace_id)
    else:
        if current_user.role == "ADMIN":
            pass
        elif current_user.role in ("MANAGER", "AGENCY_MANAGER"):
            user_workspaces = db.query(WorkspaceMember.workspace_id).filter(
                WorkspaceMember.user_id == current_user.id
            ).subquery()
            owned_workspaces = db.query(Workspace.id).filter(
                Workspace.owner_id == current_user.id
            ).subquery()
            query = query.filter(
                (MarketingContent.workspace_id.in_(user_workspaces.select())) |
                (MarketingContent.workspace_id.in_(owned_workspaces.select())) |
                (MarketingContent.workspace_id == 1) |
                (MarketingContent.workspace_id.is_(None))
            )
        else:
            allowed_campaigns = db.query(Campaign.id).filter(
                (Campaign.owner_id == current_user.id) |
                (Campaign.id.in_(
                    db.query(CampaignMember.campaign_id).filter(CampaignMember.user_id == current_user.id)
                ))
            ).subquery()
            query = query.filter(
                (MarketingSchedule.created_by == current_user.id) |
                (MarketingContent.created_by == current_user.id) |
                (MarketingContent.campaign_id.in_(allowed_campaigns.select()))
            )

    schedules = query.order_by(MarketingSchedule.scheduled_at.asc()).all()
    return [ScheduleResponse.model_validate(s) for s in schedules]

@router.post("/contents/{content_id}/schedule", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
def schedule_content(
    content_id: int,
    req: ScheduleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user_id = current_user.id

    content = db.query(MarketingContent).filter(MarketingContent.id == content_id).first()
    if not content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nội dung không tồn tại")

    # Record-level authorization check & Tenant Isolation
    check_content_access(content, current_user, db)

    # Quy tắc bắt buộc: Chỉ nội dung đã được Quản lý duyệt (APPROVED) mới được phép lập lịch đăng!
    if content.status != "APPROVED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Chỉ có thể lập lịch cho nội dung đã được Quản lý phê duyệt (APPROVED). Trạng thái hiện tại: {content.status}"
        )

    schedule = MarketingSchedule(
        content_id=content.id,
        scheduled_at=req.scheduled_at,
        timezone=req.timezone,
        status="PLANNED",
        created_by=user_id
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return ScheduleResponse.model_validate(schedule)
