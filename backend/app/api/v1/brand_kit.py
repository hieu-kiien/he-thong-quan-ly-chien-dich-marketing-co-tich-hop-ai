import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.entities import User, Workspace, WorkspaceMember, BrandKit
from app.schemas.schemas import BrandKitUpdate, BrandKitResponse

router = APIRouter(prefix="/brand-kit", tags=["Brand Kit Nhận Diện Thương Hiệu"])

def check_workspace_access(workspace: Workspace, user: User, db: Session):
    if user.role in ("ADMIN", "MANAGER") and workspace.owner_id == user.id:
        return
    if user.role == "ADMIN":
        return
    if workspace.owner_id == user.id:
        return

    membership = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace.id,
        WorkspaceMember.user_id == user.id
    ).first()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền truy cập không gian làm việc này"
        )

def check_workspace_admin_permission(workspace: Workspace, user: User, db: Session):
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
            detail="Chỉ Quản lý (AGENCY_MANAGER hoặc Owner) mới có quyền chỉnh sửa Brand Kit"
        )

def resolve_workspace_id(user: User, db: Session, query_ws_id: Optional[int] = None, payload_ws_id: Optional[int] = None) -> int:
    if query_ws_id is not None:
        return query_ws_id
    if payload_ws_id is not None:
        return payload_ws_id
    # Tìm workspace mà user đang sở hữu hoặc tham gia
    owned_ws = db.query(Workspace).filter(Workspace.owner_id == user.id).first()
    if owned_ws:
        return owned_ws.id
    membership = db.query(WorkspaceMember).filter(WorkspaceMember.user_id == user.id).first()
    if membership:
        return membership.workspace_id
    return 1

@router.get("", response_model=BrandKitResponse)
def get_brand_kit(
    workspace_id: Optional[int] = Query(None, description="ID Workspace cần lấy Brand Kit"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    target_ws_id = resolve_workspace_id(current_user, db, query_ws_id=workspace_id)
    workspace = db.query(Workspace).filter(Workspace.id == target_ws_id).first()
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không gian làm việc không tồn tại")

    check_workspace_access(workspace, current_user, db)

    brand_kit = db.query(BrandKit).filter(BrandKit.workspace_id == target_ws_id).first()
    if not brand_kit:
        # Tự động tạo Brand Kit nếu chưa có
        brand_kit = BrandKit(
            workspace_id=target_ws_id,
            brand_name=workspace.name,
            usp="Chưa thiết lập",
            tone_of_voice="Chuyên nghiệp, hiện đại, tin cậy",
            banned_keywords_json="[]"
        )
        db.add(brand_kit)
        db.commit()
        db.refresh(brand_kit)

    return BrandKitResponse.model_validate(brand_kit)

@router.put("", response_model=BrandKitResponse)
def update_brand_kit(
    req: BrandKitUpdate,
    workspace_id: Optional[int] = Query(None, description="ID Workspace cần cập nhật Brand Kit"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    target_ws_id = resolve_workspace_id(current_user, db, query_ws_id=workspace_id, payload_ws_id=req.workspace_id)
    workspace = db.query(Workspace).filter(Workspace.id == target_ws_id).first()
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không gian làm việc không tồn tại")

    check_workspace_admin_permission(workspace, current_user, db)

    brand_kit = db.query(BrandKit).filter(BrandKit.workspace_id == target_ws_id).first()
    if not brand_kit:
        brand_kit = BrandKit(
            workspace_id=target_ws_id,
            brand_name=req.brand_name or workspace.name,
            usp=req.usp or "",
            tone_of_voice=req.tone_of_voice or "Chuyên nghiệp, hiện đại, tin cậy",
            banned_keywords_json=json.dumps(req.banned_keywords or [], ensure_ascii=False)
        )
        db.add(brand_kit)
    else:
        if req.brand_name is not None:
            brand_kit.brand_name = req.brand_name
        if req.usp is not None:
            brand_kit.usp = req.usp
        if req.tone_of_voice is not None:
            brand_kit.tone_of_voice = req.tone_of_voice
        if req.banned_keywords is not None:
            brand_kit.banned_keywords_json = json.dumps(req.banned_keywords, ensure_ascii=False)

    db.commit()
    db.refresh(brand_kit)
    return BrandKitResponse.model_validate(brand_kit)
