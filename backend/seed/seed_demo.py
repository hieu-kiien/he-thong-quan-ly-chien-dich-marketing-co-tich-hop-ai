"""Script seed dữ liệu mẫu chuẩn SME Việt Nam (CONTRACT §3).

Chạy bằng lệnh tường minh:
    python seed/seed_demo.py [--force] [--reset]

Quy định an toàn:
- Từ chối thực thi khi APP_ENV=production trừ khi có cờ `--force`.
- Toàn bộ số liệu có `source=SEED` để UI gắn nhãn "Dữ liệu mẫu" (Luật chống tính năng ảo CONTRACT §0).
"""

from __future__ import annotations

import argparse
import sys
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

# Ensure UTF-8 stdout on Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

# Add backend directory to sys.path
backend_root = Path(__file__).resolve().parents[1]
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from sqlalchemy import delete, select

from app.core.config import settings
from app.core.database import Base, SessionLocal, engine, utcnow
from app.core.security import hash_password
from app.core.timeutil import today_vn
from app.models import (
    BannedKeyword,
    BrandProfile,
    Campaign,
    CampaignChannel,
    Channel,
    Content,
    ContentReview,
    Metric,
    Notification,
    Schedule,
    User,
)
from app.models.enums import (
    CampaignGoal,
    CampaignStatus,
    ContentOrigin,
    ContentStatus,
    ContentType,
    MetricSource,
    ReviewDecision,
    ScheduleStatus,
    UserRole,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed demo data for MarketFlow v2")
    parser.add_argument("--force", action="store_true", help="Bắt buộc chạy kể cả trên production")
    parser.add_argument("--reset", action="store_true", help="Xoá sạch dữ liệu cũ trước khi nạp")
    return parser.parse_args()


def check_environment(force: bool) -> None:
    if settings.is_production and not force:
        print("LỖI BẢO MẬT: Đang ở môi trường PRODUCTION! Seed chỉ được chạy khi có cờ --force.")
        sys.exit(1)


def seed_demo_data(reset: bool = False) -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        if reset:
            print("Đang dọn dẹp dữ liệu cũ (--reset)...")
            # Drop in reverse foreign key order
            db.execute(delete(Schedule))
            db.execute(delete(ContentReview))
            db.execute(delete(Content))
            db.execute(delete(Metric))
            db.execute(delete(CampaignChannel))
            db.execute(delete(Campaign))
            db.execute(delete(Notification))
            db.execute(delete(BannedKeyword))
            db.execute(delete(BrandProfile))
            db.execute(delete(Channel))
            db.execute(delete(User))
            db.commit()

        # 1. Users
        print("1. Tạo tài khoản mẫu...")
        users_spec = [
            ("manager@marketflow.vn", "Nguyễn Văn Quản Lý", "Manager@123", UserRole.MANAGER),
            ("marketer@marketflow.vn", "Trần Thị Lan Anh", "Marketer@123", UserRole.MARKETER),
            ("marketer2@marketflow.vn", "Lê Hoàng Minh", "Marketer@123", UserRole.MARKETER),
        ]
        users: dict[str, User] = {}
        for email, full_name, password, role in users_spec:
            user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
            if user is None:
                user = User(
                    email=email,
                    full_name=full_name,
                    password_hash=hash_password(password),
                    role=role,
                    is_active=True,
                    token_version=0,
                )
                db.add(user)
                db.flush()
            users[email] = user

        manager = users["manager@marketflow.vn"]
        marketer1 = users["marketer@marketflow.vn"]
        marketer2 = users["marketer2@marketflow.vn"]

        # 2. Channels (7 standard channels)
        print("2. Tạo danh mục kênh truyền thông...")
        channels_spec = [
            (
                "FACEBOOK",
                "Facebook Fanpage",
                "Tối đa 2000 ký tự. Cần có hình ảnh tỉ lệ 1:1 hoặc 16:9, hashtag thương hiệu #AnNamCoffee, CTA rõ ràng ở cuối bài.",
            ),
            (
                "INSTAGRAM",
                "Instagram",
                "Tập trung vào ảnh/Reels chất lượng cao, màu sắc ấm áp. Caption tối đa 1000 ký tự, 5-10 hashtags ngành cà phê.",
            ),
            (
                "TIKTOK",
                "TikTok",
                "Video ngắn 15-45 giây, 3 giây đầu gây ấn tượng (hook). Kịch bản ngắn gọn, giai điệu bắt tai hoặc voice-over mộc mạc.",
            ),
            (
                "ZALO_OA",
                "Zalo Official Account",
                "Tin nhắn Broadcast & bài viết Zalo. Tiêu đề dưới 100 ký tự, lời mời thân mật, gắn nút nhận voucher ưu đãi.",
            ),
            (
                "EMAIL",
                "Email Marketing",
                "Tiêu đề dưới 60 ký tự, mở đầu cá nhân hoá. Thiết kế tối giản, 1 nút CTA chính, chân trang kèm địa chỉ xưởng rang.",
            ),
            (
                "GOOGLE_ADS",
                "Google Tìm Kiếm & Hiển Thị",
                "Tiêu đề tối đa 30 ký tự, mô tả tối đa 90 ký tự. Đúng từ khoá cà phê nguyên chất, dẫn về trang đặt hàng.",
            ),
            (
                "WEBSITE",
                "Website & Blog An Nam",
                "Bài viết chuẩn SEO 800 - 1500 từ về văn hoá cà phê, cách pha chế, câu chuyện nông sản Tây Nguyên.",
            ),
        ]
        channels: dict[str, Channel] = {}
        for code, name, rules in channels_spec:
            ch = db.execute(select(Channel).where(Channel.code == code)).scalar_one_or_none()
            if ch is None:
                ch = Channel(code=code, name=name, format_rules=rules, is_active=True)
                db.add(ch)
                db.flush()
            channels[code] = ch

        # 3. Brand Profile & Banned Keywords
        print("3. Cập nhật hồ sơ thương hiệu & danh sách từ cấm...")
        bp = db.execute(select(BrandProfile).limit(1)).scalar_one_or_none()
        if bp is None:
            bp = BrandProfile(
                brand_name="Cà phê Rang xay An Nam",
                description="Chuỗi xưởng rang cà phê đặc sản và quán trải nghiệm có nguồn gốc tại Đắk Lắk và Cầu Đất (Lâm Đồng). Phục vụ người sành cà phê và giới văn phòng trẻ yêu thích hương vị mộc nguyên bản.",
                tone_of_voice="Chân thành, ấm áp, đậm chất chuyên môn cà phê Việt nhưng gần gũi, không khoa trương hay dùng thuật ngữ quá xa vời.",
                target_audience="Dân văn phòng, người làm sáng tạo từ 22 đến 40 tuổi tại Hà Nội và TP.HCM, quan tâm đến nguồn gốc thực phẩm và lối sống lành mạnh.",
                guidelines="1. Luôn tôn vinh người nông dân và văn hoá cà phê Tây Nguyên.\n2. Cam kết rang mộc 100%, không bắp rang, không hương liệu hoá học.\n3. Không so sánh dìm hàng thương hiệu khác.\n4. Giữ phong thái lịch thiệp, câu từ gãy gọn, chuẩn tiếng Việt.",
            )
            db.add(bp)

        banned_spec = [
            ("cam kết 100%", "Tránh khẳng định tuyệt đối không có cơ sở kiểm định độc lập"),
            ("chữa khỏi", "Không được dùng từ ngữ y tế chữa bệnh cho sản phẩm thực phẩm/đồ uống"),
            ("rẻ nhất", "Tránh cạnh tranh không lành mạnh bằng tuyên bố giá rẻ nhất thiếu chứng minh"),
            ("số 1 việt nam", "Vi phạm điều 8 Luật Quảng cáo 2012 về từ ngữ độc quyền duy nhất"),
            ("thần dược", "Phóng đại công dụng sản phẩm gây hiểu lầm cho người tiêu dùng"),
            ("tuyệt đối", "Tránh cam kết tuyệt đối trong tiếp thị tiêu dùng"),
            ("vĩnh viễn", "Cam kết không có khả năng bảo đảm thực tế"),
            ("trúng thưởng 100%", "Cụm từ dễ gây phản cảm và hiểu nhầm lừa đảo"),
            ("miễn phí trọn đời", "Cần có điều kiện kèm theo rõ ràng nếu có ưu đãi"),
            ("hàng đầu thế giới", "Vi phạm quy định quảng cáo so sánh bậc nhất"),
        ]
        for kw, note in banned_spec:
            existing_kw = db.execute(select(BannedKeyword).where(BannedKeyword.keyword == kw)).scalar_one_or_none()
            if existing_kw is None:
                db.add(BannedKeyword(keyword=kw, note=note))

        db.flush()

        # 4. Campaigns (5 realistic campaigns)
        print("4. Tạo 5 chiến dịch marketing mẫu...")
        today = today_vn()

        campaign_specs = [
            {
                "name": "Ra Mắt Dòng Cold Brew Đóng Chai Tiện Lợi",
                "goal": CampaignGoal.SALES,
                "objective": "Giới thiệu 3 hương vị cà phê ủ lạnh đóng chai (Nguyên bản, Cam vàng, Hạnh nhân) đến tệp khách văn phòng.",
                "target_audience": "Nhân viên văn phòng bận rộn 24-35 tuổi tại các toà nhà văn phòng trung tâm.",
                "product": "Bộ 3 chai Cold Brew An Nam 250ml",
                "key_message": "Cà phê ủ lạnh 18 tiếng — Tỉnh táo mượt mà, sẵn sàng ngày mới.",
                "start_date": today - timedelta(days=45),
                "end_date": today + timedelta(days=15),
                "budget": Decimal(35_000_000),
                "status": CampaignStatus.ACTIVE,
                "owner": marketer1,
                "channels": [
                    (channels["FACEBOOK"], Decimal(15_000_000)),
                    (channels["INSTAGRAM"], Decimal(10_000_000)),
                    (channels["TIKTOK"], Decimal(10_000_000)),
                ],
            },
            {
                "name": "Mùa Thu Cầu Đất - Hương Vị Arabica Núi Cao",
                "goal": CampaignGoal.TRAFFIC,
                "objective": "Thu hút lượt ghé thăm chuỗi quán và website trải nghiệm mùa thu hoạch Arabica Cầu Đất mới.",
                "target_audience": "Khách hàng sành gu, thích trải nghiệm không gian quán cà phê và học pha chế thủ công.",
                "product": "Bộ sưu tập Hạt Arabica Cầu Đất rang mộc & Thức uống Mùa Thu",
                "key_message": "Chạm vào mùa thu Đà Lạt qua từng giọt Arabica thơm hương hoa quả.",
                "start_date": today - timedelta(days=25),
                "end_date": today + timedelta(days=35),
                "budget": Decimal(25_000_000),
                "status": CampaignStatus.ACTIVE,
                "owner": marketer2,
                "channels": [
                    (channels["FACEBOOK"], Decimal(10_000_000)),
                    (channels["INSTAGRAM"], Decimal(10_000_000)),
                    (channels["WEBSITE"], Decimal(5_000_000)),
                ],
            },
            {
                "name": "Workshop Rang & Cupping Cà Phê Cuối Tuần",
                "goal": CampaignGoal.LEADS,
                "objective": "Thu thập danh sách 100 người đăng ký tham gia lớp học thử nếm cà phê và phân biệt hương vị.",
                "target_audience": "Khách hàng cá nhân, barista mới vào nghề, người yêu thích văn hoá thủ công.",
                "product": "Vé tham gia Workshop Cupping An Nam (299k/người)",
                "key_message": "Tự tay nếm và hiểu 8 tầng hương vị cà phê Tây Nguyên.",
                "start_date": today + timedelta(days=5),
                "end_date": today + timedelta(days=25),
                "budget": Decimal(12_000_000),
                "status": CampaignStatus.PLANNED,
                "owner": manager,
                "channels": [
                    (channels["FACEBOOK"], Decimal(7_000_000)),
                    (channels["EMAIL"], Decimal(3_000_000)),
                    (channels["WEBSITE"], Decimal(2_000_000)),
                ],
            },
            {
                "name": "Chăm Sóc Khách Thân Thiết — Tích Điểm Đổi Ly Giữ Nhiệt",
                "goal": CampaignGoal.AWARENESS,
                "objective": "Gia tăng tỷ lệ quay lại của khách hàng cũ qua Zalo OA và Email chăm sóc.",
                "target_audience": "Hội viên An Nam Member đã mua hàng từ 3 lần trở lên.",
                "product": "Chương trình Hội viên An Nam Club & Ly giữ nhiệt tre",
                "key_message": "Uống cà phê ngon, sống xanh cùng An Nam.",
                "start_date": today - timedelta(days=60),
                "end_date": today - timedelta(days=10),
                "budget": Decimal(18_000_000),
                "status": CampaignStatus.PAUSED,
                "owner": marketer1,
                "channels": [
                    (channels["ZALO_OA"], Decimal(10_000_000)),
                    (channels["EMAIL"], Decimal(8_000_000)),
                ],
            },
            {
                "name": "Mừng Khai Trương Chi Nhánh Quận 1 — Mua 1 Tặng 1",
                "goal": CampaignGoal.SALES,
                "objective": "Kéo 3.000 lượt khách đến không gian quán mới tại đường Nguyễn Huệ trong 3 tuần đầu.",
                "target_audience": "Khách địa phương và du khách tại khu vực trung tâm Quận 1.",
                "product": "Toàn bộ menu thức uống pha máy & pha thủ công",
                "key_message": "An Nam đã đến Quận 1 — Mời bạn ghé chơi nhận ưu đãi nhân đôi.",
                "start_date": today - timedelta(days=90),
                "end_date": today - timedelta(days=50),
                "budget": Decimal(30_000_000),
                "status": CampaignStatus.COMPLETED,
                "owner": marketer2,
                "channels": [
                    (channels["FACEBOOK"], Decimal(15_000_000)),
                    (channels["TIKTOK"], Decimal(10_000_000)),
                    (channels["GOOGLE_ADS"], Decimal(5_000_000)),
                ],
            },
        ]

        created_campaigns: list[Campaign] = []
        for cspec in campaign_specs:
            camp = db.execute(select(Campaign).where(Campaign.name == cspec["name"])).scalar_one_or_none()
            if camp is None:
                camp = Campaign(
                    name=cspec["name"],
                    goal=cspec["goal"],
                    objective=cspec["objective"],
                    target_audience=cspec["target_audience"],
                    product=cspec["product"],
                    key_message=cspec["key_message"],
                    start_date=cspec["start_date"],
                    end_date=cspec["end_date"],
                    budget=cspec["budget"],
                    status=cspec["status"],
                    owner_id=cspec["owner"].id,
                )
                db.add(camp)
                db.flush()
                for ch, pb in cspec["channels"]:
                    db.add(CampaignChannel(campaign_id=camp.id, channel_id=ch.id, planned_budget=pb))
                db.flush()
            created_campaigns.append(camp)

        camp_coldbrew = created_campaigns[0]
        camp_autum = created_campaigns[1]
        camp_workshop = created_campaigns[2]

        # 5. Contents across statuses (DRAFT, PENDING_REVIEW, APPROVED, REJECTED, PUBLISHED)
        print("5. Tạo nội dung với đủ trạng thái duyệt...")
        content_specs = [
            # 1. PUBLISHED
            {
                "campaign": camp_coldbrew,
                "channel": channels["FACEBOOK"],
                "content_type": ContentType.SOCIAL_POST,
                "title": "Bí quyết giữ trọn hương vị Cold Brew suốt 18 tiếng",
                "body": "Bạn có biết tại sao Cold Brew tại An Nam lại có vị ngọt hậu tự nhiên mà không cần thêm đường?\n\nĐó là nhờ phương pháp ủ lạnh chậm 18 tiếng ở nhiệt độ 4°C với hạt Robusta Đắk Lắk hái chín cây 100%. Vị đậm đà nhưng êm dịu, không gắt họng.\n\nĐặt ngay hôm nay để nhận ưu đãi dùng thử 3 chai chỉ 145.000đ!",
                "cta": "Nhắn tin đặt giao ngay",
                "status": ContentStatus.PUBLISHED,
                "origin": ContentOrigin.MANUAL,
                "created_by": marketer1,
                "published_url": "https://facebook.com/annamexample/posts/101",
                "published_at": utcnow() - timedelta(days=10),
                "published_by": manager,
            },
            # 2. APPROVED
            {
                "campaign": camp_coldbrew,
                "channel": channels["INSTAGRAM"],
                "content_type": ContentType.SOCIAL_POST,
                "title": "Visual 3 sắc màu Cold Brew An Nam đón tuần mới",
                "body": "3 chai — 3 cá tính:\n- Đen nguyên bản cho ngày cần tập trung tối đa.\n- Cam vàng tươi mát cho buổi chiều sảng khoái.\n- Hạnh nhân béo nhẹ cho buổi sáng thư thả.\n\nBạn chọn hương vị nào cho thứ Hai năng suất?",
                "cta": "Xem thêm tại link trên bio",
                "status": ContentStatus.APPROVED,
                "created_by": marketer1,
                "review_decision": ReviewDecision.APPROVED,
                "review_comment": "Nội dung chuẩn brand guideline, hình ảnh phối màu rất tốt. Đã duyệt.",
                "reviewer": manager,
            },
            # 3. PENDING_REVIEW
            {
                "campaign": camp_coldbrew,
                "channel": channels["TIKTOK"],
                "content_type": ContentType.VIDEO_SCRIPT,
                "title": "Kịch bản TikTok: Thử thách 1 ngày làm việc cùng Cold Brew",
                "body": "[0-3s Hook] Dân văn phòng 8 tiếng ngồi máy tính thì uống gì để không say cà phê?\n[3-15s Body] Cùng mình unbox set Cold Brew đóng chai của An Nam. Chai thuỷ tinh chắc chắn, rót ra đá nghe tiếng kêu cực đã tai.\n[15-30s Review] Vị êm ru, hậu ngọt tự nhiên, không bị chua gắt.\n[30-45s CTA] Bấm vào giỏ hàng góc trái nhận ngay mã giảm giá 20k cho đơn đầu tiên!",
                "cta": "Bấm vào giỏ hàng đặt thử ngay",
                "status": ContentStatus.PENDING_REVIEW,
                "origin": ContentOrigin.MANUAL,
                "created_by": marketer1,
            },
            # 4. REJECTED
            {
                "campaign": camp_autum,
                "channel": channels["FACEBOOK"],
                "content_type": ContentType.SOCIAL_POST,
                "title": "Cà phê sạch rẻ nhất Sài Gòn cam kết 100% không say",
                "body": "Đến An Nam uống cà phê rẻ nhất khu vực! Chúng tôi cam kết 100% hạt nguyên chất, uống vào sảng khoái tức thì, không say vĩnh viễn.",
                "cta": "Ghé quán ngay",
                "status": ContentStatus.REJECTED,
                "origin": ContentOrigin.MANUAL,
                "created_by": marketer2,
                "review_decision": ReviewDecision.REJECTED,
                "review_comment": "Bài viết vi phạm từ cấm ('rẻ nhất', 'cam kết 100%', 'vĩnh viễn') và không đúng giọng điệu lịch thiệp của An Nam. Vui lòng sửa lại toàn bộ.",
                "reviewer": manager,
            },
            # 5. DRAFT
            {
                "campaign": camp_workshop,
                "channel": channels["EMAIL"],
                "content_type": ContentType.EMAIL,
                "title": "[Thư Mời] Trải nghiệm giác quan cùng Xưởng Rang An Nam",
                "body": "Chào bạn,\n\nBạn đã bao giờ tự tay ngửi hạt cà phê vừa rang xong và phân biệt được nốt hương hoa quả với hương chocolate chưa?\n\nCuối tuần này, Trưởng xưởng rang An Nam thân mời bạn tham gia buổi Cupping thân mật tại số 12 Võ Thị Sáu...",
                "cta": "Đăng ký giữ chỗ Workshop",
                "status": ContentStatus.DRAFT,
                "created_by": manager,
            },
        ]

        created_contents: list[Content] = []
        for cdata in content_specs:
            content = db.execute(
                select(Content).where(
                    Content.campaign_id == cdata["campaign"].id,
                    Content.title == cdata["title"],
                )
            ).scalar_one_or_none()
            if content is None:
                content = Content(
                    campaign_id=cdata["campaign"].id,
                    channel_id=cdata["channel"].id,
                    content_type=cdata["content_type"],
                    title=cdata["title"],
                    body=cdata["body"],
                    cta=cdata.get("cta"),
                    status=cdata["status"],
                    origin=cdata.get("origin", ContentOrigin.MANUAL),
                    created_by=cdata["created_by"].id,
                    published_url=cdata.get("published_url"),
                    published_at=cdata.get("published_at"),
                    published_by=cdata.get("published_by").id if cdata.get("published_by") else None,
                )
                db.add(content)
                db.flush()

                if "review_decision" in cdata:
                    review = ContentReview(
                        content_id=content.id,
                        reviewer_id=cdata["reviewer"].id,
                        decision=cdata["review_decision"],
                        comment=cdata.get("review_comment", ""),
                    )
                    db.add(review)
                    db.flush()
            created_contents.append(content)

        # 6. Schedules
        print("6. Tạo lịch đăng bài...")
        now = utcnow()
        schedules_spec = [
            (created_contents[0], now - timedelta(days=10), ScheduleStatus.DONE, marketer1.id, "Đã đăng theo đúng khung giờ trưa"),
            (created_contents[1], now + timedelta(days=1, hours=2), ScheduleStatus.PLANNED, marketer1.id, "Đăng kèm 3 ảnh carousel"),
            (created_contents[2], now + timedelta(days=3, hours=5), ScheduleStatus.PLANNED, marketer1.id, "Chờ video hoàn thiện và duyệt kịch bản"),
        ]
        for c, dt, st, assignee, note in schedules_spec:
            sched = db.execute(select(Schedule).where(Schedule.content_id == c.id)).scalar_one_or_none()
            if sched is None:
                db.add(
                    Schedule(
                        content_id=c.id,
                        scheduled_at=dt,
                        status=st,
                        assignee_id=assignee,
                        note=note,
                        done_at=now - timedelta(days=10) if st == ScheduleStatus.DONE else None,
                    )
                )

        # 7. Metrics (30-45 days of daily data, source=SEED)
        print("7. Tạo số liệu hiệu quả 40 ngày (source=SEED)...")
        # Generates metrics for camp_coldbrew on FACEBOOK and INSTAGRAM for the past 40 days
        import random
        random.seed(42)  # Deterministic realistic numbers

        base_date = today - timedelta(days=40)
        metrics_count = 0
        for i in range(41):
            m_date = base_date + timedelta(days=i)

            # Cold Brew on Facebook
            views_fb = random.randint(800, 2500)
            clicks_fb = int(views_fb * random.uniform(0.03, 0.07))
            conv_fb = int(clicks_fb * random.uniform(0.04, 0.12))
            cost_fb = Decimal(int(clicks_fb * random.uniform(2800, 4500)))

            existing_m = db.execute(
                select(Metric).where(
                    Metric.campaign_id == camp_coldbrew.id,
                    Metric.channel_id == channels["FACEBOOK"].id,
                    Metric.metric_date == m_date,
                )
            ).scalar_one_or_none()
            if existing_m is None:
                db.add(
                    Metric(
                        campaign_id=camp_coldbrew.id,
                        channel_id=channels["FACEBOOK"].id,
                        metric_date=m_date,
                        views=views_fb,
                        clicks=clicks_fb,
                        conversions=conv_fb,
                        cost=cost_fb,
                        source=MetricSource.SEED,
                        entered_by=marketer1.id,
                        import_batch="seed_demo_v2",
                    )
                )
                metrics_count += 1

            # Cold Brew on Instagram
            views_ig = random.randint(600, 1800)
            clicks_ig = int(views_ig * random.uniform(0.025, 0.06))
            conv_ig = int(clicks_ig * random.uniform(0.03, 0.09))
            cost_ig = Decimal(int(clicks_ig * random.uniform(3200, 5200)))

            existing_m_ig = db.execute(
                select(Metric).where(
                    Metric.campaign_id == camp_coldbrew.id,
                    Metric.channel_id == channels["INSTAGRAM"].id,
                    Metric.metric_date == m_date,
                )
            ).scalar_one_or_none()
            if existing_m_ig is None:
                db.add(
                    Metric(
                        campaign_id=camp_coldbrew.id,
                        channel_id=channels["INSTAGRAM"].id,
                        metric_date=m_date,
                        views=views_ig,
                        clicks=clicks_ig,
                        conversions=conv_ig,
                        cost=cost_ig,
                        source=MetricSource.SEED,
                        entered_by=marketer1.id,
                        import_batch="seed_demo_v2",
                    )
                )
                metrics_count += 1

        # 8. Notifications
        print("8. Tạo thông báo mẫu...")
        notif_specs = [
            (
                manager.id,
                "CONTENT_SUBMITTED",
                f'{marketer1.full_name} gửi duyệt kịch bản video "{created_contents[2].title}"',
                f"/contents/{created_contents[2].id}",
                False,
            ),
            (
                marketer1.id,
                "CONTENT_APPROVED",
                f'Quản lý {manager.full_name} đã duyệt nội dung "{created_contents[1].title}"',
                f"/contents/{created_contents[1].id}",
                True,
            ),
            (
                marketer2.id,
                "CONTENT_REJECTED",
                f'Nội dung "{created_contents[3].title}" bị từ chối duyệt: vi phạm từ cấm',
                f"/contents/{created_contents[3].id}",
                False,
            ),
        ]
        for uid, ntype, msg, link, read in notif_specs:
            # Idempotent: chạy seed nhiều lần không nhân bản thông báo
            if db.execute(
                select(Notification.id).where(Notification.user_id == uid, Notification.type == ntype, Notification.link == link)
            ).first():
                continue
            db.add(Notification(user_id=uid, type=ntype, message=msg, link=link, is_read=read))

        db.commit()
        print(f"Hoàn tất nạp dữ liệu mẫu thành công! Đã tạo {metrics_count} dòng số liệu SEED.")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    args = parse_args()
    check_environment(args.force)
    print("Bắt đầu nạp dữ liệu mẫu MarketFlow v2...")
    seed_demo_data(reset=args.reset)


if __name__ == "__main__":
    main()
