from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, false

from app.core.database import get_db
from app.core.pagination import Page, PageParams, page_params, paginate_query
from app.core.security import get_current_user
from app.models.entities import Task, Campaign, User, Workspace, WorkspaceMember, CampaignMember, utc_now
from app.schemas.schemas import TaskCreate, TaskUpdate, TaskResponse, TaskBase
from app.api.v1.campaigns import _accessible_workspace_ids

router = APIRouter(tags=["Quản lý Công việc & Tác vụ"])


def _check_campaign_access(campaign: Campaign, user: User, db: Session):
    """Kiểm tra quyền truy cập vào chiến dịch (Tenant Isolation & RBAC)."""
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


def _get_task_and_check_access(task_id: int, user: User, db: Session, for_edit: bool = False) -> Task:
    """Tìm task và xác thực quyền xem/sửa."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy tác vụ")

    if user.role == "ADMIN":
        return task

    # Kiểm tra campaign liên quan
    campaign = db.query(Campaign).filter(Campaign.id == task.campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chiến dịch của tác vụ không tồn tại")

    # Fail-closed: workspace NULL
    if campaign.workspace_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Chiến dịch không thuộc workspace hợp lệ")

    # Workspace boundary: caller must belong to the workspace
    ws = db.query(Workspace).filter(Workspace.id == campaign.workspace_id).first()
    is_ws_owner = ws is not None and ws.owner_id == user.id
    is_ws_member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == campaign.workspace_id,
        WorkspaceMember.user_id == user.id
    ).first() is not None
    if not (is_ws_owner or is_ws_member):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access tasks in this workspace"
        )

    # Nếu chỉ đọc
    if not for_edit:
        # User là assignee hoặc creator luôn được xem trong workspace
        if task.assignee_id == user.id or task.creator_id == user.id:
            return task
        _check_campaign_access(campaign, user, db)
        return task

    # Nếu chỉnh sửa:
    # Assignee được phép đổi trạng thái (sẽ kiểm tra chi tiết trong endpoint)
    # Creator, Campaign Owner, Workspace Manager được phép chỉnh sửa toàn diện
    is_creator = task.creator_id == user.id
    is_campaign_owner = campaign.owner_id == user.id
    is_ws_manager = is_ws_owner or (
        user.role in ("MANAGER", "AGENCY_MANAGER") and is_ws_member
    )

    if not (is_creator or is_campaign_owner or is_ws_manager or task.assignee_id == user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền chỉnh sửa tác vụ này"
        )

    return task


# --- CAMPAIGN TASKS ENDPOINTS ---

@router.get("/campaigns/{campaign_id}/tasks", response_model=Page[TaskResponse])
def get_campaign_tasks(
    campaign_id: int,
    status_filter: Optional[str] = Query(None, alias="status"),
    priority: Optional[str] = Query(None),
    assignee_id: Optional[int] = Query(None),
    pagination: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Tác vụ trong một chiến dịch (lọc theo trạng thái, độ ưu tiên, người nhận) + phân trang.

    `_check_campaign_access` chốt quyền ở cấp chiến dịch TRƯỚC khi cắt trang.
    """
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chiến dịch không tồn tại")

    _check_campaign_access(campaign, current_user, db)

    query = db.query(Task).filter(Task.campaign_id == campaign_id)

    if status_filter:
        query = query.filter(Task.status == status_filter)
    if priority:
        query = query.filter(Task.priority == priority)
    if assignee_id:
        query = query.filter(Task.assignee_id == assignee_id)

    # `nullslast()` giữ nguyên hành vi "việc chưa có hạn nằm cuối"; thêm `Task.id`
    # làm khoá phá thế hoàn toàn để trang sau không lặp/mất dòng.
    return paginate_query(
        query.order_by(Task.due_date.asc().nullslast(), Task.created_at.desc(), Task.id.asc()),
        pagination,
    )


@router.post("/campaigns/{campaign_id}/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_campaign_task(
    campaign_id: int,
    task_in: TaskBase,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Tạo tác vụ mới cho chiến dịch (Manager, Campaign Owner, hoặc Campaign Member)."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chiến dịch không tồn tại")

    # Fail-closed: workspace NULL
    if campaign.workspace_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Chiến dịch không thuộc workspace hợp lệ")

    _check_campaign_access(campaign, current_user, db)

    # Xác thực assignee nếu có: phải thuộc workspace hoặc chiến dịch
    if task_in.assignee_id:
        assignee = db.query(User).filter(User.id == task_in.assignee_id).first()
        if not assignee:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Người được giao việc không tồn tại")

        ws = db.query(Workspace).filter(Workspace.id == campaign.workspace_id).first()
        is_assignee_ws_owner = ws is not None and ws.owner_id == task_in.assignee_id
        is_assignee_ws_member = db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == campaign.workspace_id,
            WorkspaceMember.user_id == task_in.assignee_id
        ).first() is not None
        is_assignee_campaign_member = db.query(CampaignMember).filter(
            CampaignMember.campaign_id == campaign.id,
            CampaignMember.user_id == task_in.assignee_id
        ).first() is not None
        is_assignee_campaign_owner = campaign.owner_id == task_in.assignee_id

        if not (is_assignee_ws_owner or is_assignee_ws_member or is_assignee_campaign_member or is_assignee_campaign_owner or assignee.role == "ADMIN"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Người được giao việc không thuộc workspace hoặc chiến dịch này"
            )

    workspace_id = campaign.workspace_id

    new_task = Task(
        campaign_id=campaign.id,
        workspace_id=workspace_id,
        title=task_in.title,
        description=task_in.description,
        task_type=task_in.task_type,
        assignee_id=task_in.assignee_id,
        creator_id=current_user.id,
        status=task_in.status,
        priority=task_in.priority,
        due_date=task_in.due_date,
        # Dùng `utc_now()` (tz-aware) như mọi model khác. `datetime.utcnow()` trả
        # về datetime NAIVE, nên so sánh Task với datetime tz-aware ở tầng Python
        # sẽ ném TypeError: can't compare offset-naive and offset-aware datetimes.
        # Cột DateTime của SQLite cũng không lưu được tzinfo.
        created_at=utc_now(),
        updated_at=utc_now()
    )

    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task


# --- MY TASKS ENDPOINT ---

@router.get("/tasks/my-tasks", response_model=Page[TaskResponse])
def get_my_tasks(
    status_filter: Optional[str] = Query(None, alias="status"),
    priority: Optional[str] = Query(None),
    include_completed: bool = Query(True),
    campaign_id: Optional[int] = Query(None, description="Lọc theo chiến dịch"),
    search: Optional[str] = Query(None, description="Tìm trong tiêu đề hoặc mô tả"),
    due: Optional[str] = Query(
        None,
        pattern="^(today|overdue)$",
        description="overdue = quá hạn và chưa xong; today = đến hạn đúng hôm nay",
    ),
    pagination: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Tác vụ được giao cho người dùng hiện tại (My Work Today) + phân trang.

    Nhánh `query.filter(false())` khi user không thuộc workspace nào là fail-closed
    có chủ đích: `total = 0` thay vì lộ bất kỳ tác vụ nào.

    `campaign_id` / `search` / `due` tồn tại để frontend phân trang ở phía server
    được ĐÚNG. Trước đây màn hình này lọc hoàn toàn ở client; nếu ta chỉ thêm
    phân trang mà giữ nguyên cách lọc đó, mỗi lần đổi trang sẽ chỉ lấy trang đầu
    của tập đã lọc rồi cắt tiếp — tức nhiều tác vụ biến mất khỏi danh sách mà
    `total` vẫn báo đúng. Đưa bộ lọc xuống server là điều kiện để phân trang
    tương đương, không phải mở rộng tính năng.
    """
    query = db.query(Task).filter(Task.assignee_id == current_user.id)

    if current_user.role != "ADMIN":
        ws_ids = _accessible_workspace_ids(current_user, db)
        if ws_ids:
            query = query.filter(Task.workspace_id.in_(ws_ids))
        else:
            query = query.filter(false())

    if status_filter:
        query = query.filter(Task.status == status_filter)
    elif not include_completed:
        query = query.filter(Task.status != "DONE")

    if priority:
        query = query.filter(Task.priority == priority)
    if campaign_id is not None:
        query = query.filter(Task.campaign_id == campaign_id)
    if search:
        search_fmt = f"%{search}%"
        query = query.filter(
            (Task.title.ilike(search_fmt)) | (Task.description.ilike(search_fmt))
        )
    if due:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        if due == "overdue":
            # Quá hạn = có hạn, hạn đã qua, và chưa xong.
            query = query.filter(Task.due_date.isnot(None), Task.due_date < today, Task.status != "DONE")
        else:
            query = query.filter(Task.due_date == today)

    return paginate_query(
        query.order_by(Task.due_date.asc().nullslast(), Task.created_at.desc(), Task.id.asc()),
        pagination,
    )


# --- SINGLE TASK ENDPOINTS ---

@router.get("/tasks/my-tasks/summary")
def get_my_tasks_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Bốn con số tổng hợp của tác vụ được giao, phạm vi TOÀN BỘ (không theo trang).

    Vì sao cần: trước đây các thẻ thống kê ở đầu màn hình đếm trên mảng `tasks`
    mà client đã tải về. Sau khi phân trang ở server, mảng đó chỉ là trang hiện
    tại, nên đếm trên đó sẽ báo sai ngay khi người dùng sang trang 2 — thẻ
    "Quá hạn (3)" hóa ra là 3 trong 20 dòng của trang đó chứ không phải 3 trong
    toàn bộ tác vụ. Đây là lớp số liệu đúng, tính bằng 4 truy vấn `COUNT`
    có index, không phải kéo cả danh sách về client.

    Dùng chung đúng bộ lọc tenant với `/tasks/my-tasks` để hai nơi không lệch nhau.
    """
    base = db.query(Task).filter(Task.assignee_id == current_user.id)
    if current_user.role != "ADMIN":
        ws_ids = _accessible_workspace_ids(current_user, db)
        base = base.filter(Task.workspace_id.in_(ws_ids)) if ws_ids else base.filter(false())

    today = datetime.utcnow().strftime("%Y-%m-%d")
    open_clause = Task.status != "DONE"

    return {
        "overdue": int(
            base.filter(Task.due_date.isnot(None), Task.due_date < today, open_clause).count()
        ),
        "today": int(
            base.filter(Task.due_date == today, open_clause).count()
        ),
        "in_progress": int(base.filter(Task.status == "IN_PROGRESS").count()),
        "done": int(base.filter(Task.status == "DONE").count()),
        "total": int(base.count()),
    }


@router.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lấy thông tin chi tiết một tác vụ."""
    task = _get_task_and_check_access(task_id, current_user, db, for_edit=False)
    return task


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    task_update: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cập nhật tác vụ. Người được giao việc (assignee) có thể đổi status/priority. Quản lý/người tạo được sửa toàn diện."""
    task = _get_task_and_check_access(task_id, current_user, db, for_edit=True)

    campaign = db.query(Campaign).filter(Campaign.id == task.campaign_id).first()
    is_manager_or_creator = (
        current_user.role == "ADMIN"
        or task.creator_id == current_user.id
        or (campaign and campaign.owner_id == current_user.id)
        or current_user.role in ("MANAGER", "AGENCY_MANAGER")
    )

    update_data = task_update.model_dump(exclude_unset=True)

    # Nếu chỉ là assignee (không phải manager/creator), chỉ được sửa status và priority
    if not is_manager_or_creator:
        restricted_keys = {"title", "description", "task_type", "assignee_id", "due_date"}
        attempted_restrictions = restricted_keys.intersection(update_data.keys())
        if attempted_restrictions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Người thực hiện chỉ có quyền cập nhật trạng thái (status) hoặc độ ưu tiên (priority). Không thể sửa: {', '.join(attempted_restrictions)}"
            )

    # Xác thực assignee nếu được thay đổi: phải thuộc workspace hoặc chiến dịch
    if "assignee_id" in update_data and update_data["assignee_id"] is not None:
        assignee = db.query(User).filter(User.id == update_data["assignee_id"]).first()
        if not assignee:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Người được giao việc không tồn tại")
        if campaign and campaign.workspace_id is not None:
            ws = db.query(Workspace).filter(Workspace.id == campaign.workspace_id).first()
            is_assignee_ws_owner = ws is not None and ws.owner_id == update_data["assignee_id"]
            is_assignee_ws_member = db.query(WorkspaceMember).filter(
                WorkspaceMember.workspace_id == campaign.workspace_id,
                WorkspaceMember.user_id == update_data["assignee_id"]
            ).first() is not None
            is_assignee_campaign_member = db.query(CampaignMember).filter(
                CampaignMember.campaign_id == campaign.id,
                CampaignMember.user_id == update_data["assignee_id"]
            ).first() is not None
            is_assignee_campaign_owner = campaign.owner_id == update_data["assignee_id"]

            if not (is_assignee_ws_owner or is_assignee_ws_member or is_assignee_campaign_member or is_assignee_campaign_owner or assignee.role == "ADMIN"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Người được giao việc không thuộc workspace hoặc chiến dịch này"
                )

    for key, value in update_data.items():
        setattr(task, key, value)

    task.updated_at = utc_now()
    db.commit()
    db.refresh(task)
    return task


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Xóa tác vụ (chỉ người tạo, chủ chiến dịch, quản lý workspace hoặc admin)."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tác vụ không tồn tại")

    campaign = db.query(Campaign).filter(Campaign.id == task.campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chiến dịch của tác vụ không tồn tại")

    # DELETE task phải verify workspace access
    if current_user.role != "ADMIN":
        if campaign.workspace_id is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Chiến dịch không thuộc workspace hợp lệ")
        ws = db.query(Workspace).filter(Workspace.id == campaign.workspace_id).first()
        is_ws_owner = ws is not None and ws.owner_id == current_user.id
        is_ws_member = db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == campaign.workspace_id,
            WorkspaceMember.user_id == current_user.id
        ).first() is not None
        if not (is_ws_owner or is_ws_member):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access tasks in this workspace"
            )

    is_authorized = (
        current_user.role == "ADMIN"
        or task.creator_id == current_user.id
        or (campaign and campaign.owner_id == current_user.id)
        or current_user.role in ("MANAGER", "AGENCY_MANAGER")
    )

    if not is_authorized:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bạn không có quyền xóa tác vụ này")

    db.delete(task)
    db.commit()
    return None
