"""API endpoints cho Trợ lý Marketing AI (CONTRACT §4 assistant group)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.assistant import actions_service, chat_service
from app.core.errors import Conflict, NotFound, PermissionDenied
from app.core.security import CurrentUser, DbSession
from app.models.ai import AiMessage, AiThread
from app.models.enums import AiActionStatus, AiMessageRole
from app.schemas.ai import (
    ActionConfirmIn,
    AiActionOut,
    AiMessageOut,
    AiThreadCreate,
    AiThreadOut,
    AiThreadUpdate,
    AssistantStatusOut,
    MessageSendIn,
)

router = APIRouter(prefix="/assistant", tags=["Trợ lý AI"])

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
    "Connection": "keep-alive",
}


# --- Threads ------------------------------------------------------------------

@router.get("/threads", response_model=list[AiThreadOut], summary="Danh sách phiên hội thoại")
def list_threads(
    user: CurrentUser,
    db: DbSession,
    q: Annotated[str | None, Query(description="Tìm kiếm theo tiêu đề phiên")] = None,
) -> list[AiThreadOut]:
    return chat_service.list_threads(db, user, q)


@router.post("/threads", response_model=AiThreadOut, status_code=status.HTTP_201_CREATED, summary="Tạo phiên mới")
def create_thread(
    data: AiThreadCreate,
    user: CurrentUser,
    db: DbSession,
) -> AiThreadOut:
    return chat_service.create_thread(db, user, data)


@router.get("/threads/{thread_id}", response_model=AiThreadOut, summary="Chi tiết phiên hội thoại")
def get_thread(
    thread_id: int,
    user: CurrentUser,
    db: DbSession,
) -> AiThreadOut:
    return chat_service.get_thread(db, user, thread_id)


@router.patch("/threads/{thread_id}", response_model=AiThreadOut, summary="Cập nhật phiên hội thoại")
def update_thread(
    thread_id: int,
    data: AiThreadUpdate,
    user: CurrentUser,
    db: DbSession,
) -> AiThreadOut:
    return chat_service.update_thread(db, user, thread_id, data)


@router.delete("/threads/{thread_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Xoá phiên hội thoại")
def delete_thread(
    thread_id: int,
    user: CurrentUser,
    db: DbSession,
) -> None:
    chat_service.delete_thread(db, user, thread_id)


@router.get("/threads/{thread_id}/messages", response_model=list[AiMessageOut], summary="Danh sách tin nhắn của phiên")
def list_messages(
    thread_id: int,
    user: CurrentUser,
    db: DbSession,
) -> list[AiMessageOut]:
    return chat_service.list_messages(db, user, thread_id)


# --- Stream Interaction -------------------------------------------------------

@router.post("/threads/{thread_id}/messages", summary="Gửi tin nhắn & nhận luồng SSE")
async def send_message(
    thread_id: int,
    data: MessageSendIn,
    user: CurrentUser,
    db: DbSession,
) -> StreamingResponse:
    # Xác thực quyền truy cập phiên trước khi stream
    chat_service.get_thread_orm(db, user, thread_id)
    if await chat_service.is_thread_busy(thread_id):
        raise Conflict("Phiên hội thoại đang có lượt xử lý chưa hoàn tất", code="THREAD_BUSY")

    stream = chat_service.run_turn_stream(
        user_id=user.id,
        thread_id=thread_id,
        content=data.content,
    )
    return StreamingResponse(stream, media_type="text/event-stream", headers=SSE_HEADERS)


@router.post("/threads/{thread_id}/stop", summary="Dừng lượt trả lời đang chạy")
async def stop_turn(
    thread_id: int,
    user: CurrentUser,
    db: DbSession,
) -> dict[str, Any]:
    return await chat_service.stop_thread(db, user, thread_id)


@router.post("/messages/{message_id}/regenerate", summary="Tạo lại phản hồi cho tin nhắn")
async def regenerate_message(
    message_id: int,
    user: CurrentUser,
    db: DbSession,
) -> StreamingResponse:
    msg = db.get(AiMessage, message_id)
    if not msg:
        raise NotFound("Không tìm thấy tin nhắn cần tạo lại")

    thread = db.get(AiThread, msg.thread_id)
    if not thread or (thread.user_id != user.id and not user.is_manager):
        raise PermissionDenied("Không có quyền truy cập phiên này")

    # Tìm tin nhắn user trước đó trong cùng thread
    prev_user_msg = db.execute(
        select(AiMessage)
        .where(
            AiMessage.thread_id == thread.id,
            AiMessage.role == AiMessageRole.USER,
            AiMessage.id <= msg.id,
        )
        .order_by(AiMessage.id.desc())
    ).scalars().first()

    if not prev_user_msg:
        raise NotFound("Không tìm thấy tin nhắn người dùng tương ứng để tạo lại")

    if await chat_service.is_thread_busy(thread.id):
        raise Conflict("Phiên hội thoại đang có lượt xử lý chưa hoàn tất", code="THREAD_BUSY")

    stream = chat_service.run_turn_stream(
        user_id=user.id,
        thread_id=thread.id,
        content=prev_user_msg.content,
    )
    return StreamingResponse(stream, media_type="text/event-stream", headers=SSE_HEADERS)


# --- Actions (Proposals) ------------------------------------------------------

@router.get("/actions", response_model=list[AiActionOut], summary="Danh sách đề xuất thao tác")
def list_actions(
    user: CurrentUser,
    db: DbSession,
    thread_id: Annotated[int | None, Query(description="Lọc theo id phiên hội thoại")] = None,
    status: Annotated[AiActionStatus | None, Query(description="Lọc theo trạng thái đề xuất")] = None,
) -> list[AiActionOut]:
    actions = actions_service.list_actions(db, user, thread_id=thread_id, status=status)
    return [AiActionOut.model_validate(a) for a in actions]


@router.post("/actions/{action_id}/confirm", response_model=AiActionOut, summary="Xác nhận thực thi đề xuất")
def confirm_action(
    action_id: int,
    user: CurrentUser,
    db: DbSession,
    data: ActionConfirmIn | None = None,
) -> AiActionOut:
    args_override = data.args if data else None
    action = actions_service.confirm(db, user, action_id, args_override)
    return AiActionOut.model_validate(action)


@router.post("/actions/{action_id}/reject", response_model=AiActionOut, summary="Từ chối đề xuất")
def reject_action(
    action_id: int,
    user: CurrentUser,
    db: DbSession,
) -> AiActionOut:
    action = actions_service.reject(db, user, action_id)
    return AiActionOut.model_validate(action)


# --- Trạng thái AI ------------------------------------------------------------

@router.get("/status", response_model=AssistantStatusOut, summary="Trạng thái dịch vụ Trợ lý AI")
async def get_assistant_status(
    user: CurrentUser,
) -> AssistantStatusOut:
    runner_health = await chat_service.default_runner.health()
    is_ok = bool(runner_health.get("ok", False))
    return AssistantStatusOut(
        available=is_ok,
        runner={
            "ok": is_ok,
            "version": runner_health.get("opencode_version"),
            "model": runner_health.get("model"),
        },
        last_error=runner_health.get("last_error") if not is_ok else None,
        queue_length=int(runner_health.get("queue_length", 0)),
    )
