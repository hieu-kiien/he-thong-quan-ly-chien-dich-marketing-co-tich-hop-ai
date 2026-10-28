"""Nghiệp vụ xác nhận / từ chối đề xuất của Trợ lý AI (AiAction)."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.assistant.tools import (
    ProposeCampaignArgs,
    ProposeCampaignUpdateArgs,
    ProposeContentDraftsArgs,
    ProposeMetricsArgs,
    ProposeScheduleArgs,
)
from app.core.errors import (
    BadRequest,
    Conflict,
    DomainError,
    NotFound,
    PermissionDenied,
    ValidationFailed,
)
from app.core.timeutil import now_utc
from app.models.ai import AiAction, AiThread
from app.models.enums import AiActionStatus, ContentOrigin, MetricSource
from app.models.metric import Metric
from app.models.user import User
from app.schemas.campaign import CampaignChannelIn, CampaignCreate, CampaignUpdate
from app.schemas.content import ContentCreate
from app.schemas.metric import MetricIn
from app.schemas.schedule import ScheduleCreate
from app.services import (
    campaign_service,
    channel_service,
    content_service,
    metric_service,
    schedule_service,
)


def get_action_orm(db: Session, action_id: int) -> AiAction:
    action = db.get(AiAction, action_id)
    if action is None:
        raise NotFound("Không tìm thấy đề xuất thao tác")
    return action


def list_actions(
    db: Session,
    user: User,
    thread_id: int | None = None,
    status: AiActionStatus | None = None,
) -> list[AiAction]:
    # Phiên chat là riêng tư của từng người dùng (kể cả Quản lý) — chỉ thấy đề xuất của chính mình.
    stmt = select(AiAction).where(AiAction.user_id == user.id)
    if thread_id is not None:
        stmt = stmt.where(AiAction.thread_id == thread_id)
    if status is not None:
        stmt = stmt.where(AiAction.status == status)
    stmt = stmt.order_by(AiAction.id.desc())
    return list(db.execute(stmt).scalars())


def confirm(
    db: Session,
    user: User,
    action_id: int,
    args_override: dict[str, Any] | None = None,
) -> AiAction:
    # Khoá dòng (PostgreSQL) để hai lần bấm "Xác nhận" đồng thời không thực thi hai lần.
    action = db.execute(
        select(AiAction).where(AiAction.id == action_id).with_for_update()
    ).scalar_one_or_none()
    if action is None:
        raise NotFound("Không tìm thấy đề xuất thao tác")

    # 1. Ownership & state checks — chỉ chủ phiên mới được xác nhận (CONTRACT §4/§5)
    if action.user_id != user.id:
        raise PermissionDenied("Bạn không có quyền xác nhận đề xuất của người dùng khác")
    if action.status != AiActionStatus.PROPOSED:
        raise Conflict(
            f"Đề xuất đang ở trạng thái '{action.status.value}', chỉ có thể xác nhận khi ở trạng thái 'PROPOSED'",
            code="ACTION_NOT_PROPOSED",
        )

    # 2. Merge args
    merged_args = dict(action.args_json)
    if args_override:
        merged_args.update(args_override)

    try:
        result_json: dict[str, Any]
        tool_name = action.tool

        if tool_name == "propose_content_drafts":
            validated = ProposeContentDraftsArgs.model_validate(merged_args)
            pending_items: list[ContentCreate] = []
            draft_items: list[ContentCreate] = []
            thread_obj = db.get(AiThread, action.thread_id) if action.thread_id else None
            thread_cid = thread_obj.campaign_id if thread_obj else None
            for it in validated.items:
                resolved_cid = it.campaign_id or validated.campaign_id or thread_cid
                if not resolved_cid:
                    raise ValidationFailed(fields={"campaign_id": "Thiếu ID chiến dịch (campaign_id)"})
                ch = channel_service.resolve_channel(db, None, it.channel_code)
                c_in = ContentCreate(
                    campaign_id=resolved_cid,
                    channel_id=ch.id,
                    content_type=it.content_type,
                    title=it.title,
                    body=it.body,
                    cta=it.cta,
                )
                if (it.status or "PENDING_REVIEW").upper() == "DRAFT":
                    draft_items.append(c_in)
                else:
                    pending_items.append(c_in)

            created_contents = []
            if pending_items:
                created_contents.extend(
                    content_service.create_contents(
                        db,
                        user,
                        pending_items,
                        origin=ContentOrigin.AI,
                        ai_message_id=action.message_id,
                        submit=True,
                    )
                )
            if draft_items:
                created_contents.extend(
                    content_service.create_contents(
                        db,
                        user,
                        draft_items,
                        origin=ContentOrigin.AI,
                        ai_message_id=action.message_id,
                        submit=False,
                    )
                )

            result_json = {
                "contents": [
                    {
                        "id": c.id,
                        "link": f"/contents/{c.id}",
                        "status": c.status.value,
                    }
                    for c in created_contents
                ]
            }

        elif tool_name == "propose_campaign":
            c_args = ProposeCampaignArgs.model_validate(merged_args)
            channel_links: list[CampaignChannelIn] = []
            for ch_item in c_args.channels:
                ch = channel_service.resolve_channel(db, None, ch_item.channel_code)
                channel_links.append(
                    CampaignChannelIn(channel_id=ch.id, planned_budget=ch_item.planned_budget)
                )
            camp_create = CampaignCreate(
                name=c_args.name,
                goal=c_args.goal,
                objective=c_args.objective,
                target_audience=c_args.target_audience,
                product=c_args.product,
                key_message=c_args.key_message,
                start_date=c_args.start_date,
                end_date=c_args.end_date,
                budget=c_args.budget,
                channels=channel_links,
            )
            created_camp = campaign_service.create_campaign(db, user, camp_create)
            result_json = {
                "campaign_id": created_camp.id,
                "link": f"/campaigns/{created_camp.id}",
            }

        elif tool_name == "propose_campaign_update":
            u_args = ProposeCampaignUpdateArgs.model_validate(merged_args)
            channel_links_up: list[CampaignChannelIn] | None = None
            if u_args.channels is not None:
                channel_links_up = []
                for ch_item in u_args.channels:
                    ch = channel_service.resolve_channel(db, None, ch_item.channel_code)
                    channel_links_up.append(
                        CampaignChannelIn(channel_id=ch.id, planned_budget=ch_item.planned_budget)
                    )
            camp_update = CampaignUpdate(
                name=u_args.name,
                goal=u_args.goal,
                objective=u_args.objective,
                target_audience=u_args.target_audience,
                product=u_args.product,
                key_message=u_args.key_message,
                start_date=u_args.start_date,
                end_date=u_args.end_date,
                budget=u_args.budget,
                status=u_args.status,
                channels=channel_links_up,
            )
            updated_camp = campaign_service.update_campaign(db, user, u_args.campaign_id, camp_update)
            result_json = {
                "campaign_id": updated_camp.id,
                "link": f"/campaigns/{updated_camp.id}",
            }

        elif tool_name == "propose_schedule":
            s_args = ProposeScheduleArgs.model_validate(merged_args)
            sched_create = ScheduleCreate(
                content_id=s_args.content_id,
                scheduled_at=s_args.scheduled_at,
                note=s_args.note,
            )
            created_sched = schedule_service.create_schedule(db, user, sched_create)
            result_json = {
                "schedule_id": created_sched.id,
                "link": "/calendar",
            }

        elif tool_name == "propose_metrics":
            m_args = ProposeMetricsArgs.model_validate(merged_args)
            metric_ids = []
            inserted_count = 0
            updated_count = 0
            campaign_id = m_args.rows[0].campaign_id if m_args.rows else 0

            # Kiểm tra TOÀN BỘ dòng trước khi ghi dòng nào (mỗi upsert tự commit nên không thể rollback)
            for row in m_args.rows:
                metric_service.validate_metric_counts(row.views, row.clicks, row.conversions, row.cost)
                campaign_service.find_campaign_for_reference(db, row.campaign_id, field="campaign_id")
                channel_service.resolve_channel(db, None, row.channel_code, field="channel_code")

            for row in m_args.rows:
                metric_in = MetricIn(
                    campaign_id=row.campaign_id,
                    channel_code=row.channel_code,
                    metric_date=row.metric_date,
                    views=row.views,
                    clicks=row.clicks,
                    conversions=row.conversions,
                    cost=row.cost,
                )
                ch = channel_service.resolve_channel(db, None, row.channel_code)
                existing = db.execute(
                    select(Metric.id).where(
                        Metric.campaign_id == row.campaign_id,
                        Metric.channel_id == ch.id,
                        Metric.metric_date == row.metric_date,
                    )
                ).scalar_one_or_none()
                if existing:
                    updated_count += 1
                else:
                    inserted_count += 1

                m = metric_service.upsert_metric(db, user, metric_in, source=MetricSource.MANUAL)
                metric_ids.append(m.id)

            result_json = {
                "inserted": inserted_count,
                "updated": updated_count,
                "metric_ids": metric_ids,
                "link": f"/campaigns/{campaign_id}",
            }

        else:
            raise ValidationFailed(fields={"tool": f"Không hỗ trợ thực thi thao tác '{tool_name}'"})

        action.status = AiActionStatus.EXECUTED
        action.result_json = result_json
        action.executed_at = now_utc()
        action.error = None
        db.commit()
        db.refresh(action)
        return action

    except (DomainError, PydanticValidationError) as exc:
        db.rollback()
        domain_exc: DomainError
        if isinstance(exc, PydanticValidationError):
            fields = {".".join(str(p) for p in e["loc"]) or "args": e["msg"] for e in exc.errors()[:5]}
            domain_exc = ValidationFailed(fields=fields)
        else:
            domain_exc = exc
        action = db.get(AiAction, action_id)
        if action is not None:
            action.error = domain_exc.message
            # Lỗi do dữ liệu/nghiệp vụ có thể sửa được (ví dụ gõ sai ngày): giữ PROPOSED để người dùng
            # chỉnh lại rồi xác nhận lần nữa. Lỗi quyền/không tồn tại thì không thể thành công → FAILED.
            if not isinstance(domain_exc, ValidationFailed | Conflict | BadRequest):
                action.status = AiActionStatus.FAILED
            db.commit()
        if domain_exc is exc:
            raise
        raise domain_exc from exc
    except Exception as exc:
        db.rollback()
        action = db.get(AiAction, action_id)
        if action is not None:
            action.status = AiActionStatus.FAILED
            action.error = getattr(exc, "message", str(exc))
            db.commit()
        raise


def reject(db: Session, user: User, action_id: int) -> AiAction:
    action = get_action_orm(db, action_id)
    if action.user_id != user.id:
        raise PermissionDenied("Bạn không có quyền từ chối đề xuất của người khác")
    if action.status != AiActionStatus.PROPOSED:
        raise Conflict(
            f"Đề xuất đang ở trạng thái '{action.status.value}', chỉ có thể từ chối khi ở trạng thái 'PROPOSED'",
            code="ACTION_NOT_PROPOSED",
        )
    action.status = AiActionStatus.REJECTED
    db.commit()
    db.refresh(action)
    return action
