"""Campaign lifecycle rules (state machine).

Statuses (matches DB CHECK chk_campaign_status):
  DRAFT | PLANNED | ACTIVE | PAUSED | COMPLETED | ARCHIVED

Rules:
- Transition phải nằm trong ALLOWED_TRANSITIONS[from] (kể cả same-status = no-op).
- ARCHIVED là soft-delete; chỉ ADMIN/manager restore được về trạng thái trước đó
  (đơn giản hoá: ARCHIVED → DRAFT hoặc PLANNED; không cho ACTIVE trực tiếp).
- Create chỉ nhận DRAFT / PLANNED / ACTIVE — PAUSED/COMPLETED/ARCHIVED vô nghĩa
  khi mới tạo.
"""

from __future__ import annotations

from typing import FrozenSet, Iterable, Mapping, Optional

from fastapi import HTTPException, status

CAMPAIGN_STATUSES = frozenset(
    {"DRAFT", "PLANNED", "ACTIVE", "PAUSED", "COMPLETED", "ARCHIVED"}
)

CREATE_ALLOWED_STATUSES = frozenset({"DRAFT", "PLANNED", "ACTIVE"})

# from → allowed next statuses (includes self for no-op update)
ALLOWED_TRANSITIONS: Mapping[str, FrozenSet[str]] = {
    "DRAFT": frozenset({"DRAFT", "PLANNED", "ACTIVE", "ARCHIVED"}),
    "PLANNED": frozenset({"PLANNED", "DRAFT", "ACTIVE", "PAUSED", "ARCHIVED"}),
    "ACTIVE": frozenset({"ACTIVE", "PAUSED", "COMPLETED", "ARCHIVED"}),
    "PAUSED": frozenset({"PAUSED", "ACTIVE", "PLANNED", "COMPLETED", "ARCHIVED"}),
    "COMPLETED": frozenset({"COMPLETED", "ARCHIVED", "ACTIVE"}),
    "ARCHIVED": frozenset({"ARCHIVED", "DRAFT", "PLANNED"}),
}

# Trạng thái ẩn khỏi list mặc định (soft-delete / archive)
HIDDEN_FROM_DEFAULT_LIST = frozenset({"ARCHIVED"})


def normalize_status(raw: Optional[str]) -> str:
    return (raw or "DRAFT").strip().upper()


def is_valid_status(raw: Optional[str]) -> bool:
    return normalize_status(raw) in CAMPAIGN_STATUSES


def assert_create_status(raw: Optional[str]) -> str:
    value = normalize_status(raw)
    if value not in CREATE_ALLOWED_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Trạng thái khởi tạo không hợp lệ: '{value}'. "
                f"Chỉ nhận: {', '.join(sorted(CREATE_ALLOWED_STATUSES))}."
            ),
        )
    return value


def assert_transition(current: Optional[str], new: Optional[str]) -> str:
    """Validate + trả về status mới chuẩn hoá. No-op nếu new is None."""
    if new is None:
        return normalize_status(current)
    current_n = normalize_status(current)
    new_n = normalize_status(new)
    if new_n not in CAMPAIGN_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Trạng thái '{new_n}' không hợp lệ.",
        )
    allowed = ALLOWED_TRANSITIONS.get(current_n, frozenset())
    if new_n not in allowed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Không thể chuyển trạng thái '{current_n}' → '{new_n}'. "
                f"Chuyển tiếp hợp lệ: {', '.join(sorted(allowed))}."
            ),
        )
    return new_n


def compute_progress_pct(completed_tasks: int, total_tasks: int) -> Optional[int]:
    """% hoàn thành theo task. None khi chưa có task (không bịa số)."""
    if total_tasks <= 0:
        return None
    return max(0, min(100, int(round(100.0 * completed_tasks / total_tasks))))
