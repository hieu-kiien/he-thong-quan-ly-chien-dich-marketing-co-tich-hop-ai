from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, and_
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.pagination import Page, PageParams, page_params, paginate_query
from app.core.security import get_current_user
from app.models.entities import Notification, User, Workspace, WorkspaceMember
from app.schemas.schemas import NotificationResponse, NotificationUpdate

router = APIRouter(prefix="/notifications", tags=["Thông báo (Notifications)"])


def _get_accessible_workspace_ids(user: User, db: Session) -> List[int]:
    """Lấy danh sách ID các workspace mà user có quyền truy cập (sở hữu hoặc thành viên)."""
    if user.role == "ADMIN":
        return [w[0] for w in db.query(Workspace.id).all()]
    owned = [w[0] for w in db.query(Workspace.id).filter(Workspace.owner_id == user.id).all()]
    memberships = [m[0] for m in db.query(WorkspaceMember.workspace_id).filter(WorkspaceMember.user_id == user.id).all()]
    return list(set(owned + memberships))


def create_notification(
    db: Session,
    user_id: Optional[int],
    workspace_id: int,
    title: str,
    message: str,
    notif_type: str = "info",
    target_tab: Optional[str] = None
) -> Notification:
    """Helper function to record a database notification and commit."""
    notif = Notification(
        user_id=user_id,
        workspace_id=workspace_id,
        title=title,
        message=message,
        type=notif_type,
        read=False,
        target_tab=target_tab
    )
    db.add(notif)
    try:
        db.commit()
        db.refresh(notif)
    except Exception:
        db.rollback()
        raise
    return notif


@router.get("", response_model=Page[NotificationResponse])
def get_notifications(
    workspace_id: Optional[int] = Query(None, description="Lọc theo ID workspace"),
    unread_only: bool = Query(False, description="Chỉ lấy thông báo chưa đọc"),
    pagination: PageParams = Depends(page_params),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Thông báo của người dùng + thông báo broadcast các workspace họ thuộc về.

    Trước đây dùng tham số `limit` (mặc định 50, trần 100) và trả mảng phẳng:
    client không biết còn bao nhiêu thông báo nên không dựng được nút "xem thêm".
    Nay dùng chung envelope `Page` của toàn hệ thống. `limit` bị gỡ — ai đó
    vẫn truyền `limit` sẽ bị FastAPI bỏ qua (không phải lỗi) và nhận trang đầu.
    """
    accessible_ws_ids = _get_accessible_workspace_ids(current_user, db)

    if workspace_id is not None:
        if current_user.role != "ADMIN" and workspace_id not in accessible_ws_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Không có quyền truy cập vào Workspace này"
            )

    query = db.query(Notification)

    # Filter by user or broadcast to accessible workspace
    if current_user.role == "ADMIN":
        user_cond = or_(
            Notification.user_id == current_user.id,
            Notification.user_id.is_(None)
        )
    else:
        user_cond = or_(
            Notification.user_id == current_user.id,
            and_(
                Notification.user_id.is_(None),
                Notification.workspace_id.in_(accessible_ws_ids)
            )
        )
    query = query.filter(user_cond)

    if workspace_id is not None:
        query = query.filter(Notification.workspace_id == workspace_id)

    if unread_only:
        query = query.filter(Notification.read == False)

    return paginate_query(
        query.order_by(Notification.created_at.desc(), Notification.id.desc()),
        pagination,
        serializer=lambda n: NotificationResponse.model_validate(n),
    )


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_as_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Đánh dấu thông báo là đã đọc."""
    notif = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notif:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thông báo không tồn tại"
        )

    # Check access: cannot modify other user's private notification or inaccessible workspace broadcast
    if current_user.role != "ADMIN":
        if notif.user_id is not None and notif.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền thao tác trên thông báo này"
            )
        if notif.user_id is None and notif.workspace_id is not None:
            accessible_ws_ids = _get_accessible_workspace_ids(current_user, db)
            if notif.workspace_id not in accessible_ws_ids:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Bạn không có quyền thao tác trên thông báo này"
                )

    notif.read = True
    db.commit()
    db.refresh(notif)
    return NotificationResponse.model_validate(notif)


@router.post("/mark-all-read")
def mark_all_notifications_as_read(
    workspace_id: Optional[int] = Query(None, description="ID workspace"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Đánh dấu tất cả thông báo chưa đọc là đã đọc."""
    accessible_ws_ids = _get_accessible_workspace_ids(current_user, db)

    if workspace_id is not None:
        if current_user.role != "ADMIN" and workspace_id not in accessible_ws_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Không có quyền truy cập vào Workspace này"
            )

    if current_user.role == "ADMIN":
        user_cond = or_(
            Notification.user_id == current_user.id,
            Notification.user_id.is_(None)
        )
    else:
        user_cond = or_(
            Notification.user_id == current_user.id,
            and_(
                Notification.user_id.is_(None),
                Notification.workspace_id.in_(accessible_ws_ids)
            )
        )

    query = db.query(Notification).filter(
        Notification.read == False,
        user_cond
    )

    if workspace_id is not None:
        query = query.filter(Notification.workspace_id == workspace_id)

    updated_count = query.update({Notification.read: True}, synchronize_session=False)
    db.commit()
    return {"success": True, "count": updated_count}
