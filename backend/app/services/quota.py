"""Hạn mức gói miễn phí theo workspace (free-tier product quota).

KHÁC `enforce_quota` Ở ĐÂY LÀ GÌ — ĐỪNG GỘP
------------------------------------------
`app/core/security.py::enforce_quota` là **rate limiter chống lạm dụng**: bộ đếm
trong bộ nhớ tiến trình, cửa sổ trượt, khoá theo chuỗi tự do. Nó chống việc gọi
liên tục và biến mất khi tiến trình restart, và bị nhân lên theo số worker.
Module này là **giới hạn sản phẩm**: đếm trong CSDL, bền qua restart, gắn với
workspace. Hai tầng độc lập, cả hai đều giữ nguyên.

VÌ SAO AI JOB ĐƯỢC TÍNH NGAY LÚC ENQUEUE, KHÔNG PHẢI LÚC HOÀN THÀNH
------------------------------------------------------------------
Vì "lượt tiêu" của một AI job chính là HÀNG TRONG BẢNG `ai_jobs`. Ta đếm chính
những hàng đó, không lưu bộ đếm riêng:

- Job được nhận (enqueue) -> có hàng -> đã tính 1 lượt. Người dùng biết ngay
  mình đã vượt, thay vì đợi vài phút rồi mới thấy job chết.
- Retry idempotent -> `find_by_idempotency_key` trả về job cũ, KHÔNG tạo hàng
  mới -> không tính lần hai. Đây là bảo đảm CẤU TRÚC chứ không phải bằng
  kỷ luật code: không có đường nào để trừ hai lần cùng một yêu cầu logic.
- Job hỏng/huỷ vẫn được tính, vì nó đã chiếm slot worker và đã gọi (hoặc đã cố
  gọi) LLM. Tính lúc hoàn thành sẽ cho phép dồn hàng trăm job rồi "trừ một lần".
- Restart tiến trình không xoá lịch sử tiêu — khác hẳn bộ đếm trong RAM.

CÁC HẠN MỨC CÒN LẠI LÀ "ĐỒNG HỒ"
--------------------------------
`campaigns`, `contents`, `workspace_members`, `schedules` là tài nguyên tích luỹ
nên dùng phép đo trực tiếp: đếm số dòng đang tồn tại của workspace và từ chối khi
đã chạm trần. Không cần bảng đếm riêng, nên không bao giờ lệch với dữ liệu thật.

CỬA SỔ 24 GIỜ TRƯỜT (KHÔNG PHẢI NGÀY LỊCH)
------------------------------------------
`ai_jobs_per_day` dùng cửa sổ trượt 24 giờ chứ không phải ngày lịch UTC. Lý do
cụ thể: múi giờ Việt Nam là UTC+7, nên "ngày UTC" cắt qua lúc 7h sáng giờ địa
phương — người dùng demo buổi sáng sẽ thấy hạn mức tự nhảy về 0 giữa buổi.
Cửa sổ trượt cũng cho `resets_at` chính xác: thời điểm job cũ nhất rơi khỏi
cửa sổ, tức là lúc đúng một lượt được hoàn lại.

ĐƯỜNG GHI ĐÈ CHO QUẢN TRỊ VIÊN
-----------------------------
Một admin khoá ngoài chính instance của mình thì không tự sửa được. Vì vậy có
hai đường ghi đè, đều được ghi log:
- `QUOTA_OVERRIDE_WORKSPACE_IDS`: danh sách id workspace được miễn trần.
- Người dùng vai trò ADMIN được miễn (khớp với mô hình "ADMIN có phạm vi toàn
  cục" đã có sẵn ở mọi endpoint khác của hệ thống).

CẢNH BÁO VỀ ĐỘ CHÍNH XÁC
------------------------
Giữa lúc đếm và lúc ghi có thể có hai request cùng vượt trần. Trên deployment
này (Render free, dưới 50 người dùng đồng thời) chấp nhận được và ghi rõ ở
đây; siết thành khoá ghi serializable là việc khác, và sẽ tốn thêm một round-trip
cho mọi lần tạo. Hạn mứng ở đây là đường phòng thủ, không phải hàng rào tài
chính — nên lệch một lượt khi có tranh chấp là chấp nhận được.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.entities import (
    AIJob,
    Campaign,
    MarketingContent,
    MarketingSchedule,
    Workspace,
    WorkspaceMember,
)

logger = logging.getLogger("marketflow.quota")

# ---------------------------------------------------------------------------
# Mã hạn mức. Đây là hợp đồng với frontend và với thông báo lỗi — đổi chuỗi ở
# đây là đổi hợp đồng, nên giữ nguyên.
# ---------------------------------------------------------------------------
LIMIT_AI_JOBS_PER_DAY = "ai_jobs_per_day"
LIMIT_CAMPAIGNS = "campaigns"
LIMIT_CONTENTS = "contents"
LIMIT_WORKSPACE_MEMBERS = "workspace_members"
LIMIT_SCHEDULES = "schedules"
LIMIT_WORKSPACES_PER_USER = "workspaces_per_user"

#: Thứ tự hiển thị trong `GET /workspaces/{id}/quota`.
ALL_LIMIT_CODES = (
    LIMIT_AI_JOBS_PER_DAY,
    LIMIT_CAMPAIGNS,
    LIMIT_CONTENTS,
    LIMIT_WORKSPACE_MEMBERS,
    LIMIT_SCHEDULES,
    LIMIT_WORKSPACES_PER_USER,
)

#: Cửa sổ trượt của `ai_jobs_per_day`.
AI_JOBS_WINDOW = timedelta(hours=24)

#: Nhãn tiếng Việt cho client (và cho thông báo lỗi).
LIMIT_LABELS = {
    LIMIT_AI_JOBS_PER_DAY: "AI job mỗi 24 giờ",
    LIMIT_CAMPAIGNS: "chiến dịch",
    LIMIT_CONTENTS: "bài nội dung",
    LIMIT_WORKSPACE_MEMBERS: "thành viên",
    LIMIT_SCHEDULES: "lịch đăng",
    LIMIT_WORKSPACES_PER_USER: "không gian làm việc",
}


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(value: Optional[datetime]) -> Optional[datetime]:
    """Gắn UTC cho datetime naive đọc ra từ CSDL (cột DateTime không khai báo tz)."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


@dataclass(frozen=True)
class QuotaSnapshot:
    """Trạng thái một hạn mức tại thời điểm đọc. Dùng để render UI đếm ngược."""

    limit_code: str
    used: int
    limit: int
    scope: str  # "workspace" | "user"
    label: str
    window: Optional[str] = None  # "24h" cho AI job, None cho đồng hồ tích luỹ
    resets_at: Optional[datetime] = None

    @property
    def remaining(self) -> int:
        return max(self.limit - self.used, 0)

    @property
    def exceeded(self) -> bool:
        return self.used >= self.limit

    def to_dict(self) -> Dict[str, Any]:
        return {
            "limit_code": self.limit_code,
            "label": self.label,
            "used": self.used,
            "limit": self.limit,
            "remaining": self.remaining,
            "exceeded": self.exceeded,
            "scope": self.scope,
            "window": self.window,
            "resets_at": self.resets_at.isoformat() if self.resets_at else None,
        }


# ---------------------------------------------------------------------------
# Đọc giá trị cấu hình
# ---------------------------------------------------------------------------
def _limits_from_settings() -> Dict[str, int]:
    from app.core.config import settings

    return {
        LIMIT_AI_JOBS_PER_DAY: int(settings.QUOTA_AI_JOBS_PER_DAY),
        LIMIT_CAMPAIGNS: int(settings.QUOTA_MAX_CAMPAIGNS),
        LIMIT_CONTENTS: int(settings.QUOTA_MAX_CONTENTS),
        LIMIT_WORKSPACE_MEMBERS: int(settings.QUOTA_MAX_WORKSPACE_MEMBERS),
        LIMIT_SCHEDULES: int(settings.QUOTA_MAX_SCHEDULES),
        LIMIT_WORKSPACES_PER_USER: int(settings.QUOTA_MAX_WORKSPACES_PER_USER),
    }


def _override_workspace_ids() -> frozenset:
    from app.core.config import settings

    raw = str(getattr(settings, "QUOTA_OVERRIDE_WORKSPACE_IDS", "") or "")
    ids = set()
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            ids.add(int(chunk))
        except ValueError:
            logger.warning(
                "[Quota] Bo qua muc khong phai so nguyen trong QUOTA_OVERRIDE_WORKSPACE_IDS: %r", chunk
            )
    return frozenset(ids)


def is_quota_exempt(user, workspace_id: Optional[int]) -> bool:
    """Người dùng/workspace này có được miễn hạn mứng không.

    Miễn trần luôn được GHI LOG. Một lớp phòng thủ bị bỏ qua trong im lặng thì
    không còn là lớp phòng thủ nữa — không ai biết nó đang tồn tại.
    """
    if user is not None and getattr(user, "role", None) == "ADMIN":
        logger.warning(
            "[Quota] Admin %s duoc MIEN han muc tren workspace_id=%s.",
            getattr(user, "email", "?"), workspace_id,
        )
        return True
    if workspace_id is not None and int(workspace_id) in _override_workspace_ids():
        logger.warning(
            "[Quota] Workspace %s duoc MIEN han muc qua QUOTA_OVERRIDE_WORKSPACE_IDS.", workspace_id
        )
        return True
    return False


# ---------------------------------------------------------------------------
# Đếm
# ---------------------------------------------------------------------------
def _count_window(db: Session, column, value: int, window_start: datetime) -> int:
    return int(
        db.execute(
            select(func.count()).select_from(AIJob).where(
                AIJob.workspace_id == value,
                AIJob.queued_at >= window_start,
            )
        ).scalar()
        or 0
    )


def _oldest_in_window(db: Session, workspace_id: int, window_start: datetime) -> Optional[datetime]:
    return as_utc(
        db.execute(
            select(func.min(AIJob.queued_at)).where(
                AIJob.workspace_id == workspace_id,
                AIJob.queued_at >= window_start,
            )
        ).scalar()
    )


def _count_rows(db: Session, model, workspace_id: int) -> int:
    return int(
        db.execute(
            select(func.count()).select_from(model).where(model.workspace_id == workspace_id)
        ).scalar()
        or 0
    )


def measure(
    db: Session,
    limit_code: str,
    *,
    workspace_id: Optional[int],
    user_id: Optional[int] = None,
    now: Optional[datetime] = None,
) -> QuotaSnapshot:
    """Đo lại một hạn mức. Hàm thuần (chỉ đọc), dùng cho cả lỗi lẫn endpoint báo cáo."""
    now = now or now_utc()
    limits = _limits_from_settings()
    if limit_code not in limits:
        # Ném ValueError chứ không để KeyInfo lọt ra: đây là lỗi lập trình, gọi
        # sai tên hạn mức, và phải lộ ra ngay ở test chứ không phải lúc chạy thật.
        raise ValueError(
            f"Mã hạn mức không hợp lệ: {limit_code!r}. Hợp lệ: {', '.join(sorted(limits))}"
        )
    limit = limits[limit_code]

    if limit_code == LIMIT_AI_JOBS_PER_DAY:
        window_start = now - AI_JOBS_WINDOW
        used = _count_window(db, AIJob.workspace_id, int(workspace_id), window_start)
        oldest = _oldest_in_window(db, int(workspace_id), window_start)
        # Cửa sổ trượt: một lượt được hoàn lại khi job cũ nhất rơi khỏi cửa sổ.
        resets_at = (oldest + AI_JOBS_WINDOW) if oldest is not None else None
        return QuotaSnapshot(
            limit_code=limit_code,
            used=used,
            limit=limit,
            scope="workspace",
            label=LIMIT_LABELS[limit_code],
            window="24h",
            resets_at=resets_at,
        )

    if limit_code == LIMIT_CAMPAIGNS:
        return _gauge(limit_code, limit, _count_rows(db, Campaign, int(workspace_id)))
    if limit_code == LIMIT_CONTENTS:
        return _gauge(limit_code, limit, _count_rows(db, MarketingContent, int(workspace_id)))
    if limit_code == LIMIT_SCHEDULES:
        # Lịch đăng không mang workspace_id: suy ra qua nội dung cha.
        used = int(
            db.execute(
                select(func.count())
                .select_from(MarketingSchedule)
                .join(MarketingContent, MarketingSchedule.content_id == MarketingContent.id)
                .where(MarketingContent.workspace_id == int(workspace_id))
            ).scalar()
            or 0
        )
        return _gauge(limit_code, limit, used)
    if limit_code == LIMIT_WORKSPACE_MEMBERS:
        return _gauge(
            limit_code, limit,
            int(
                db.execute(
                    select(func.count())
                    .select_from(WorkspaceMember)
                    .where(WorkspaceMember.workspace_id == int(workspace_id))
                ).scalar()
                or 0
            ),
        )
    if limit_code == LIMIT_WORKSPACES_PER_USER:
        used = int(
            db.execute(
                select(func.count())
                .select_from(Workspace)
                .where(Workspace.owner_id == int(user_id))
            ).scalar()
            or 0
        )
        return _gauge(limit_code, limit, used)

    raise ValueError(f"Mã hạn mức không hợp lệ: {limit_code!r}")


def _gauge(limit_code: str, limit: int, used: int) -> QuotaSnapshot:
    return QuotaSnapshot(
        limit_code=limit_code,
        used=used,
        limit=limit,
        scope="user" if limit_code == LIMIT_WORKSPACES_PER_USER else "workspace",
        label=LIMIT_LABELS[limit_code],
        window=None,
        resets_at=None,
    )


def snapshot_workspace(
    db: Session,
    *,
    workspace_id: int,
    user_id: Optional[int] = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Ảnh chụp mọi hạn mức liên quan tới workspace + người dùng (cho UI)."""
    items: List[Dict[str, Any]] = []
    for code in ALL_LIMIT_CODES:
        if code == LIMIT_WORKSPACES_PER_USER:
            if user_id is None:
                continue
            items.append(measure(db, code, workspace_id=workspace_id, user_id=user_id, now=now).to_dict())
            continue
        items.append(measure(db, code, workspace_id=workspace_id, user_id=user_id, now=now).to_dict())
    return {
        "workspace_id": workspace_id,
        "exempt": bool(_override_workspace_ids()) and int(workspace_id) in _override_workspace_ids(),
        "limits": items,
    }


# ---------------------------------------------------------------------------
# Thực thi
# ---------------------------------------------------------------------------
def quota_error_detail(
    snapshot: QuotaSnapshot,
    *,
    limit_code: str,
    pending: int = 1,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Thân lỗi máy-đọc-được cho client.

    Một 429 trần không nói cho người dùng biết vì sao bị chặn, đã dùng bao nhiêu,
    hay bao giờ hết hạn — đúng những thứ cần để quyết định có chờ hay đổi việc.
    """
    now = now or now_utc()
    limit = snapshot.limit
    used_after = snapshot.used + pending
    detail: Dict[str, Any] = {
        "error": "quota_exceeded",
        "limit_code": limit_code,
        "message": (
            f"Bạn đã dùng hết hạn mức {snapshot.label} của gói miễn phí "
            f"({snapshot.used}/{limit}). Hạn mức được tính theo không gian làm việc."
        ),
        "used": snapshot.used,
        "limit": limit,
        "remaining": 0,
        "requested": pending,
        "scope": snapshot.scope,
        "resets_at": snapshot.resets_at.isoformat() if snapshot.resets_at else None,
    }
    if snapshot.resets_at is None:
        # Đồng hồ tích luỹ không tự xoá: phải nói rõ để người dùng biết phải
        # xoá thứ gì thay vì chờ.
        detail["message"] = (
            f"Bạn đã dùng hết hạn mức {snapshot.label} của gói miễn phí "
            f"({snapshot.used}/{limit}). Hạn mức này KHÔNG tự đặt lại — "
            f"hãy xoá bản ghi cũ hoặc liên hệ quản trị viên để được nâng hạn mức."
        )
    else:
        seconds = max(int((snapshot.resets_at - now).total_seconds()), 0)
        detail["retry_after_seconds"] = seconds
        detail["retry_after"] = max(1, int(seconds // 60) + (1 if seconds % 60 else 0))
    detail["would_be_used"] = used_after
    return detail


def enforce(
    db: Session,
    limit_code: str,
    *,
    user,
    workspace_id: Optional[int] = None,
    user_id: Optional[int] = None,
    pending: int = 1,
    now: Optional[datetime] = None,
) -> QuotaSnapshot:
    """Kiểm tra hạn mứng, ném 429 có thân lỗi nếu vượt. Trả về snapshot khi đạt.

    `pending` là số lượt sắp tiêu (mặc định 1 cho một lần tạo). Cho phép kiểm tra
    nhiều lượt một lần để không phải đo lại cho từng bản ghi.
    """
    now = now or now_utc()
    if is_quota_exempt(user, workspace_id):
        # Trả snapshot vẫn đúng để UI hiển thị, chỉ không chặn.
        return measure(
            db, limit_code,
            workspace_id=workspace_id,
            user_id=user_id if user_id is not None else getattr(user, "id", None),
            now=now,
        )

    snapshot = measure(
        db, limit_code,
        workspace_id=workspace_id,
        user_id=user_id if user_id is not None else getattr(user, "id", None),
        now=now,
    )
    if snapshot.used + pending > snapshot.limit:
        detail = quota_error_detail(snapshot, limit_code=limit_code, pending=pending, now=now)
        logger.warning(
            "[Quota] Tu choi %s: limit_code=%s used=%s limit=%s workspace=%s user=%s",
            getattr(user, "email", "?"), limit_code, snapshot.used, snapshot.limit,
            workspace_id, getattr(user, "id", None),
        )
        headers = {}
        if detail.get("retry_after"):
            headers["Retry-After"] = str(detail["retry_after"])
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            headers=headers or None,
        )
    return snapshot