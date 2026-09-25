import re
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
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

@router.get("", response_model=List[WorkspaceResponse])
def get_workspaces(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role == "ADMIN":
        workspaces = db.query(Workspace).filter(Workspace.status == "ACTIVE").all()
        return [WorkspaceResponse.model_validate(ws) for ws in workspaces]

    # Lấy các workspace do user sở hữu hoặc user là thành viên
    member_ws_ids = db.query(WorkspaceMember.workspace_id).filter(
        WorkspaceMember.user_id == current_user.id
    ).subquery()

    workspaces = db.query(Workspace).filter(
        Workspace.status == "ACTIVE",
        (Workspace.owner_id == current_user.id) | (Workspace.id.in_(member_ws_ids.select()))
    ).order_by(Workspace.id.asc()).all()

    return [WorkspaceResponse.model_validate(ws) for ws in workspaces]

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

    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=target_user.id,
        role=req.role
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return WorkspaceMemberResponse.model_validate(member)
