from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.entities import MarketingSchedule, MarketingContent, User
from app.schemas.schemas import ScheduleCreate, ScheduleResponse

router = APIRouter(tags=["Quản lý Lịch đăng"])

@router.get("/schedules", response_model=List[ScheduleResponse])
def get_schedules(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    schedules = db.query(MarketingSchedule).order_by(MarketingSchedule.scheduled_at.asc()).all()
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
