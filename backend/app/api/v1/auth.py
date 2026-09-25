import re
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_password, hash_password, create_access_token, get_current_user
from app.models.entities import User, Workspace, WorkspaceMember, BrandKit
from app.schemas.schemas import LoginRequest, TokenResponse, UserResponse, UserRegister

router = APIRouter(prefix="/auth", tags=["Xác thực & Phân quyền"])

def generate_workspace_slug(name: str, user_id: int) -> str:
    cleaned = re.sub(r'[^a-zA-Z0-9]+', '-', name.lower()).strip('-')
    if not cleaned:
        cleaned = "workspace"
    short_uid = str(uuid.uuid4())[:8]
    return f"{cleaned}-{user_id}-{short_uid}"

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(req: UserRegister, db: Session = Depends(get_db)):
    # 1. Kiểm tra email duy nhất
    existing_user = db.query(User).filter(User.email == req.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email này đã được sử dụng trong hệ thống"
        )

    # 2. Tạo User mới
    role = req.role or "MARKETER"
    user = User(
        email=req.email,
        full_name=req.full_name,
        password_hash=hash_password(req.password),
        role=role,
        status="ACTIVE"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # 3. Tự động tạo Personal Workspace ban đầu cho người dùng
    ws_name = f"Workspace của {user.full_name}"
    ws_slug = generate_workspace_slug(user.full_name, user.id)
    ws = Workspace(
        name=ws_name,
        slug=ws_slug,
        description=f"Không gian làm việc cá nhân của {user.full_name}",
        owner_id=user.id,
        status="ACTIVE"
    )
    db.add(ws)
    db.commit()
    db.refresh(ws)

    # 4. Gán người dùng vào Workspace
    member_role = "AGENCY_MANAGER" if role in ("MANAGER", "AGENCY_MANAGER") else role
    ws_member = WorkspaceMember(
        workspace_id=ws.id,
        user_id=user.id,
        role=member_role
    )
    db.add(ws_member)

    # 5. Tự động khởi tạo Brand Kit mặc định cho Workspace
    brand_kit = BrandKit(
        workspace_id=ws.id,
        brand_name=user.full_name,
        usp="Chưa thiết lập",
        tone_of_voice="Chuyên nghiệp, hiện đại, tin cậy",
        banned_keywords_json="[]"
    )
    db.add(brand_kit)
    db.commit()

    return UserResponse.model_validate(user)

@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email hoặc mật khẩu không chính xác",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if user.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản đã bị vô hiệu hóa"
        )

    access_token = create_access_token(data={
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "full_name": user.full_name
    })

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)

