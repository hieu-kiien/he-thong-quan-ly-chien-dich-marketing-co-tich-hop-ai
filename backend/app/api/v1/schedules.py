import hmac
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Header
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.core.pagination import Page, PageParams, page_params, paginate_query
from app.core.security import get_current_user, security_bearer
from app.models.entities import MarketingSchedule, MarketingContent, User, Workspace, WorkspaceMember, Campaign, CampaignMember
from app.schemas.schemas import ScheduleCreate, ScheduleUpdate, ScheduleResponse
from app.api.v1.contents import check_content_access
from app.services.scheduler.worker import process_due_schedules

router = APIRouter(tags=["Quản lý Lịch đăng"])

@router.get("/schedules", response_model=Page[ScheduleResponse])
def get_schedules(
    workspace_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    content_id: Optional[int] = Query(None),
    pagination: PageParams = Depends(page_params),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Danh sách lịch đăng, có lọc + phân trang.

    Lưu ý thứ tự: mọi nhánh lọc tenant (theo `workspace_id`, theo vai trò) được áp
    TRƯỚC, `paginate_query` mới cắt trang — nên `total` và `offset` đều tính trên
    tập đã giới hạn tenant, không phải trên toàn bảng `marketing_schedules`.
    """
    query = db.query(MarketingSchedule).join(MarketingContent, MarketingSchedule.content_id == MarketingContent.id)

    if workspace_id is not None:
        if current_user.role != "ADMIN":
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
                (MarketingContent.workspace_id.in_(owned_workspaces.select()))
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

    if status_filter:
        query = query.filter(MarketingSchedule.status == status_filter)
    if content_id:
        query = query.filter(MarketingSchedule.content_id == content_id)

    return paginate_query(
        query.order_by(MarketingSchedule.scheduled_at.asc(), MarketingSchedule.id.asc()),
        pagination,
        serializer=lambda s: ScheduleResponse.model_validate(s),
    )

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

@router.delete("/schedules/{schedule_id}", response_model=ScheduleResponse)
@router.post("/schedules/{schedule_id}/cancel", response_model=ScheduleResponse)
def cancel_schedule(
    schedule_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Hủy lịch đăng bài viết. Trạng thái lịch đổi sang CANCELLED, nội dung bài viết vẫn giữ APPROVED."""
    schedule = db.query(MarketingSchedule).filter(MarketingSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lịch đăng không tồn tại")

    content = db.query(MarketingContent).filter(MarketingContent.id == schedule.content_id).first()
    if not content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nội dung liên kết không tồn tại")

    check_content_access(content, current_user, db)

    if schedule.status == "EXECUTED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể hủy lịch đăng đã thực thi (EXECUTED)."
        )

    schedule.status = "CANCELLED"
    db.commit()
    db.refresh(schedule)
    return ScheduleResponse.model_validate(schedule)

@router.put("/schedules/{schedule_id}", response_model=ScheduleResponse)
@router.patch("/schedules/{schedule_id}", response_model=ScheduleResponse)
def update_schedule(
    schedule_id: int,
    req: ScheduleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cập nhật thời gian hẹn đăng / múi giờ. Nếu lịch đã bị CANCELLED trước đó, đưa về PLANNED."""
    schedule = db.query(MarketingSchedule).filter(MarketingSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lịch đăng không tồn tại")

    content = db.query(MarketingContent).filter(MarketingContent.id == schedule.content_id).first()
    if not content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nội dung liên kết không tồn tại")

    check_content_access(content, current_user, db)

    if schedule.status == "EXECUTED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể cập nhật hoặc dời lịch đăng đã thực thi (EXECUTED)."
        )

    if content.status != "APPROVED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Chỉ có thể dời lịch cho nội dung đã được Quản lý phê duyệt (APPROVED). Trạng thái hiện tại: {content.status}"
        )

    if req.scheduled_at is not None:
        schedule.scheduled_at = req.scheduled_at
    if req.timezone is not None:
        schedule.timezone = req.timezone

    # Nếu lịch trước đó bị hủy (CANCELLED), kích hoạt lại thành PLANNED
    if schedule.status == "CANCELLED":
        schedule.status = "PLANNED"

    db.commit()
    db.refresh(schedule)
    return ScheduleResponse.model_validate(schedule)

@router.post("/schedules/trigger-worker")
def trigger_scheduler_worker(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    x_scheduler_secret: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Kích hoạt thủ công tiến trình Scheduler Worker kiểm tra và thực thi các lịch đến hạn.

    Đây là endpoint nội bộ. Ngoài việc cho phép quản lý bấm tay qua UI, nó phục vụ
    Durable Object trên Cloudflare: scheduler trong container bị tắt (vì ghi
    thẳng vào SQLite mà không qua HTTP sẽ không được snapshot lên R2), nên cron
    của Worker gọi endpoint này rồi mới snapshot.

    Hai đường xác thực được chấp nhận:
    1. Bearer token của người dùng đã đăng nhập (quản lý bấm tay từ UI).
    2. Header `X-Scheduler-Secret` khớp `SCHEDULER_SECRET` (dùng bởi Worker, vốn
       không mang token của người dùng).

    Nếu `SCHEDULER_SECRET` chưa được cấu hình thì đường (2) không hoạt động —
    lớp bảo vệ không bị nới lỏng chỉ vì thêm một caller.
    """
    expected_secret = str(getattr(settings, "SCHEDULER_SECRET", "") or "").strip()
    provided_secret = (x_scheduler_secret or "").strip()
    if expected_secret and provided_secret and hmac.compare_digest(provided_secret, expected_secret):
        pass  # đã xác thực bằng scheduler secret
    elif credentials:
        # Chuẩn hoá về cùng một kiểm tra với mọi endpoint khác.
        get_current_user(credentials, db)
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Yêu cầu Bearer token hoặc X-Scheduler-Secret hợp lệ",
            headers={"WWW-Authenticate": "Bearer"},
        )

    processed_ids = process_due_schedules(db)
    return {
        "message": "Scheduler worker executed successfully",
        "processed_schedule_ids": processed_ids,
        "count": len(processed_ids)
    }

