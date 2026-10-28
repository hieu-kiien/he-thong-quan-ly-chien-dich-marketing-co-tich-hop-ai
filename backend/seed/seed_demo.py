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
    AiAction,
    AiMessage,
    AiThread,
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
    parser = argparse.ArgumentParser(description="Seed demo data for MarketFlow")
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
            db.execute(delete(AiAction))
            db.execute(delete(AiMessage))
            db.execute(delete(AiThread))
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
        camp_loyalty = created_campaigns[3]
        camp_opening = created_campaigns[4]

        # 5. Contents across statuses (DRAFT, PENDING_REVIEW, APPROVED, REJECTED, PUBLISHED)
        # Bám sát chặt chẽ mục tiêu (Goal), sản phẩm (Product) và thông điệp cốt lõi (Key Message) của cả 5 chiến dịch
        print("5. Tạo 18 nội dung bám sát mục tiêu của từng chiến dịch với đủ trạng thái duyệt...")
        content_specs = [
            # --- CHIẾN DỊCH 1: Cold Brew (Mục tiêu: SALES - Tăng doanh số) ---
            # 0. PUBLISHED
            {
                "campaign": camp_coldbrew,
                "channel": channels["FACEBOOK"],
                "content_type": ContentType.SOCIAL_POST,
                "title": "Bí quyết giữ trọn hương vị Cold Brew suốt 18 tiếng",
                "body": "Bạn có biết tại sao Cold Brew tại An Nam lại có vị ngọt hậu tự nhiên mà không cần thêm đường?\n\nĐó là nhờ phương pháp ủ lạnh chậm 18 tiếng ở nhiệt độ 4°C với hạt Robusta & Arabica hái chín cây. Vị đậm đà nhưng êm dịu, không gắt họng.\n\nĐặt ngay Bộ 3 chai Cold Brew An Nam 250ml hôm nay để nhận ưu đãi dùng thử chỉ 145.000đ!",
                "cta": "Nhắn tin đặt giao ngay",
                "status": ContentStatus.PUBLISHED,
                "origin": ContentOrigin.MANUAL,
                "created_by": marketer1,
                "published_url": "https://facebook.com/annamcoffee/posts/coldbrew-18h",
                "published_at": utcnow() - timedelta(days=10),
                "published_by": manager,
                "review_decision": ReviewDecision.APPROVED,
                "review_comment": "Bài viết bám sát mục tiêu Tăng doanh số và thông điệp ủ lạnh 18 tiếng. Duyệt đăng.",
                "reviewer": manager,
            },
            # 1. APPROVED
            {
                "campaign": camp_coldbrew,
                "channel": channels["INSTAGRAM"],
                "content_type": ContentType.SOCIAL_POST,
                "title": "Visual 3 sắc màu Cold Brew An Nam đón tuần mới",
                "body": "3 chai — 3 cá tính cho tuần làm việc hiệu suất:\n- Nguyên bản đậm sâu cho buổi sáng cần tập trung.\n- Cam vàng thanh mát cho buổi chiều sảng khoái.\n- Hạnh nhân béo nhẹ cho ngày làm việc thư thả.\n\nCà phê ủ lạnh 18 tiếng — Tỉnh táo mượt mà, sẵn sàng ngày mới.",
                "cta": "Đặt mua combo 3 chai tại bio",
                "status": ContentStatus.APPROVED,
                "origin": ContentOrigin.MANUAL,
                "created_by": marketer1,
                "review_decision": ReviewDecision.APPROVED,
                "review_comment": "Nội dung chuẩn quy định kênh Instagram, hình ảnh phối màu ấm áp. Đã duyệt.",
                "reviewer": manager,
            },
            # 2. PENDING_REVIEW (by marketer1 -> Manager có thể duyệt ngay khi demo)
            {
                "campaign": camp_coldbrew,
                "channel": channels["TIKTOK"],
                "content_type": ContentType.VIDEO_SCRIPT,
                "title": "Kịch bản TikTok: Thử thách 1 ngày làm việc cùng Cold Brew",
                "body": "[0-3s Hook] Dân văn phòng 8 tiếng ngồi máy tính thì uống gì để tỉnh táo mượt mà không lo say cà phê?\n[3-15s Body] Cùng mình khui Bộ 3 chai Cold Brew An Nam 250ml. Chai thuỷ tinh cầm chắc tay, rót ra đá viên nghe tiếng leng keng cực cuốn.\n[15-30s Điểm nhấn] Ủ lạnh đủ 18 tiếng nên hậu vị ngọt thanh tự nhiên của cam vàng và hạnh nhân.\n[30-45s CTA] Bấm vào giỏ hàng góc trái nhận ngay ưu đãi đặt mua combo 3 vị giao nhanh trong 2 giờ!",
                "cta": "Bấm giỏ hàng đặt thử ngay",
                "status": ContentStatus.PENDING_REVIEW,
                "origin": ContentOrigin.MANUAL,
                "created_by": marketer1,
            },
            # 3. APPROVED (AI origin)
            {
                "campaign": camp_coldbrew,
                "channel": channels["FACEBOOK"],
                "content_type": ContentType.AD_COPY,
                "title": "Ưu đãi Combo 3 chai Cold Brew giao nhanh tận bàn làm việc",
                "body": "Cơn buồn ngủ lúc 2 giờ chiều làm chậm tiến độ của bạn?\n\nBộ 3 chai Cold Brew An Nam 250ml (Nguyên bản - Cam vàng - Hạnh nhân) được ủ lạnh 18 tiếng giúp giữ trọn hương thơm tự nhiên, tiếp thêm sự tỉnh táo mượt mà cho cả tuần làm việc.\n\nƯu đãi tuần này: Giảm ngay 25.000đ và miễn phí giao hàng nội thành cho đơn từ 2 combo.",
                "cta": "Đặt mua nhận ưu đãi ngay",
                "status": ContentStatus.APPROVED,
                "origin": ContentOrigin.AI,
                "created_by": marketer1,
                "review_decision": ReviewDecision.APPROVED,
                "review_comment": "Bản nháp từ Trợ lý AI nêu rõ ưu đãi và CTA đặt hàng sát mục tiêu SALES.",
                "reviewer": manager,
            },

            # --- CHIẾN DỊCH 2: Mùa Thu Cầu Đất (Mục tiêu: TRAFFIC - Tăng lượt truy cập) ---
            # 4. REJECTED (Vi phạm từ cấm)
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
                "review_comment": "Bài viết vi phạm từ cấm ('rẻ nhất', 'cam kết 100%', 'vĩnh viễn') và sai lệch thông điệp mùa thu Cầu Đất. Yêu cầu viết lại.",
                "reviewer": manager,
            },
            # 5. PUBLISHED
            {
                "campaign": camp_autum,
                "channel": channels["WEBSITE"],
                "content_type": ContentType.OTHER,
                "title": "Hành trình hạt Arabica Cầu Đất từ sương mù 1.650m đến tách cà phê sáng",
                "body": "Ở độ cao 1.650m so với mực nước biển, vùng nguyên liệu Cầu Đất (Đà Lạt) quanh năm mây phủ là cái nôi của những trái Arabica chín đỏ mọng.\n\nBài viết trên Blog An Nam dẫn bạn đi qua quy trình thu hái chọn lọc từng trái chín, sơ chế ướt (Washed) và rang mộc chuẩn xác để giữ lại hương hoa trắng cùng vị chua thanh tựa táo xanh.\n\nKhám phá trọn vẹn câu chuyện nông trại và bảng hướng dẫn pha Pour-over tại trang chuyên đề Mùa Thu Cầu Đất.",
                "cta": "Đọc trọn bài viết trên Website An Nam",
                "status": ContentStatus.PUBLISHED,
                "origin": ContentOrigin.MANUAL,
                "created_by": marketer2,
                "published_url": "https://annamcoffee.vn/blog/mua-thu-cau-dat-arabica",
                "published_at": utcnow() - timedelta(days=14),
                "published_by": manager,
                "review_decision": ReviewDecision.APPROVED,
                "review_comment": "Bài chuẩn SEO kéo lượt truy cập về website rất tốt.",
                "reviewer": manager,
            },
            # 6. APPROVED
            {
                "campaign": camp_autum,
                "channel": channels["INSTAGRAM"],
                "content_type": ContentType.SOCIAL_POST,
                "title": "Chạm vào mùa thu Đà Lạt qua từng giọt Arabica Cầu Đất thơm hương hoa quả",
                "body": "Một góc nắng thu dịu nhẹ tại không gian An Nam cùng bình Pour-over Arabica Cầu Đất vừa chiết xuất.\n\nHương thơm dịu của vỏ cam chín, chút ngọt thanh của mật ong rừng Tây Nguyên khiến buổi sáng cuối tuần thêm trọn vẹn.\n\nXem bản đồ các cơ sở trải nghiệm và thực đơn Mùa Thu tại đường dẫn trên trang cá nhân.",
                "cta": "Khám phá thực đơn Mùa Thu tại bio",
                "status": ContentStatus.APPROVED,
                "origin": ContentOrigin.AI,
                "created_by": marketer2,
                "review_decision": ReviewDecision.APPROVED,
                "review_comment": "Đúng tông giọng ấm áp và dẫn link tăng lượt truy cập.",
                "reviewer": manager,
            },
            # 7. PENDING_REVIEW (by marketer2)
            {
                "campaign": camp_autum,
                "channel": channels["FACEBOOK"],
                "content_type": ContentType.SOCIAL_POST,
                "title": "Gợi ý 3 cách pha hạt Arabica Cầu Đất rang mộc thơm chuẩn vị tại nhà",
                "body": "Nhiều bạn hỏi An Nam làm sao để pha túi hạt Arabica Cầu Đất tại nhà mà vẫn dậy hương hoa quả tự nhiên như ngoài quán?\n\nTrong bài hướng dẫn mới trên Website, Barista trưởng của An Nam đã chia sẻ chi tiết tỷ lệ nước, nhiệt độ 92°C và cỡ xay cho cả 3 dụng cụ: V60, AeroPress và Cold Brew.\n\nNhấp vào liên kết bên dưới để xem bảng thông số chi tiết nhé!",
                "cta": "Xem hướng dẫn pha chế trên Website",
                "status": ContentStatus.PENDING_REVIEW,
                "origin": ContentOrigin.MANUAL,
                "created_by": marketer2,
            },

            # --- CHIẾN DỊCH 3: Workshop Rang & Cupping (Mục tiêu: LEADS - Thu khách hàng tiềm năng) ---
            # 8. DRAFT
            {
                "campaign": camp_workshop,
                "channel": channels["EMAIL"],
                "content_type": ContentType.EMAIL,
                "title": "[Thư Mời] Trải nghiệm giác quan cùng Xưởng Rang An Nam",
                "body": "Chào bạn,\n\nBạn đã bao giờ tự tay ngửi hạt cà phê vừa rang xong và phân biệt được 8 tầng hương vị cà phê Tây Nguyên từ hoa trắng, cam chanh đến sô-cô-la đen chưa?\n\nCuối tuần này, Trưởng xưởng rang An Nam thân mời bạn tham gia buổi Workshop Rang & Cupping thân mật. Chỉ 20 suất mỗi buổi để đảm bảo trải nghiệm thực hành trực tiếp.",
                "cta": "Đăng ký giữ chỗ Workshop",
                "status": ContentStatus.DRAFT,
                "origin": ContentOrigin.MANUAL,
                "created_by": manager,
            },
            # 9. APPROVED
            {
                "campaign": camp_workshop,
                "channel": channels["FACEBOOK"],
                "content_type": ContentType.AD_COPY,
                "title": "Mở cổng đăng ký Workshop Cupping: Tự tay nếm 8 tầng hương vị cà phê Tây Nguyên",
                "body": "Dành cho người yêu cà phê thủ công và các Barista muốn nâng cao cảm quan mùi vị:\n\n- Thực hành quan sát biến đổi hạt trên máy rang mẫu.\n- Trải nghiệm quy trình Cupping tiêu chuẩn SCA cùng 6 mẫu hạt Đắk Lắk & Cầu Đất.\n- Tặng kèm 01 túi hạt Arabica 150g tự phối trộn mang về.\n\nPhí tham dự: 299.000đ/người. Điền biểu mẫu đăng ký để giữ suất cuối tuần này!",
                "cta": "Điền thông tin đăng ký tham dự",
                "status": ContentStatus.APPROVED,
                "origin": ContentOrigin.AI,
                "created_by": marketer1,
                "review_decision": ReviewDecision.APPROVED,
                "review_comment": "Nêu rõ quyền lợi người tham dự, bám sát mục tiêu thu 100 đăng ký.",
                "reviewer": manager,
            },
            # 10. PENDING_REVIEW (by manager -> Dùng để demo quy tắc Bốn Mắt chặn tự duyệt bài chính mình!)
            {
                "campaign": camp_workshop,
                "channel": channels["WEBSITE"],
                "content_type": ContentType.OTHER,
                "title": "Trang đích đăng ký Workshop Rang & Cupping Cà Phê Cuối Tuần",
                "body": "Tự tay nếm và hiểu 8 tầng hương vị cà phê Tây Nguyên trong buổi trải nghiệm 120 phút tại Xưởng Rang An Nam.\n\nNội dung chương trình:\n1. Tìm hiểu nguồn gốc hạt cà phê Đắk Lắk và Cầu Đất.\n2. Thực hành ngửi hương khô (Fragrance) và hương ướt (Aroma).\n3. Thử nếm đối chiếu 6 mẻ rang mộc.\n\nĐể lại Họ tên và Số điện thoại bên dưới để bộ phận điều phối gửi mã vé xác nhận.",
                "cta": "Gửi thông tin giữ vé ngay",
                "status": ContentStatus.PENDING_REVIEW,
                "origin": ContentOrigin.MANUAL,
                "created_by": manager,
            },

            # --- CHIẾN DỊCH 4: Chăm Sóc Khách Thân Thiết (Mục tiêu: AWARENESS - Nhận diện thương hiệu) ---
            # 11. PUBLISHED
            {
                "campaign": camp_loyalty,
                "channel": channels["ZALO_OA"],
                "content_type": ContentType.SOCIAL_POST,
                "title": "Đặc quyền Hội viên An Nam Club: Tích điểm đổi Ly giữ nhiệt vỏ tre",
                "body": "Uống cà phê ngon, sống xanh cùng An Nam!\n\nMỗi ly cà phê bạn thưởng thức tại hệ thống An Nam đều được tích lũy điểm thưởng trên Zalo OA. Khi đạt 15 điểm, bạn có thể đổi ngay 01 Ly giữ nhiệt vỏ tre khắc tên riêng — cùng An Nam giảm thiểu ly nhựa dùng một lần.",
                "cta": "Mở thẻ hội viên trên Zalo OA",
                "status": ContentStatus.PUBLISHED,
                "origin": ContentOrigin.MANUAL,
                "created_by": marketer1,
                "published_url": "https://zalo.me/annamcoffee/posts/loyalty-bamboo-cup",
                "published_at": utcnow() - timedelta(days=30),
                "published_by": manager,
                "review_decision": ReviewDecision.APPROVED,
                "review_comment": "Thông điệp sống xanh truyền cảm hứng tốt cho tệp khách hàng thân thiết.",
                "reviewer": manager,
            },
            # 12. PUBLISHED
            {
                "campaign": camp_loyalty,
                "channel": channels["EMAIL"],
                "content_type": ContentType.EMAIL,
                "title": "Cảm ơn bạn đã đồng hành cùng hành trình cà phê bền vững An Nam",
                "body": "Chào hội viên thân thiết của An Nam,\n\nNhờ sự ủng hộ của bạn trong suốt thời gian qua, cộng đồng An Nam Club đã giảm thiểu hơn 12.000 chiếc cốc nhựa dùng một lần thông qua chương trình mang bình cá nhân tới quán.\n\nHãy tiếp tục kiểm tra điểm tích lũy của bạn để nhận chiếc Ly giữ nhiệt tre phiên bản giới hạn mùa này nhé.",
                "cta": "Kiểm tra điểm tích lũy của bạn",
                "status": ContentStatus.PUBLISHED,
                "origin": ContentOrigin.AI,
                "created_by": marketer1,
                "published_url": "https://annamcoffee.vn/newsletter/cam-on-hoi-vien-song-xanh",
                "published_at": utcnow() - timedelta(days=22),
                "published_by": manager,
                "review_decision": ReviewDecision.APPROVED,
                "review_comment": "Email chăm sóc hội viên rất ấm áp, đúng hướng dẫn thương hiệu.",
                "reviewer": manager,
            },
            # 13. APPROVED
            {
                "campaign": camp_loyalty,
                "channel": channels["ZALO_OA"],
                "content_type": ContentType.AD_COPY,
                "title": "Nhắc lịch đổi điểm thưởng nhận Ly giữ nhiệt tre An Nam Club",
                "body": "Tin nhắn dành riêng cho Hội viên An Nam Member:\n\nĐợt quà tặng Ly giữ nhiệt vỏ tre thủ công vẫn đang chờ bạn tại quầy trải nghiệm. Đừng quên xuất trình mã QR Hội viên trên Zalo OA trong lần ghé quán tiếp theo để nhân viên gửi tặng món quà xanh từ An Nam.",
                "cta": "Xem mã QR Hội viên ngay",
                "status": ContentStatus.APPROVED,
                "origin": ContentOrigin.MANUAL,
                "created_by": marketer2,
                "review_decision": ReviewDecision.APPROVED,
                "review_comment": "Ngắn gọn, chuẩn định dạng broadcast Zalo OA.",
                "reviewer": manager,
            },

            # --- CHIẾN DỊCH 5: Mừng Khai Trương Chi Nhánh Quận 1 (Mục tiêu: SALES - Tăng doanh số) ---
            # 14. PUBLISHED
            {
                "campaign": camp_opening,
                "channel": channels["FACEBOOK"],
                "content_type": ContentType.SOCIAL_POST,
                "title": "Chính thức khai trương An Nam Quận 1 — Ưu đãi Mua 1 Tặng 1 tuần lễ đầu",
                "body": "An Nam đã đến Quận 1 — Mời bạn ghé chơi nhận ưu đãi nhân đôi!\n\nKhông gian mới tại đường Nguyễn Huệ mang trọn hương cà phê rang mộc Tây Nguyên giữa lòng trung tâm thành phố. Trong tuần lễ khai trương, An Nam gửi tặng ưu đãi Mua 1 Tặng 1 cho toàn bộ menu thức uống pha máy và pha thủ công.",
                "cta": "Lấy mã ưu đãi Mua 1 Tặng 1",
                "status": ContentStatus.PUBLISHED,
                "origin": ContentOrigin.MANUAL,
                "created_by": marketer2,
                "published_url": "https://facebook.com/annamcoffee/posts/khai-truong-quan-1",
                "published_at": utcnow() - timedelta(days=75),
                "published_by": manager,
                "review_decision": ReviewDecision.APPROVED,
                "review_comment": "Bài thông báo khai trương rõ ràng, thu hút khách hàng ghé quán.",
                "reviewer": manager,
            },
            # 15. PUBLISHED
            {
                "campaign": camp_opening,
                "channel": channels["TIKTOK"],
                "content_type": ContentType.VIDEO_SCRIPT,
                "title": "Check-in góc ban công nhìn xuống phố đi bộ tại An Nam Nguyễn Huệ",
                "body": "[0-3s Hook] Một góc ban công ngập nắng ngay phố đi bộ Nguyễn Huệ vừa mới mở cửa!\n[3-15s Cảnh quay] Không gian gỗ ấm cúng, mùi cà phê rang mới thơm phức từ quầy bar thủ công.\n[15-30s Ưu đãi] Đặc biệt tuần lễ khai trương đang áp dụng Mua 1 Tặng 1 toàn bộ menu pha máy và Cold Brew.\n[30-45s CTA] Rủ ngay đồng nghiệp ghé số 88 Nguyễn Huệ thưởng thức nhé!",
                "cta": "Lưu địa chỉ ghé quán ngay",
                "status": ContentStatus.PUBLISHED,
                "origin": ContentOrigin.AI,
                "created_by": marketer2,
                "published_url": "https://tiktok.com/@annamcoffee/video/khai-truong-nguyen-hue",
                "published_at": utcnow() - timedelta(days=70),
                "published_by": manager,
                "review_decision": ReviewDecision.APPROVED,
                "review_comment": "Kịch bản video ngắn gọn, bắt mắt.",
                "reviewer": manager,
            },
            # 16. PUBLISHED
            {
                "campaign": camp_opening,
                "channel": channels["GOOGLE_ADS"],
                "content_type": ContentType.AD_COPY,
                "title": "Cà Phê Đặc Sản Quận 1 | An Nam Nguyễn Huệ Mua 1 Tặng 1",
                "body": "Trải nghiệm cà phê rang mộc 100% Đắk Lắk & Cầu Đất ngay trung tâm Quận 1. Không gian yên tĩnh làm việc, ưu đãi Mua 1 Tặng 1 mừng khai trương.",
                "cta": "Xem chỉ đường & nhận ưu đãi",
                "status": ContentStatus.PUBLISHED,
                "origin": ContentOrigin.MANUAL,
                "created_by": marketer2,
                "published_url": "https://annamcoffee.vn/chi-nhanh-quan-1",
                "published_at": utcnow() - timedelta(days=68),
                "published_by": manager,
                "review_decision": ReviewDecision.APPROVED,
                "review_comment": "Đúng chuẩn giới hạn từ khoá Google Tìm Kiếm.",
                "reviewer": manager,
            },
            # 17. DRAFT
            {
                "campaign": camp_opening,
                "channel": channels["FACEBOOK"],
                "content_type": ContentType.SOCIAL_POST,
                "title": "Nhìn lại 3.200 ly cà phê đầu tiên tại An Nam chi nhánh Quận 1",
                "body": "Khép lại tháng khai trương rực rỡ tại con đường Nguyễn Huệ, đội ngũ Barista An Nam vô cùng biết ơn khi được đón tiếp hơn 3.200 lượt khách ghé thăm và thưởng thức cà phê nguyên bản.",
                "cta": "Xem album ảnh tháng khai trương",
                "status": ContentStatus.DRAFT,
                "origin": ContentOrigin.MANUAL,
                "created_by": marketer2,
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

        # 6. Schedules (Trải đều quá khứ, HÔM NAY và các ngày sắp tới để Lịch đăng bài & Dashboard sống động)
        print("6. Tạo 12 lịch đăng bài cho các chiến dịch...")
        now = utcnow()
        schedules_spec = [
            # Đã hoàn thành trong quá khứ
            (created_contents[0], now - timedelta(days=10), ScheduleStatus.DONE, marketer1.id, "Đã đăng khung giờ trưa 11:30 trên Fanpage"),
            (created_contents[5], now - timedelta(days=14), ScheduleStatus.DONE, marketer2.id, "Đã xuất bản bài chuẩn SEO trên Blog An Nam"),
            (created_contents[11], now - timedelta(days=30), ScheduleStatus.DONE, marketer1.id, "Đã gửi tin nhắn Broadcast Zalo OA"),
            (created_contents[12], now - timedelta(days=22), ScheduleStatus.DONE, marketer1.id, "Đã gửi bản tin Email cho 4.500 hội viên"),
            (created_contents[14], now - timedelta(days=75), ScheduleStatus.DONE, marketer2.id, "Bài mở màn tuần lễ khai trương Quận 1"),
            (created_contents[15], now - timedelta(days=70), ScheduleStatus.DONE, marketer2.id, "Video TikTok check-in ban công Nguyễn Huệ"),
            # Lịch đăng HÔM NAY (để Dashboard hiển thị schedules_today > 0)
            (created_contents[1], now + timedelta(hours=2), ScheduleStatus.PLANNED, marketer1.id, "Đăng kèm bộ 3 ảnh sản phẩm Cold Brew"),
            (created_contents[3], now + timedelta(hours=4), ScheduleStatus.PLANNED, marketer1.id, "Bật bài quảng cáo ưu đãi combo văn phòng"),
            # Lịch đăng những ngày tới trong tháng
            (created_contents[6], now + timedelta(days=1, hours=3), ScheduleStatus.PLANNED, marketer2.id, "Đăng Reels Pour-over Arabica Cầu Đất"),
            (created_contents[2], now + timedelta(days=2, hours=5), ScheduleStatus.PLANNED, marketer1.id, "Chờ duyệt kịch bản TikTok Cold Brew"),
            (created_contents[9], now + timedelta(days=4, hours=2), ScheduleStatus.PLANNED, marketer1.id, "Mở form đăng ký Workshop Cupping cuối tuần"),
            (created_contents[13], now + timedelta(days=6, hours=1), ScheduleStatus.CANCELLED, marketer2.id, "Tạm hoãn chờ cập nhật số lượng ly tre tồn kho"),
        ]
        for c, dt, st, assignee, note in schedules_spec:
            sched = db.execute(
                select(Schedule).where(Schedule.content_id == c.id, Schedule.note == note)
            ).scalar_one_or_none()
            if sched is None:
                db.add(
                    Schedule(
                        content_id=c.id,
                        scheduled_at=dt,
                        status=st,
                        assignee_id=assignee,
                        note=note,
                        done_at=dt if st == ScheduleStatus.DONE else None,
                    )
                )

        # 7. Metrics (Số liệu đa chiến dịch, đa kênh trong 45 ngày, source=SEED)
        print("7. Tạo số liệu hiệu quả cho toàn bộ 5 chiến dịch trên cả 7 kênh (source=SEED)...")
        import random
        random.seed(42)  # Deterministic realistic numbers

        def upsert_seed_metric(
            camp_obj: Campaign,
            ch_obj: Channel,
            m_date,
            views_range: tuple[int, int],
            ctr_range: tuple[float, float],
            cvr_range: tuple[float, float],
            cpc_range: tuple[int, int],
            entered_user_id: int,
        ) -> int:
            views_val = random.randint(*views_range)
            clicks_val = max(1, int(views_val * random.uniform(*ctr_range)))
            conv_val = max(0, int(clicks_val * random.uniform(*cvr_range)))
            cost_val = Decimal(int(clicks_val * random.uniform(*cpc_range)))
            existing = db.execute(
                select(Metric).where(
                    Metric.campaign_id == camp_obj.id,
                    Metric.channel_id == ch_obj.id,
                    Metric.metric_date == m_date,
                )
            ).scalar_one_or_none()
            if existing is None:
                db.add(
                    Metric(
                        campaign_id=camp_obj.id,
                        channel_id=ch_obj.id,
                        metric_date=m_date,
                        views=views_val,
                        clicks=clicks_val,
                        conversions=conv_val,
                        cost=cost_val,
                        source=MetricSource.SEED,
                        entered_by=entered_user_id,
                        import_batch="seed_demo_annam",
                    )
                )
                return 1
            return 0

        metrics_count = 0

        # Chiến dịch 1: Cold Brew (ACTIVE - 41 ngày gần nhất trên FACEBOOK, INSTAGRAM, TIKTOK)
        base_cb = today - timedelta(days=40)
        for i in range(41):
            d = base_cb + timedelta(days=i)
            metrics_count += upsert_seed_metric(camp_coldbrew, channels["FACEBOOK"], d, (1100, 2600), (0.038, 0.068), (0.055, 0.115), (2400, 3600), marketer1.id)
            metrics_count += upsert_seed_metric(camp_coldbrew, channels["INSTAGRAM"], d, (800, 1900), (0.030, 0.055), (0.045, 0.095), (2600, 3900), marketer1.id)
            metrics_count += upsert_seed_metric(camp_coldbrew, channels["TIKTOK"], d, (1800, 4200), (0.025, 0.048), (0.040, 0.085), (1800, 2900), marketer1.id)

        # Chiến dịch 2: Mùa Thu Cầu Đất (ACTIVE - 25 ngày gần nhất trên FACEBOOK, INSTAGRAM, WEBSITE)
        base_aut = today - timedelta(days=24)
        for i in range(25):
            d = base_aut + timedelta(days=i)
            metrics_count += upsert_seed_metric(camp_autum, channels["FACEBOOK"], d, (950, 2200), (0.045, 0.082), (0.030, 0.065), (2100, 3200), marketer2.id)
            metrics_count += upsert_seed_metric(camp_autum, channels["INSTAGRAM"], d, (850, 1950), (0.040, 0.072), (0.028, 0.060), (2300, 3400), marketer2.id)
            metrics_count += upsert_seed_metric(camp_autum, channels["WEBSITE"], d, (450, 1100), (0.065, 0.120), (0.040, 0.085), (1500, 2300), marketer2.id)

        # Chiến dịch 3: Workshop Cupping (PLANNED - 5 ngày chạy thử nghiệm thu hút đăng ký sớm trên FACEBOOK & EMAIL)
        base_ws = today - timedelta(days=4)
        for i in range(5):
            d = base_ws + timedelta(days=i)
            metrics_count += upsert_seed_metric(camp_workshop, channels["FACEBOOK"], d, (600, 1200), (0.042, 0.075), (0.080, 0.150), (2200, 3100), manager.id)
            metrics_count += upsert_seed_metric(camp_workshop, channels["EMAIL"], d, (400, 850), (0.085, 0.140), (0.100, 0.180), (900, 1500), manager.id)

        # Chiến dịch 4: Chăm Sóc Khách Thân Thiết (PAUSED - 30 ngày hoạt động trên ZALO_OA, EMAIL)
        base_loy = today - timedelta(days=45)
        for i in range(30):
            d = base_loy + timedelta(days=i)
            metrics_count += upsert_seed_metric(camp_loyalty, channels["ZALO_OA"], d, (1200, 2500), (0.055, 0.095), (0.060, 0.110), (1600, 2500), marketer1.id)
            metrics_count += upsert_seed_metric(camp_loyalty, channels["EMAIL"], d, (900, 1800), (0.065, 0.115), (0.050, 0.095), (1200, 2000), marketer1.id)

        # Chiến dịch 5: Mừng Khai Trương Quận 1 (COMPLETED - 30 ngày cao điểm trên FACEBOOK, TIKTOK, GOOGLE_ADS)
        base_open = today - timedelta(days=80)
        for i in range(30):
            d = base_open + timedelta(days=i)
            metrics_count += upsert_seed_metric(camp_opening, channels["FACEBOOK"], d, (1600, 3500), (0.045, 0.080), (0.065, 0.125), (2500, 3800), marketer2.id)
            metrics_count += upsert_seed_metric(camp_opening, channels["TIKTOK"], d, (2400, 5200), (0.032, 0.060), (0.050, 0.095), (1900, 2900), marketer2.id)
            metrics_count += upsert_seed_metric(camp_opening, channels["GOOGLE_ADS"], d, (700, 1500), (0.060, 0.110), (0.080, 0.145), (2800, 4200), marketer2.id)

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
                manager.id,
                "CONTENT_SUBMITTED",
                f'{marketer2.full_name} gửi duyệt bài đăng "{created_contents[7].title}"',
                f"/contents/{created_contents[7].id}",
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
                f'Nội dung "{created_contents[4].title}" bị từ chối duyệt: vi phạm từ cấm',
                f"/contents/{created_contents[4].id}",
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
    print("Bắt đầu nạp dữ liệu mẫu MarketFlow...")
    seed_demo_data(reset=args.reset)


if __name__ == "__main__":
    main()
