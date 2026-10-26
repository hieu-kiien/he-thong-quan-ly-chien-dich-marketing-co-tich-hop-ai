"""Khối [NGỮ CẢNH] gửi cho mô hình: dữ liệu thật theo quyền, lượt đầu đầy đủ, lượt sau gọn."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.assistant import chat_service
from app.core.timeutil import today_vn
from app.models import AiThread, BannedKeyword, Campaign, Channel, Metric, User
from app.models.enums import MetricSource
from app.schemas.ai import AiThreadUpdate


def _thread(db: Session, user: User, campaign: Campaign | None, session_id: str | None = None) -> AiThread:
    thread = AiThread(
        user_id=user.id,
        campaign_id=campaign.id if campaign else None,
        title="Phiên test",
        opencode_session_id=session_id,
    )
    db.add(thread)
    db.commit()
    db.refresh(thread)
    return thread


def test_first_turn_has_snapshot_without_invented_numbers(
    db: Session, marketer1_user: User, sample_campaign: Campaign
):
    db.add(BannedKeyword(keyword="cam kết 100%"))
    db.commit()
    thread = _thread(db, marketer1_user, sample_campaign)

    prompt = chat_service.build_prompt(db, marketer1_user, thread, "Tóm tắt hiệu quả")

    assert "[NGỮ CẢNH]" in prompt and prompt.rstrip().endswith("Tóm tắt hiệu quả")
    assert '"cam kết 100%"' in prompt
    assert sample_campaign.name in prompt and "Cold Brew Đóng Chai" in prompt
    assert "FACEBOOK (dự kiến 12.000.000 VND)" in prompt
    # Chưa nhập số liệu → nói rõ là chưa có, không có dòng số liệu nào
    assert "CHƯA CÓ dữ liệu hiệu quả" in prompt
    assert "views" not in prompt


def test_first_turn_includes_real_metrics_by_channel(
    db: Session, marketer1_user: User, sample_campaign: Campaign, test_channels: dict[str, Channel]
):
    db.add(Metric(
        campaign_id=sample_campaign.id, channel_id=test_channels["FACEBOOK"].id, metric_date=today_vn(),
        views=1000, clicks=50, conversions=5, cost=Decimal(500_000), source=MetricSource.MANUAL,
        entered_by=marketer1_user.id,
    ))
    db.commit()
    thread = _thread(db, marketer1_user, sample_campaign)

    prompt = chat_service.build_prompt(db, marketer1_user, thread, "Tóm tắt")

    assert "views 1000, clicks 50, chuyển đổi 5" in prompt
    assert "CTR 5.00%" in prompt
    assert "FACEBOOK: views 1000" in prompt


def test_later_turns_are_compact(db: Session, marketer1_user: User, sample_campaign: Campaign):
    thread = _thread(db, marketer1_user, sample_campaign, session_id="ses_existing")

    prompt = chat_service.build_prompt(db, marketer1_user, thread, "Viết thêm 1 caption")

    assert f"Chiến dịch gắn với phiên: #{sample_campaign.id}" in prompt
    assert "Đối tượng" not in prompt  # phiên OpenCode đã nhớ ảnh chụp từ lượt đầu


def test_changing_campaign_starts_new_session(db: Session, marketer1_user: User, sample_campaign: Campaign):
    thread = _thread(db, marketer1_user, None, session_id="ses_existing")

    chat_service.update_thread(db, marketer1_user, thread.id, AiThreadUpdate(campaign_id=sample_campaign.id))

    db.refresh(thread)
    assert thread.campaign_id == sample_campaign.id
    assert thread.opencode_session_id is None
