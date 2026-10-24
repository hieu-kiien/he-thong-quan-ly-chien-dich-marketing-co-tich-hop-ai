"""Kênh truyền thông. Mọi người xem; chỉ MANAGER tạo/sửa/xoá."""

from __future__ import annotations

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from app.core.errors import Conflict, NotFound, PermissionDenied, ValidationFailed
from app.models import CampaignChannel, Channel, Content, Metric, User
from app.schemas.channel import ChannelCreate, ChannelOut, ChannelUpdate
from app.services.common import get_or_404


def _require_manager(user: User) -> None:
    if not user.is_manager:
        raise PermissionDenied("Chỉ Quản lý marketing được quản lý kênh")


def list_channels(db: Session, user: User, include_inactive: bool = False) -> list[ChannelOut]:
    stmt = select(Channel).order_by(Channel.id)
    if not include_inactive:
        stmt = stmt.where(Channel.is_active.is_(True))
    return [ChannelOut.model_validate(c) for c in db.execute(stmt).scalars()]


def get_channel(db: Session, user: User, channel_id: int) -> ChannelOut:
    return ChannelOut.model_validate(get_or_404(db, Channel, channel_id, "Không tìm thấy kênh"))


def find_by_code(db: Session, code: str) -> Channel | None:
    return db.execute(select(Channel).where(func.upper(Channel.code) == code.strip().upper())).scalar_one_or_none()


def resolve_channel(
    db: Session,
    channel_id: int | None,
    channel_code: str | None,
    *,
    field: str = "channel_id",
    require_active: bool = True,
) -> Channel:
    """Tìm kênh theo id hoặc mã (công cụ AI dùng mã). Lỗi → ValidationFailed với tên trường."""
    channel: Channel | None = None
    if channel_id is not None:
        channel = db.get(Channel, channel_id)
        if channel is None:
            raise ValidationFailed(fields={field: "Kênh không tồn tại"})
    elif channel_code:
        channel = find_by_code(db, channel_code)
        if channel is None:
            raise ValidationFailed(fields={field: f"Không có kênh mã '{channel_code}'"})
    else:
        raise ValidationFailed(fields={field: "Trường này là bắt buộc"})
    if require_active and not channel.is_active:
        raise ValidationFailed(fields={field: f"Kênh {channel.name} đang tắt"})
    return channel


def create_channel(db: Session, user: User, data: ChannelCreate) -> ChannelOut:
    _require_manager(user)
    if find_by_code(db, data.code) is not None:
        raise Conflict("Mã kênh đã tồn tại", code="CHANNEL_CODE_EXISTS", fields={"code": "Mã kênh đã tồn tại"})
    channel = Channel(code=data.code, name=data.name, format_rules=data.format_rules, is_active=data.is_active)
    db.add(channel)
    db.commit()
    db.refresh(channel)
    return ChannelOut.model_validate(channel)


def update_channel(db: Session, user: User, channel_id: int, data: ChannelUpdate) -> ChannelOut:
    _require_manager(user)
    channel = get_or_404(db, Channel, channel_id, "Không tìm thấy kênh")
    for field in ("name", "format_rules", "is_active"):
        value = getattr(data, field)
        if value is not None:
            setattr(channel, field, value)
    db.commit()
    db.refresh(channel)
    return ChannelOut.model_validate(channel)


def delete_channel(db: Session, user: User, channel_id: int) -> None:
    _require_manager(user)
    channel = db.get(Channel, channel_id)
    if channel is None:
        raise NotFound("Không tìm thấy kênh")
    in_use = db.execute(
        select(
            exists().where(CampaignChannel.channel_id == channel_id)
            | exists().where(Content.channel_id == channel_id)
            | exists().where(Metric.channel_id == channel_id)
        )
    ).scalar()
    if in_use:
        raise Conflict(
            "Kênh đã được dùng trong chiến dịch, nội dung hoặc số liệu. Hãy tắt kênh (is_active=false) thay vì xoá.",
            code="CHANNEL_IN_USE",
        )
    db.delete(channel)
    db.commit()
