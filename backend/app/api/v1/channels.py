"""Router kênh truyền thông."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.core.security import CurrentUser, DbSession, ManagerUser
from app.schemas.channel import ChannelCreate, ChannelOut, ChannelUpdate
from app.schemas.common import Message
from app.services import channel_service

router = APIRouter(prefix="/channels", tags=["Kênh truyền thông"])


@router.get("", response_model=list[ChannelOut])
def list_channels(user: CurrentUser, db: DbSession, include_inactive: bool = False) -> list[ChannelOut]:
    return channel_service.list_channels(db, user, include_inactive=include_inactive)


@router.get("/{channel_id}", response_model=ChannelOut)
def get_channel(channel_id: int, user: CurrentUser, db: DbSession) -> ChannelOut:
    return channel_service.get_channel(db, user, channel_id)


@router.post("", response_model=ChannelOut, status_code=status.HTTP_201_CREATED)
def create_channel(data: ChannelCreate, user: ManagerUser, db: DbSession) -> ChannelOut:
    return channel_service.create_channel(db, user, data)


@router.patch("/{channel_id}", response_model=ChannelOut)
def update_channel(channel_id: int, data: ChannelUpdate, user: ManagerUser, db: DbSession) -> ChannelOut:
    return channel_service.update_channel(db, user, channel_id, data)


@router.delete("/{channel_id}", response_model=Message)
def delete_channel(channel_id: int, user: ManagerUser, db: DbSession) -> Message:
    channel_service.delete_channel(db, user, channel_id)
    return Message(message="Đã xoá kênh thành công")
