import re
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.pagination import Page, PageParams, page_params, paginate_query
from app.core.security import get_current_user, hash_password
from app.services import quota
from app.models.entities import User, Workspace, WorkspaceMember, BrandKit
from app.schemas.schemas import (
    WorkspaceCreate, WorkspaceUpdate, WorkspaceResponse,
    WorkspaceMemberAdd, WorkspaceMemberResponse,
    WorkspaceAccountProvision, WorkspaceRoleUpdate,
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
    """Kiểm tra quyền quản trị workspace (chỉ Owner hoặc AGENCY_MANAGER/MANAGER hoặc ADMIN)"""
    if user.role in ("ADMIN", "MANAGER", "AGENCY_MANAGER"):
        # Nếu là ADMIN hoặc Owner thì cho phép ngay; nếu là MANAGER thì phải thuộc workspace này
        if user.role == "ADMIN" or workspace.owner_id == user.id:
            return
    if workspace.owner_id == user.id:
        return
    membership = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace.id,
        WorkspaceMember.user_id == user.id
    ).first()
    if not membership or (membership.role not in ("AGENCY_MANAGER", "MANAGER") and user.role not in ("MANAGER", "AGENCY_MANAGER")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ Quản lý chiến dịch (MANAGER / AGENCY_MANAGER) hoặc Chủ sở hữu mới có quyền cấp phát & phân quyền tài khoản"
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


@router.get("/{workspace_id}/members")
def list_workspace_members(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Danh sách nhân sự trong Workspace kèm vai trò hệ thống và vai trò tại Workspace."""
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không gian làm việc không tồn tại")

    check_workspace_access(workspace, current_user, db)

    rows = (
        db.query(WorkspaceMember, User)
        .join(User, User.id == WorkspaceMember.user_id)
        .filter(WorkspaceMember.workspace_id == workspace.id)
        .order_by(WorkspaceMember.id.asc())
        .all()
    )

    items = []
    seen_user_ids = set()
    for member, usr in rows:
        seen_user_ids.add(usr.id)
        items.append({
            "id": member.id,
            "workspace_id": workspace.id,
            "user_id": usr.id,
            "email": usr.email,
            "full_name": usr.full_name,
            "workspace_role": member.role,
            "system_role": usr.role,
            "status": usr.status,
            "is_owner": workspace.owner_id == usr.id,
            "created_at": member.created_at,
        })

    if workspace.owner_id and workspace.owner_id not in seen_user_ids:
        owner = db.query(User).filter(User.id == workspace.owner_id).first()
        if owner:
            items.insert(0, {
                "id": 0,
                "workspace_id": workspace.id,
                "user_id": owner.id,
                "email": owner.email,
                "full_name": owner.full_name,
                "workspace_role": "AGENCY_MANAGER",
                "system_role": owner.role,
                "status": owner.status,
                "is_owner": True,
                "created_at": workspace.created_at,
            })

    return {"items": items, "total": len(items)}


@router.post("/{workspace_id}/provision-account", status_code=status.HTTP_201_CREATED)
def provision_workspace_account(
    workspace_id: int,
    req: WorkspaceAccountProvision,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cấp phát tài khoản mới (hoặc gán tài khoản đã có) kèm phân quyền RBAC trực tiếp bởi Quản lý / Chủ sở hữu.

    Giải quyết bài toán thực tế:
    - Tự đăng ký công khai (/auth/register) chỉ cấp quyền MARKETER để chống leo thang đặc quyền.
    - Quản lý (MANAGER / AGENCY_MANAGER / ADMIN / Owner) có thể tạo trực tiếp tài khoản cho
      Quản lý mới, Marketer hoặc Khách hàng duyệt bài (CLIENT_APPROVER) ngay trong Cài đặt.
    """
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không gian làm việc không tồn tại")

    check_workspace_admin_permission(workspace, current_user, db)

    normalized_role = (req.role or "MARKETER").strip().upper()
    system_role = "MANAGER" if normalized_role in ("MANAGER", "AGENCY_MANAGER") else normalized_role
    workspace_role = "AGENCY_MANAGER" if normalized_role in ("MANAGER", "AGENCY_MANAGER") else normalized_role

    email_clean = req.email.strip().lower()
    target_user = db.query(User).filter(User.email == email_clean).first()
    created_new_user = False

    if not target_user:
        target_user = User(
            email=email_clean,
            password_hash=hash_password(req.password),
            full_name=req.full_name.strip(),
            role=system_role if current_user.role in ("ADMIN", "MANAGER") else "MARKETER",
            status="ACTIVE",
        )
        db.add(target_user)
        db.flush()
        created_new_user = True
    else:
        # Nếu người dùng đã tồn tại, chỉ cập nhật vai trò toàn cục khi caller là ADMIN hoặc MANAGER
        if target_user.role != "ADMIN" and current_user.role in ("ADMIN", "MANAGER"):
            target_user.role = system_role
        if req.full_name and req.full_name.strip():
            target_user.full_name = req.full_name.strip()

    existing_member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace.id,
        WorkspaceMember.user_id == target_user.id,
    ).first()

    if existing_member:
        existing_member.role = workspace_role
        member = existing_member
    else:
        quota.enforce(
            db, quota.LIMIT_WORKSPACE_MEMBERS,
            user=current_user, workspace_id=workspace.id,
        )
        member = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=target_user.id,
            role=workspace_role,
        )
        db.add(member)

    db.commit()
    db.refresh(target_user)
    db.refresh(member)

    return {
        "id": member.id,
        "workspace_id": workspace.id,
        "user_id": target_user.id,
        "email": target_user.email,
        "full_name": target_user.full_name,
        "workspace_role": member.role,
        "system_role": target_user.role,
        "status": target_user.status,
        "is_owner": workspace.owner_id == target_user.id,
        "created_new_user": created_new_user,
        "created_at": member.created_at,
    }


@router.patch("/{workspace_id}/members/{member_user_id}/role")
def update_workspace_member_role(
    workspace_id: int,
    member_user_id: int,
    req: WorkspaceRoleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Thay đổi vai trò (MANAGER / MARKETER / CLIENT_APPROVER) của một nhân sự trong Workspace."""
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không gian làm việc không tồn tại")

    check_workspace_admin_permission(workspace, current_user, db)

    target_user = db.query(User).filter(User.id == member_user_id).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy người dùng")

    normalized_role = req.role.strip().upper()
    system_role = "MANAGER" if normalized_role in ("MANAGER", "AGENCY_MANAGER") else normalized_role
    workspace_role = "AGENCY_MANAGER" if normalized_role in ("MANAGER", "AGENCY_MANAGER") else normalized_role

    if workspace.owner_id == target_user.id and system_role != "MANAGER":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể hạ quyền Chủ sở hữu (Owner) của không gian làm việc",
        )

    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace.id,
        WorkspaceMember.user_id == target_user.id,
    ).first()
    if not member:
        member = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=target_user.id,
            role=workspace_role,
        )
        db.add(member)
    else:
        member.role = workspace_role

    if target_user.role != "ADMIN" and current_user.role in ("ADMIN", "MANAGER"):
        target_user.role = system_role

    db.commit()
    db.refresh(target_user)
    db.refresh(member)

    return {
        "id": member.id,
        "workspace_id": workspace.id,
        "user_id": target_user.id,
        "email": target_user.email,
        "full_name": target_user.full_name,
        "workspace_role": member.role,
        "system_role": target_user.role,
        "status": target_user.status,
        "is_owner": workspace.owner_id == target_user.id,
    }


@router.delete("/{workspace_id}/members/{member_user_id}")
def remove_workspace_member(
    workspace_id: int,
    member_user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Gỡ một thành viên khỏi Workspace (không xóa tài khoản gốc, không cho phép gỡ Chủ sở hữu)."""
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không gian làm việc không tồn tại")

    check_workspace_admin_permission(workspace, current_user, db)

    if workspace.owner_id == member_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể gỡ Chủ sở hữu khỏi không gian làm việc",
        )

    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace.id,
        WorkspaceMember.user_id == member_user_id,
    ).first()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thành viên không thuộc không gian làm việc này")

    db.delete(member)
    db.commit()
    return {"status": "REMOVED", "user_id": member_user_id}


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

