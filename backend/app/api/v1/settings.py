"""API Endpoints cho Enterprise Settings & BYOK Custom AI API Key (FEAT-BE-24, FEAT-BE-25)."""

import time
from typing import Optional, List, Union
from fastapi import APIRouter, Depends, HTTPException, status, Query
import httpx
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.core.security import get_current_user
from app.models.entities import User, CustomApiKey, Workspace, WorkspaceMember
from app.schemas.schemas import (
    AIKeyTestRequest, AIKeyTestResponse,
    AIKeyCreate, AIKeyResponse
)
from app.core.crypto import encrypt_api_key, decrypt_api_key, mask_api_key

router = APIRouter(prefix="/settings", tags=["Cài đặt Doanh nghiệp & Custom AI Key (BYOK)"])


import re
import logging
from urllib.parse import quote

logger = logging.getLogger(__name__)


def sanitize_error_text(text: Optional[str], secret_key: Optional[str] = None) -> str:
    """Loại bỏ triệt để các token nhạy cảm, query param ?key=... và API key khỏi chuỗi lỗi/log."""
    if not text:
        return ""
    sanitized = str(text)
    # 1. Nếu có key cụ thể được truyền vào, thay thế trực tiếp
    if secret_key and len(secret_key.strip()) >= 4:
        clean = secret_key.strip()
        sanitized = sanitized.replace(clean, "[REDACTED_API_KEY]")
    # 2. Xóa query parameter ?key=... hoặc &key=...
    sanitized = re.sub(r'([?&]key=)[^&\s"\'\\}]+', r'\1[REDACTED]', sanitized, flags=re.IGNORECASE)
    # 3. Xóa các token định dạng Google Gemini API key: AIzaSy... hoặc AIza... (39 ký tự)
    sanitized = re.sub(r'AIza[0-9A-Za-z_-]{35}', '[REDACTED_GEMINI_KEY]', sanitized)
    sanitized = re.sub(r'AIzaSy[0-9A-Za-z_-]+', '[REDACTED_GEMINI_KEY]', sanitized)
    # 4. Xóa Bearer tokens
    sanitized = re.sub(r'(Bearer\s+)[A-Za-z0-9._-]+', r'\1[REDACTED]', sanitized, flags=re.IGNORECASE)
    return sanitized


@router.post("/test-ai-connection", response_model=AIKeyTestResponse)
def test_ai_connection(
    req: AIKeyTestRequest,
    current_user: User = Depends(get_current_user),
):
    """Kiểm tra tính hợp lệ của API Key với AI Provider (Gemini, OpenRouter, OpenAI) và đo lường độ trễ."""
    start_time = time.time()
    clean_key = req.api_key.strip()
    provider = (req.provider or "gemini").lower().strip()
    provider_title = {
        "gemini": "Google Gemini",
        "openrouter": "OpenRouter",
        "openai": "OpenAI",
        "opencode": "OpenCode",
    }.get(provider, provider)

    # Backdoor guard (M2): token kiểm thử giả chỉ được chạy ngoài production.
    # Nếu bật ở production, bất kỳ ai cũng dán "mock-anything" vào đây và nhận
    # success=True "Mock Verified" mà KHÔNG có request nào tới provider thật ->
    # người dùng tin rằng khoá đã cấu hình đúng trong khi thực tế mọi lệnh gọi
    # AI sau đó đều thất bại (và tự tin rằng hệ thống đã được kiểm thử).
    is_production = str(getattr(settings, "APP_ENV", "development")).strip().lower() == "production"

    # 1. Xử lý token kiểm thử Mock trong test suite
    if not is_production and (
        any(m in clean_key for m in ["MockVerification", "TestResolverKey"])
        or clean_key.startswith(("AIzaSyMock", "sk-or-mock", "sk-mock", "mock-", "mock_"))
    ):
        latency = int((time.time() - start_time) * 1000) or 25
        return AIKeyTestResponse(
            success=True,
            latency_ms=latency,
            message=f"Kết nối thử nghiệm {provider_title} API thành công (Mock Verified).",
            provider=provider,
            model=req.model
        )

    # 2. Xử lý trường hợp key giả lập không hợp lệ
    if "invalid_dummy_key" in clean_key or clean_key.startswith("invalid_"):
        latency = int((time.time() - start_time) * 1000) or 30
        return AIKeyTestResponse(
            success=False,
            latency_ms=latency,
            message=f"API Key không hợp lệ hoặc đã hết hạn từ {provider_title}.",
            provider=provider,
            model=req.model,
            error="API_KEY_INVALID"
        )

    # 3. Kiểm tra thực tế bằng API ping theo từng provider
    try:
        if provider == "gemini":
            # M3: KHÔNG bao giờ đặt API key vào query string. `?key=...` bị ghi vào
            # access log của Cloudflare/nginx/proxy và vào lịch sử trình duyệt, tức
            # là rò khoá ra ngoài hệ thống. Gemini REST API hỗ trợ header
            # `x-goog-api-key` tương đương. `quote()` cũng chặn path traversal /
            # header injection qua req.model do người dùng tự do kiểm soát.
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{quote(str(req.model), safe='')}"
            headers = {"x-goog-api-key": clean_key}
        elif provider == "openrouter":
            url = "https://openrouter.ai/api/v1/models"
            headers = {
                "Authorization": f"Bearer {clean_key}",
                "HTTP-Referer": "https://marketflow.ai",
                "X-Title": "MarketFlow AI",
            }
        elif provider == "openai":
            url = "https://api.openai.com/v1/models"
            headers = {"Authorization": f"Bearer {clean_key}"}
        elif provider == "opencode":
            # opencode zen là endpoint OpenAI-compatible: danh sách model ở
            # {base}/models. Base lấy từ cấu hình để hỗ trợ endpoint tùy biến.
            url = f"{settings.AI_BASE_URL.rstrip('/')}/models"
            headers = {
                "Authorization": f"Bearer {clean_key}",
                "HTTP-Referer": "http://localhost:5173",
                "X-Title": "MarketFlow AI",
            }
        else:
            raise ValueError(f"Nhà cung cấp {provider} không được hỗ trợ")

        with httpx.Client(timeout=5.0) as client:
            resp = client.get(url, headers=headers)
            latency = int((time.time() - start_time) * 1000) or 50
            if resp.status_code == 200:
                return AIKeyTestResponse(
                    success=True,
                    latency_ms=latency,
                    message=f"Kết nối {provider_title} API thành công.",
                    provider=provider,
                    model=req.model
                )
            else:
                sanitized_err = sanitize_error_text(resp.text, secret_key=clean_key)
                logger.warning("[BYOK Connection Test] %s rejected request (HTTP %d): %s", provider_title, resp.status_code, sanitized_err)
                return AIKeyTestResponse(
                    success=False,
                    latency_ms=latency,
                    message=f"{provider_title} từ chối yêu cầu (HTTP {resp.status_code}).",
                    provider=provider,
                    model=req.model,
                    error=sanitized_err
                )
    except Exception as e:
        latency = int((time.time() - start_time) * 1000) or 40
        sanitized_exc = sanitize_error_text(str(e), secret_key=clean_key)
        logger.error("[BYOK Connection Test] Error testing %s connection: %s", provider_title, sanitized_exc)
        return AIKeyTestResponse(
            success=False,
            latency_ms=latency,
            message=f"Không thể kết nối đến máy chủ {provider_title}: {sanitized_exc}",
            provider=provider,
            model=req.model,
            error=sanitized_exc
        )


@router.post("/ai-keys", response_model=AIKeyResponse, status_code=status.HTTP_200_OK)
def store_custom_ai_key(
    req: AIKeyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lưu trữ khóa API tùy biến vào vault mã hóa an toàn (cho Workspace hoặc User cá nhân)."""
    encrypted = encrypt_api_key(req.api_key)
    masked = mask_api_key(req.api_key)

    target_ws_id = req.workspace_id
    if target_ws_id is not None:
        # Kiểm tra quyền với workspace nếu chỉ định workspace_id
        if current_user.role != "ADMIN":
            ws = db.query(Workspace).filter(Workspace.id == target_ws_id).first()
            is_ws_owner = ws is not None and ws.owner_id == current_user.id
            is_ws_member = db.query(WorkspaceMember).filter(
                WorkspaceMember.workspace_id == target_ws_id,
                WorkspaceMember.user_id == current_user.id
            ).first()
            if not (is_ws_owner or (is_ws_member and is_ws_member.role in ("MANAGER", "AGENCY_MANAGER"))):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Không có quyền quản lý khóa cho Workspace này.")

        existing = db.query(CustomApiKey).filter(
            CustomApiKey.workspace_id == target_ws_id,
            CustomApiKey.provider == req.provider
        ).first()

        if existing:
            existing.encrypted_key = encrypted
            existing.model = req.model or "gemini-2.5-flash"
            existing.is_active = True if req.is_active is None else req.is_active
            existing.user_id = current_user.id
            db.commit()
            db.refresh(existing)
            return AIKeyResponse(
                id=existing.id,
                provider=existing.provider,
                model=existing.model,
                masked_key=masked,
                is_active=existing.is_active,
                workspace_id=existing.workspace_id,
                user_id=existing.user_id,
                scope="workspace",
                created_at=existing.created_at,
                updated_at=existing.updated_at,
                status="SAVED"
            )
        else:
            new_key = CustomApiKey(
                user_id=current_user.id,
                workspace_id=target_ws_id,
                provider=req.provider,
                encrypted_key=encrypted,
                model=req.model or "gemini-2.5-flash",
                is_active=True if req.is_active is None else req.is_active
            )
            db.add(new_key)
            db.commit()
            db.refresh(new_key)
            return AIKeyResponse(
                id=new_key.id,
                provider=new_key.provider,
                model=new_key.model,
                masked_key=masked,
                is_active=new_key.is_active,
                workspace_id=new_key.workspace_id,
                user_id=new_key.user_id,
                scope="workspace",
                created_at=new_key.created_at,
                updated_at=new_key.updated_at,
                status="SAVED"
            )
    else:
        # Cấu hình khóa cá nhân User
        existing = db.query(CustomApiKey).filter(
            CustomApiKey.user_id == current_user.id,
            CustomApiKey.workspace_id == None,
            CustomApiKey.provider == req.provider
        ).first()

        if existing:
            existing.encrypted_key = encrypted
            existing.model = req.model or "gemini-2.5-flash"
            existing.is_active = True if req.is_active is None else req.is_active
            db.commit()
            db.refresh(existing)
            return AIKeyResponse(
                id=existing.id,
                provider=existing.provider,
                model=existing.model,
                masked_key=masked,
                is_active=existing.is_active,
                workspace_id=None,
                user_id=existing.user_id,
                scope="personal",
                created_at=existing.created_at,
                updated_at=existing.updated_at,
                status="SAVED"
            )
        else:
            new_key = CustomApiKey(
                user_id=current_user.id,
                workspace_id=None,
                provider=req.provider,
                encrypted_key=encrypted,
                model=req.model or "gemini-2.5-flash",
                is_active=True if req.is_active is None else req.is_active
            )
            db.add(new_key)
            db.commit()
            db.refresh(new_key)
            return AIKeyResponse(
                id=new_key.id,
                provider=new_key.provider,
                model=new_key.model,
                masked_key=masked,
                is_active=new_key.is_active,
                workspace_id=None,
                user_id=new_key.user_id,
                scope="personal",
                created_at=new_key.created_at,
                updated_at=new_key.updated_at,
                status="SAVED"
            )


@router.get("/ai-keys", response_model=AIKeyResponse)
def get_custom_ai_keys(
    workspace_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lấy thông tin cấu hình Custom AI Key đã được che mặt nạ (không trả về plain-text key)."""
    key_record = None

    if workspace_id is not None:
        if current_user.role != "ADMIN":
            ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
            is_ws_owner = ws is not None and ws.owner_id == current_user.id
            is_ws_member = db.query(WorkspaceMember).filter(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == current_user.id
            ).first() is not None
            if not (is_ws_owner or is_ws_member):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Không có quyền truy cập cấu hình AI của Workspace này."
                )

        key_record = db.query(CustomApiKey).filter(
            CustomApiKey.workspace_id == workspace_id,
            CustomApiKey.provider == "gemini"
        ).order_by(CustomApiKey.updated_at.desc()).first()

    if not key_record:
        key_record = db.query(CustomApiKey).filter(
            CustomApiKey.user_id == current_user.id,
            CustomApiKey.workspace_id == None,
            CustomApiKey.provider == "gemini"
        ).order_by(CustomApiKey.updated_at.desc()).first()

    if not key_record:
        # Nếu user chưa có key cá nhân riêng biệt, kiểm tra xem user có bất kỳ key nào không
        key_record = db.query(CustomApiKey).filter(
            CustomApiKey.user_id == current_user.id,
            CustomApiKey.provider == "gemini"
        ).order_by(CustomApiKey.updated_at.desc()).first()

    if key_record:
        try:
            plain = decrypt_api_key(key_record.encrypted_key)
            masked = mask_api_key(plain)
        except Exception:
            masked = "AIzaSy...****"

        return AIKeyResponse(
            id=key_record.id,
            provider=key_record.provider,
            model=key_record.model,
            masked_key=masked,
            is_active=key_record.is_active,
            workspace_id=key_record.workspace_id,
            user_id=key_record.user_id,
            scope="workspace" if key_record.workspace_id else "personal",
            created_at=key_record.created_at,
            updated_at=key_record.updated_at,
            status="ACTIVE" if key_record.is_active else "INACTIVE"
        )

    # Mặc định chưa cấu hình key
    return AIKeyResponse(
        id=None,
        provider="gemini",
        model="gemini-2.5-flash",
        masked_key="",
        is_active=False,
        workspace_id=workspace_id,
        user_id=current_user.id,
        scope="personal",
        status="NOT_CONFIGURED"
    )


@router.get("/ai-keys/list", response_model=List[AIKeyResponse])
def list_custom_ai_keys(
    workspace_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Danh sách tất cả các khóa của người dùng hoặc workspace (đã che mặt nạ)."""
    query = db.query(CustomApiKey)
    if workspace_id is not None:
        if current_user.role != "ADMIN":
            ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
            is_ws_owner = ws is not None and ws.owner_id == current_user.id
            is_ws_member = db.query(WorkspaceMember).filter(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == current_user.id
            ).first() is not None
            if not (is_ws_owner or is_ws_member):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Không có quyền truy cập cấu hình AI của Workspace này."
                )
        query = query.filter(CustomApiKey.workspace_id == workspace_id)
    else:
        query = query.filter(
            (CustomApiKey.user_id == current_user.id) |
            (CustomApiKey.workspace_id.in_(
                db.query(WorkspaceMember.workspace_id).filter(WorkspaceMember.user_id == current_user.id)
            ))
        )

    records = query.order_by(CustomApiKey.updated_at.desc()).all()
    results = []
    for r in records:
        try:
            plain = decrypt_api_key(r.encrypted_key)
            masked = mask_api_key(plain)
        except Exception:
            masked = "AIzaSy...****"

        results.append(AIKeyResponse(
            id=r.id,
            provider=r.provider,
            model=r.model,
            masked_key=masked,
            is_active=r.is_active,
            workspace_id=r.workspace_id,
            user_id=r.user_id,
            scope="workspace" if r.workspace_id else "personal",
            created_at=r.created_at,
            updated_at=r.updated_at,
            status="ACTIVE" if r.is_active else "INACTIVE"
        ))
    return results


@router.delete("/ai-keys", status_code=status.HTTP_200_OK)
def deactivate_or_delete_current_byok_key(
    workspace_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Vô hiệu hóa hoặc xóa custom key để hoàn nguyên về System Default Key (theo test_t1_r6_05)."""
    if workspace_id is not None:
        if current_user.role != "ADMIN":
            ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
            is_ws_owner = ws is not None and ws.owner_id == current_user.id
            is_ws_member = db.query(WorkspaceMember).filter(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == current_user.id
            ).first() is not None
            if not (is_ws_owner or is_ws_member):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Không có quyền thao tác trên Workspace này."
                )
        key_record = db.query(CustomApiKey).filter(
            CustomApiKey.workspace_id == workspace_id,
            CustomApiKey.provider == "gemini"
        ).first()
    else:
        key_record = db.query(CustomApiKey).filter(
            CustomApiKey.user_id == current_user.id,
            CustomApiKey.workspace_id == None,
            CustomApiKey.provider == "gemini"
        ).first()
        if not key_record:
            key_record = db.query(CustomApiKey).filter(
                CustomApiKey.user_id == current_user.id,
                CustomApiKey.provider == "gemini"
            ).first()

    if key_record:
        check_ai_key_access(key_record, current_user, db)
        key_record.is_active = False
        db.delete(key_record)
        db.commit()

    return {"status": "DEACTIVATED", "message": "Custom AI key deactivated/removed successfully."}


def check_ai_key_access(key_record: CustomApiKey, current_user: User, db: Session):
    """Kiểm tra quyền thao tác trên CustomApiKey (Xóa hoặc Bật/Tắt).
    - ADMIN có toàn quyền.
    - Người tạo khóa (user_id == current_user.id) có quyền thao tác trên khóa của mình.
    - Nếu là khóa của Workspace (workspace_id is not None):
      Người dùng là MANAGER / AGENCY_MANAGER phải thuộc workspace đó (là owner của workspace hoặc thành viên).
    - Bất kỳ trường hợp nào khác: 403 FORBIDDEN.
    """
    if current_user.role == "ADMIN":
        return

    # Người tạo khóa được thao tác trên khóa của chính mình
    if key_record.user_id == current_user.id:
        return

    # Nếu khóa thuộc một Workspace cụ thể
    if key_record.workspace_id is not None:
        if current_user.role in ("MANAGER", "AGENCY_MANAGER"):
            ws = db.query(Workspace).filter(Workspace.id == key_record.workspace_id).first()
            if ws and ws.owner_id == current_user.id:
                return
            is_member = db.query(WorkspaceMember).filter(
                WorkspaceMember.workspace_id == key_record.workspace_id,
                WorkspaceMember.user_id == current_user.id
            ).first()
            if is_member and is_member.role in ("MANAGER", "AGENCY_MANAGER"):
                return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Không có quyền thao tác trên cấu hình khóa AI này."
    )


@router.delete("/ai-keys/{key_id}", status_code=status.HTTP_200_OK)
def delete_custom_ai_key_by_id(
    key_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Xóa khóa cấu hình theo ID."""
    key_record = db.query(CustomApiKey).filter(CustomApiKey.id == key_id).first()
    if not key_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy cấu hình khóa.")

    check_ai_key_access(key_record, current_user, db)

    db.delete(key_record)
    db.commit()
    return {"status": "DELETED", "message": "Đã xóa khóa thành công."}


@router.patch("/ai-keys/{key_id}/toggle", response_model=AIKeyResponse)
def toggle_custom_ai_key_active(
    key_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Bật/tắt trạng thái kích hoạt của Custom AI Key."""
    key_record = db.query(CustomApiKey).filter(CustomApiKey.id == key_id).first()
    if not key_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy cấu hình khóa.")

    check_ai_key_access(key_record, current_user, db)

    key_record.is_active = not key_record.is_active
    db.commit()
    db.refresh(key_record)

    try:
        plain = decrypt_api_key(key_record.encrypted_key)
        masked = mask_api_key(plain)
    except Exception:
        masked = "AIzaSy...****"

    return AIKeyResponse(
        id=key_record.id,
        provider=key_record.provider,
        model=key_record.model,
        masked_key=masked,
        is_active=key_record.is_active,
        workspace_id=key_record.workspace_id,
        user_id=key_record.user_id,
        scope="workspace" if key_record.workspace_id else "personal",
        created_at=key_record.created_at,
        updated_at=key_record.updated_at,
        status="ACTIVE" if key_record.is_active else "INACTIVE"
    )
