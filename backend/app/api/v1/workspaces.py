import re
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.pagination import Page, PageParams, page_params, paginate_query
from app.core.security import get_current_user
from app.services import quota
from app.models.entities import User, Workspace, WorkspaceMember, BrandKit
from app.schemas.schemas import (
    WorkspaceCreate, WorkspaceUpdate, WorkspaceResponse,
    WorkspaceMemberAdd, WorkspaceMemberResponse
)

router = APIRouter(prefix="/workspaces", tags=["Không gian làm việc (Workspaces)"])

def generate_workspace_slug(name: str, user_id: int) -> str:
    cleaned = re.sub(r'[^a-zA-Z0-9]+', '-', name.lower()).strip('-')
    if not cleaned:
        cleaned = "workspace"
    short_uid = str(uuid.uuid4())[:8]
    return f"{cleaned}-{user_id}-{short_uid}"

def check_workspace_access(workspace: Workspace, user: User, db: Session) -> WorkspaceMember:
    """Kiểm tra quyền truy cập workspace:
    ADMIN hoặc owner có toàn quyền.
    Thành viên có quyền theo vai trò.
    Người ngoài bị chặn 403.
    """
    if user.role in ("ADMIN", "MANAGER") and workspace.owner_id == user.id:
        return None
    if user.role == "ADMIN":
        return None
    if workspace.owner_id == user.id:
        return None

    membership = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace.id,
        WorkspaceMember.user_id == user.id
    ).first()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền truy cập không gian làm việc này"
        )
    return membership

def check_workspace_admin_permission(workspace: Workspace, user: User, db: Session):
    """Kiểm tra quyền quản trị workspace (chỉ Owner hoặc AGENCY_MANAGER hoặc ADMIN)"""
    if user.role == "ADMIN":
        return
    if workspace.owner_id == user.id:
        return
    membership = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace.id,
        WorkspaceMember.user_id == user.id
    ).first()
    if not membership or membership.role not in ("AGENCY_MANAGER", "MANAGER"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ Quản trị viên (AGENCY_MANAGER hoặc Owner) mới có quyền thực hiện thao tác này"
        )

@router.get("", response_model=Page[WorkspaceResponse])
def get_workspaces(
    pagination: PageParams = Depends(page_params),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Workspace người dùng sở hữu hoặc là thành viên, có phân trang.

    Sắp xếp theo `id` cho CẢ ADMIN lẫn user thường: trước đây nhánh ADMIN không
    có `order_by` nên thứ tự do CSDL quyết định — với phân trang đó là nguồn lỗi
    kinh điển (một dòng có thể xuất hiện ở cả trang 1 và trang 2).
    """
    if current_user.role == "ADMIN":
        query = db.query(Workspace).filter(Workspace.status == "ACTIVE")
    else:
        # Lấy các workspace do user sở hữu hoặc user là thành viên
        member_ws_ids = db.query(WorkspaceMember.workspace_id).filter(
            WorkspaceMember.user_id == current_user.id
        ).subquery()

        query = db.query(Workspace).filter(
            Workspace.status == "ACTIVE",
            (Workspace.owner_id == current_user.id) | (Workspace.id.in_(member_ws_ids.select()))
        )

    return paginate_query(
        query.order_by(Workspace.id.asc()),
        pagination,
        serializer=lambda ws: WorkspaceResponse.model_validate(ws),
    )

@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
def create_workspace(
    req: WorkspaceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    slug = req.slug
    if not slug:
        slug = generate_workspace_slug(req.name, current_user.id)

    # Đảm bảo slug duy nhất
    existing_slug = db.query(Workspace).filter(Workspace.slug == slug).first()
    if existing_slug:
        slug = f"{slug}-{str(uuid.uuid4())[:6]}"

    workspace = Workspace(
        name=req.name,
        slug=slug,
        description=req.description,
        owner_id=current_user.id,
        status="ACTIVE"
    )

    # Hạn mức số workspace MỖI NGƯỜI DÙNG sở hữu. Kiểm tra trước khi insert.
    quota.enforce(
        db, quota.LIMIT_WORKSPACES_PER_USER,
        user=current_user, workspace_id=None, user_id=current_user.id,
    )

    db.add(workspace)
    db.commit()
    db.refresh(workspace)

    # Tự động gán người tạo làm AGENCY_MANAGER
    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=current_user.id,
        role="AGENCY_MANAGER"
    )
    db.add(member)

    # Tự động tạo Brand Kit ban đầu
    brand_kit = BrandKit(
        workspace_id=workspace.id,
        brand_name=workspace.name,
        usp="Chưa thiết lập",
        tone_of_voice="Chuyên nghiệp, hiện đại, tin cậy",
        banned_keywords_json="[]"
    )
    db.add(brand_kit)
    db.commit()

    return WorkspaceResponse.model_validate(workspace)

@router.get("/{workspace_id}", response_model=WorkspaceResponse)
def get_workspace(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không gian làm việc không tồn tại")

    check_workspace_access(workspace, current_user, db)
    return WorkspaceResponse.model_validate(workspace)

@router.put("/{workspace_id}", response_model=WorkspaceResponse)
def update_workspace(
    workspace_id: int,
    req: WorkspaceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không gian làm việc không tồn tại")

    check_workspace_admin_permission(workspace, current_user, db)

    if req.name is not None:
        workspace.name = req.name
    if req.description is not None:
        workspace.description = req.description

    db.commit()
    db.refresh(workspace)
    return WorkspaceResponse.model_validate(workspace)

@router.get("/{workspace_id}/quota")
def get_workspace_quota(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Trạng thái hạn mức gói miễn phí của workspace, để UI hiện đếm ngược.

    Dùng chung `check_workspace_access` với `GET /workspaces/{id}`: đây là dữ
    liệu của một tenant, không được đọc chéo. Quyền xem hạn mức KHÔNG đồng nghĩa
    quyền vượt hạn mứng — nơi thực thi vẫn là các endpoint tạo mới.
    """
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không gian làm việc không tồn tại")

    check_workspace_access(workspace, current_user, db)
    return quota.snapshot_workspace(
        db, workspace_id=workspace.id, user_id=current_user.id
    )


@router.post("/{workspace_id}/members", response_model=WorkspaceMemberResponse, status_code=status.HTTP_201_CREATED)
def add_workspace_member(
    workspace_id: int,
    req: WorkspaceMemberAdd,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không gian làm việc không tồn tại")

    check_workspace_admin_permission(workspace, current_user, db)

    target_user = db.query(User).filter(User.email == req.email).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Người dùng với email này không tồn tại")

    existing_member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace.id,
        WorkspaceMember.user_id == target_user.id
    ).first()
    if existing_member:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Người dùng đã là thành viên của không gian làm việc này")

    # Hạn mức thành viên: kiểm tra sau khi đã chặn trùng lặp, để một lời gọi lặp
    # lại báo "đã là thành viên" (lỗi của người gọi) chứ không phải 429.
    quota.enforce(
        db, quota.LIMIT_WORKSPACE_MEMBERS,
        user=current_user, workspace_id=workspace.id,
    )

    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=target_user.id,
        role=req.role
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return WorkspaceMemberResponse.model_validate(member)
