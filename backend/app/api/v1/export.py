"""Xuất dữ liệu toàn hệ thống (chỉ ADMIN).

Mục đích: cứu hộ dữ liệu khi nhà cung cấp database (Render Free) xoá instance,
hoặc khi cần chuyển sang nhà cung cấp khác.

QUY TẮC AN TOÀN: mọi cột chứa bí mật đều bị loại khỏi payload. File export
KHÔNG BAO GIỜ được dùng để khôi phục mật khẩu hoặc API key — sau khi chuyển
sang DB mới, mật khẩu phải được đặt lại qua luồng bình thường.
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import Base, get_db
from app.core.security import get_current_user
from app.models.entities import User, utc_now

router = APIRouter()

# Tên cột bị loại khỏi export. So khớp theo tên cột ở mọi bảng.
SENSITIVE_COLUMNS = {
    "password_hash",
    "encrypted_key",
    "api_key",
    "secret",
    "token",
    "access_token",
    "refresh_token",
}


def _is_sensitive(column_name: str) -> bool:
    name = column_name.lower()
    if name in SENSITIVE_COLUMNS:
        return True
    # Bắt các biến thể như `client_secret`, `ai_api_key`, `session_token`.
    return any(name.endswith(f"_{s}") or name.startswith(f"{s}_") for s in SENSITIVE_COLUMNS)


def _serialize(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, bytes):
        # Blob không phải dữ liệu nghiệp vụ, không export.
        return None
    return value


def _dump_table(db: Session, table) -> Dict[str, Any]:
    columns = [c for c in table.columns if not _is_sensitive(c.name)]
    rows = db.execute(table.select()).mappings().all()
    return {
        "columns": [c.name for c in columns],
        "row_count": len(rows),
        "rows": [{c.name: _serialize(row.get(c.name)) for c in columns} for row in rows],
    }


@router.get("/export/data")
def export_all_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Trả về toàn bộ dữ liệu mọi bảng dưới dạng JSON (không kèm bí mật)."""
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ ADMIN được xuất dữ liệu toàn hệ thống.",
        )

    tables = Base.metadata.sorted_tables
    data: Dict[str, Any] = {}
    total_rows = 0
    skipped: List[str] = []

    for table in tables:
        try:
            dumped = _dump_table(db, table)
        except Exception:
            # Bảng chưa tồn tại ở provider hiện tại (Postgres thiếu bảng SQLite).
            skipped.append(table.name)
            continue
        if dumped["row_count"]:
            data[table.name] = dumped
            total_rows += dumped["row_count"]

    return {
        "exported_by": current_user.email,
        "exported_at": utc_now().isoformat(),
        "total_rows": total_rows,
        "tables": data,
        "skipped_tables": skipped,
        "redacted_columns": sorted(SENSITIVE_COLUMNS),
    }
