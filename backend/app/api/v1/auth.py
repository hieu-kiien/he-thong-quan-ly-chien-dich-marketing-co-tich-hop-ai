import re
import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
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
    enforce_quota,
)
from app.models.entities import User, Workspace, WorkspaceMember, BrandKit
from app.schemas.schemas import (
    LoginRequest,
    PasswordChangeRequest,
    TokenResponse,
    UserResponse,
    UserRegister,
)

router = APIRouter(prefix="/auth", tags=["Xác thực & Phân quyền"])

logger = logging.getLogger(__name__)


def _resolve_client_ip(request: Request) -> str:
    """Xác định IP thật của client, chỉ dùng X-Forwarded-For khi proxy đáng tin."""
    from app.core.security import is_trusted_proxy  # import cục bộ tránh vòng lặp

    peer = request.client.host if request.client else "unknown"
    if not is_trusted_proxy(peer):
        return peer

    # Cloudflare dùng CF-Connecting-IP cho IP thật của client. Phải ưu tiên
    # header này TRƯỚC X-Forwarded-For.
    #
    # Lý do (sự cố thật khi triển khai qua Cloudflare Tunnel, đã đo trên VPS):
    # X-Forwarded-For KHÔNG ổn định — cùng một client quan sát được cả IP thật lẫn
    # IP điểm vào dùng chung của Cloudflare (`2001:470:...`) tuỳ lúc. Đọc phần đầu
    # chuỗi XFF vì vậy gộp nhiều người dùng vào một bucket rate limit: một người gõ
    # sai mật khẩu vài lần thì mọi người khác cũng bị khoá. CF-Connecting-IP luôn là
    # IP client thật, đã kiểm chứng qua tunnel (171.229.242.250 khớp IP thật).
    #
    # Lưu ý triển khai: nginx phải forward header này (proxy_set_header
    # CF-Connecting-IP $http_cf_connecting_ip) — nếu không, header không tới app.
    # X-Forwarded-For chỉ là phương án dự phòng cho hạ tầng không có Cloudflare.
    cf_ip = (request.headers.get("cf-connecting-ip") or "").strip()
    if cf_ip:
        return cf_ip

    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # Chuỗi XFF là "client, proxy1, proxy2, ...". Phần đầu tiên là client thật.
        return forwarded.split(",")[0].strip() or peer

    return request.headers.get("x-real-ip") or peer


def generate_workspace_slug(name: str, user_id: int) -> str:
    cleaned = re.sub(r'[^a-zA-Z0-9]+', '-', name.lower()).strip('-')
    if not cleaned:
        cleaned = "workspace"
    short_uid = str(uuid.uuid4())[:8]
    return f"{cleaned}-{user_id}-{short_uid}"

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(req: UserRegister, request: Request, db: Session = Depends(get_db)):
    # Hạn mức đăng ký: trước đây endpoint này không bị giới hạn, nên có thể tạo vô
    # hạn tài khoản + workspace + brand kit, vừa tốn tài nguyên vừa loãng dữ liệu.
    enforce_quota(f"auth:register:ip={_resolve_client_ip(request)}", max_calls=10, window_seconds=60 * 60)

    # 1. Kiểm tra email duy nhất
    existing_user = db.query(User).filter(User.email == req.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email này đã được sử dụng trong hệ thống"
        )

    # 2. Tạo User mới (Chặn leo thang đặc quyền Privilege Escalation)
    # Không được nhận vai trò đặc quyền từ client: tự đăng ký luôn là MARKETER.
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
    try:
        # Phải bắt IntegrityError: hai request đăng ký song song cùng email đều
        # qua bước SELECT ở trên, rồi cả hai INSERT -> thẳng 500 thay vì 400.
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email này đã được sử dụng trong hệ thống"
        )
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
    ws_member = WorkspaceMember(
        workspace_id=ws.id,
        user_id=user.id,
        # Người tự đăng ký luôn là MARKETER, nên vai trò trong workspace cũng vậy.
        role=role
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
    #
    # PHẢI đọc IP từ X-Forwarded-For chứ không dùng `request.client.host`.
    # Khi chạy sau nginx/Cloudflare, `request.client.host` là địa chỉ của proxy,
    # nên MỌI người dùng cùng nằm trong một bucket: 5 lần đoán sai từ bất kỳ ai
    # cũng khoá đúng email đó cho toàn bộ hệ thống (DoS đăng nhập theo email),
    # và rate limit thực tế yếu hơn hình thức trên giấy.
    client_ip = _resolve_client_ip(request)
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

    # Token chỉ chứa `sub` (id). KHÔNG nhúng email/role/full_name: JWT là base64
    # (không mã hoá), nên mọi PII đó đều đọc được bằng mắt thường từ localStorage,
    # và bất kỳ XSS nào cũng đọc được ngay. Vai trò được đọc lại từ DB ở
    # `get_current_user` (xem app/core/security.py), nên bỏ khỏi token không ảnh
    # hưởng phân quyền — thay vào đó loại bỏ nguy cơ token "cũ" mang vai trò cũ.
    #
    # `ver` = phiên bản token hiện tại của user: dùng để thu hồi phiên khi
    # logout / đổi mật khẩu (xem assert_token_version_current).
    access_token = create_access_token(data={"sub": str(user.id), "ver": int(user.token_version or 0)})

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Thu hồi phiên hiện tại (và mọi token khác đã cấp cho user này).

    JWT không thể bị server "hạ" đơn lẻ, nên revocation thực hiện bằng cách tăng
    `token_version`: mọi token phát hành trước đó không còn khớp → 401 fail-closed.
    """
    current_user.token_version = int(current_user.token_version or 0) + 1
    db.commit()


@router.post("/change-password", status_code=status.HTTP_200_OK)
def change_password(
    payload: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Đổi mật khẩu: xác minh mật khẩu hiện tại, ghi đè hash mới, thu hồi phiên cũ."""
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu hiện tại không chính xác",
        )
    if payload.new_password == payload.current_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu mới phải khác mật khẩu hiện tại",
        )

    current_user.password_hash = hash_password(payload.new_password)
    # Đổi mật khẩu = thu hồi mọi phiên đang mở (kể cả token đang dùng request này).
    current_user.token_version = int(current_user.token_version or 0) + 1
    db.commit()

    # Cấp token mới cho phiên đang đổi để người dùng không bị đá ra giữa chừng.
    new_token = create_access_token(
        data={"sub": str(current_user.id), "ver": int(current_user.token_version or 0)}
    )
    return TokenResponse(
        access_token=new_token,
        token_type="bearer",
        user=UserResponse.model_validate(current_user),
    )


DEMO_PERSONA_EMAILS = {
    "manager": "manager@gmail.com",
    "marketer": "marketer@gmail.com",
    "approver": "approver@gmail.com",
}


@router.post("/switch-demo-role", response_model=TokenResponse)
def switch_demo_role(
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Chuyển nhanh giữa 3 vai trò Demo RBAC (Manager / Marketer / Approver) trong 1 cú nhấp.

    Bảo mật:
    - Yêu cầu người gọi ĐÃ ĐĂNG NHẬP hợp lệ (`get_current_user`).
    - Không cần nhúng mật khẩu rõ vào bundle Frontend (tuân thủ tuyệt đối
      `test_seed_credentials_not_shipped.py`).
    - Chỉ cho phép chuyển sang các tài khoản mẫu nằm trong `DEMO_PERSONA_EMAILS`.
    """
    role_key = str(payload.get("role_key") or "").strip().lower()
    target_email = DEMO_PERSONA_EMAILS.get(role_key)
    if not target_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vai trò demo không hợp lệ. Chọn một trong: manager, marketer, approver.",
        )

    target_user = db.query(User).filter(User.email == target_email).first()
    if not target_user or target_user.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tài khoản mẫu ({target_email}) chưa được khởi tạo hoặc không hoạt động.",
        )

    access_token = create_access_token(
        data={"sub": str(target_user.id), "ver": int(target_user.token_version or 0)}
    )
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(target_user),
    )


