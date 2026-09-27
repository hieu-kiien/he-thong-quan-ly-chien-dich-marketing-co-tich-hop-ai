import re
import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import (
    verify_password,
    hash_password,
    create_access_token,
    get_current_user,
    check_login_rate_limit,
    record_login_failure,
    reset_login_rate_limit,
)
from app.models.entities import User, Workspace, WorkspaceMember, BrandKit
from app.schemas.schemas import LoginRequest, TokenResponse, UserResponse, UserRegister

router = APIRouter(prefix="/auth", tags=["Xác thực & Phân quyền"])

logger = logging.getLogger(__name__)

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

    # 2. Tạo User mới (Chặn leo thang đặc quyền Privilege Escalation)
    requested_role = (req.role or "MARKETER").strip().upper()
    if requested_role in ("AGENCY_MANAGER", "CLIENT_APPROVER", "ADMIN", "MANAGER"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Self-registration with privileged roles is not allowed. Contact your workspace administrator."
        )
    role = "MARKETER"
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
def login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    # Brute-force protection (H1): khoá theo (email, client IP) để vừa chặn tấn
    # công dò tài khoản vừa tránh kẻ xấu khoá chính một email từ IP khác.
    client_ip = request.client.host if request.client else "unknown"
    identifier = f"{req.email}|{client_ip}"

    # PHẢI kiểm tra TRƯỚC khi chạm vào CSDL: nếu không, kẻ dò mật khẩu vẫn tiêu tốn
    # truy vấn cho mỗi lần đoán và không bao giờ bị chặn.
    check_login_rate_limit(identifier)

    # Nhánh DB được bọc riêng: nếu lỗi CSDL xảy ra, ta KHÔNG được bỏ sót việc
    # ghi nhận lần thử sai, nếu không kẻ tấn công có thể gây lỗi DB liên tục để
    # đẩy bộ đếm rate limit về 0.
    try:
        user = db.query(User).filter(User.email == req.email).first()
        password_ok = bool(user) and verify_password(req.password, user.password_hash)
    except HTTPException:
        raise
    except Exception:
        record_login_failure(identifier)
        logger.exception("Loi khi truy van nguoi dung dang dang nhap: %s", req.email)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Dịch vụ đăng nhập tạm thời không khả dụng. Vui lòng thử lại sau.",
            headers={"Retry-After": "30"},
        )

    if not user or not password_ok:
        record_login_failure(identifier)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email hoặc mật khẩu không chính xác",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Đăng nhập thành công: xoá bộ đếm để người dùng thật không bị khoá oan.
    reset_login_rate_limit(identifier)

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

