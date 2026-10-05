import os
import sys
from pathlib import Path

# Đảm bảo đường dẫn gốc backend nằm trong sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Cấu hình UTF-8 cho Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from datetime import datetime
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.core.database import engine, SessionLocal, Base, ensure_sqlite_schema_compatibility
from app.core.security import hash_password
from app.models.entities import (
    User, ProductCategory, Product, MarketingChannel,
    Campaign, CampaignMember, MarketingContent, ContentReview,
    MarketingSchedule, CampaignMetric, AILog,
    Workspace, WorkspaceMember, BrandKit
)


def is_production_env() -> bool:
    """Kiểm tra xem hệ thống có đang cấu hình ở môi trường production hay không."""
    env = getattr(settings, "ENVIRONMENT", getattr(settings, "APP_ENV", "development"))
    if str(env).lower() == "production":
        return True
    if os.getenv("ENVIRONMENT") == "production" or os.getenv("APP_ENV") == "production":
        return True
    return False


def reset_db(db_engine=engine):
    """
    Xóa sạch toàn bộ các bảng trong cơ sở dữ liệu.
    TUYỆT ĐỐI BỊ CẤM trong môi trường production.
    """
    if is_production_env():
        raise RuntimeError("Database reset is forbidden in production environment")
    print("[*] Dang xoa toan bo cac bang co so du lieu (drop_all)...")
    Base.metadata.drop_all(bind=db_engine)
    print("[OK] Da xoa toan bo cac bang co so du lieu!")


def init_db(reset: bool = False, db_engine=engine, force: bool = False):
    """
    Khởi tạo cơ sở dữ liệu an toàn.
    - reset=False (mặc định): Tuyệt đối KHÔNG BAO GIỜ gọi drop_all(). Chỉ gọi create_all(),
      đảm bảo tương thích schema SQLite và nạp các thực thể mặc định nếu chưa tồn tại.
    - reset=True: Gọi reset_db() (bị chặn nếu production) trước khi khởi tạo lại.
    - force=True: Ép nạp dữ liệu mẫu (demo) ngay cả khi đang ở môi trường production.
    """
    if reset:
        reset_db(db_engine=db_engine)

    print("[*] Dang khoi tao cac bang co so du lieu...")
    Base.metadata.create_all(bind=db_engine)
    ensure_sqlite_schema_compatibility(db_engine)
    print("[OK] Da tao thanh cong cac bang co so du lieu!")

    # Nạp các thực thể mặc định nếu chưa tồn tại
    if db_engine is not engine:
        CustomSession = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
        session = CustomSession()
        try:
            seed_data(session=session, force=force)
        finally:
            session.close()
    else:
        seed_data(force=force)


def seed_data(session=None, force: bool = False):
    """Nạp các thực thể mặc định nếu chưa tồn tại (Idempotent Non-Destructive Seeding).

    Tự bảo vệ: trên môi trường production, KHÔNG tạo tài khoản demo với mật khẩu mặc định.
    Dùng force=True (ví dụ `python seed/seed_data.py --reset`) để ghi đè.
    """
    if not force and is_production_env():
        # Không raise: Cloudflare runtime vẫn phải chạy được với DB rỗng.
        print(
            "[WARNING] APP_ENV=production: BO QUA nap du lieu mau (tai khoan demo mac dinh). "
            "Dat force=True neu that su muon nap du lieu mau tren production."
        )
        return

    should_close = False
    if session is not None:
        db = session
    else:
        from app.core.database import SessionLocal as DynamicSessionLocal
        db = DynamicSessionLocal()
        should_close = True

    def resolve_password(env_name: str, default: str) -> str:
        """Chuyen gia tri env thanh mat khau an toan.

        PHAI dung `or` chu KHONG dung `os.getenv(name, default)`: khi bien env
        duoc khai bao nhung RONG (dung trong docker-compose: `${VAR:-}`), os.getenv
        tra ve chuoi rong chu KHONG phai gia tri mac dinh. Ket qua: tai khoan demo
        duoc tao voi mat khau RONG, khong ai dang nhap duoc nhung mat khau "trong"
        tai lieu la mat khau sai.

        Nen production KHONG nap du lieu mau (da chan o tren bang is_production_env),
        nen fallback ve mat khau mac dinh o day chi ap dung cho moi truong dev/test
        va co canh bao ro de lau bat ky ai do doc code.
        """
        raw = os.getenv(env_name)
        if raw is not None and not raw.strip():
            print(
                f"[WARNING] {env_name} duoc dat thanh chuoi RONG -> dung mat khau mac dinh "
                f"'{default}' cho tai khoan demo. Hay dat {env_name} that neu khong muon dung."
            )
            raw = None
        resolved = (raw or default).strip()
        if len(resolved) < 8:
            raise RuntimeError(
                f"{env_name} qua ngan ({len(resolved)} ky tu). Mat khau toi thieu 8 ky tu."
            )
        return resolved

    try:
        print("[*] Dang kiem tra va nap du lieu mau (Seed Data)...")

        # 1. Users
        manager = db.query(User).filter(User.email == "manager@gmail.com").first()
        if not manager:
            manager = User(
                email="manager@gmail.com",
                full_name="Nguyễn Văn Quản Lý",
                password_hash=hash_password(resolve_password("MARKETFLOW_MANAGER_PASSWORD", "Manager@123")),
                role="MANAGER",
                status="ACTIVE"
            )
            db.add(manager)

        marketer = db.query(User).filter(User.email == "marketer@gmail.com").first()
        if not marketer:
            marketer = User(
                email="marketer@gmail.com",
                full_name="Trần Thị Marketing",
                password_hash=hash_password(resolve_password("MARKETFLOW_MARKETER_PASSWORD", "Marketer@123")),
                role="MARKETER",
                status="ACTIVE"
            )
            db.add(marketer)

        approver = db.query(User).filter(User.email == "approver@gmail.com").first()
        if not approver:
            approver = User(
                email="approver@gmail.com",
                full_name="Đại Diện Khách Hàng (Approver)",
                password_hash=hash_password(resolve_password("MARKETFLOW_APPROVER_PASSWORD", "Approver@123")),
                role="CLIENT_APPROVER",
                status="ACTIVE"
            )
            db.add(approver)

        db.commit()
        db.refresh(manager)
        db.refresh(marketer)
        db.refresh(approver)
        print(f"   + Đã kiểm tra/khởi tạo 3 tài khoản: {manager.email} (MANAGER), {marketer.email} (MARKETER), {approver.email} (CLIENT_APPROVER)")

        # 1.5. Khởi tạo Default Workspace & Brand Kit
        default_ws = db.query(Workspace).filter(Workspace.id == 1).first()
        if not default_ws:
            default_ws = db.query(Workspace).filter(Workspace.slug == "default-agency").first()
        if not default_ws:
            default_ws = Workspace(
                id=1,
                name="Default Agency Workspace",
                slug="default-agency",
                description="Không gian làm việc mặc định của hệ thống MarketFlow AI",
                owner_id=manager.id,
                status="ACTIVE"
            )
            db.add(default_ws)
            db.commit()
            db.refresh(default_ws)

        for u_obj, role_name in [(manager, "AGENCY_MANAGER"), (marketer, "MARKETER"), (approver, "CLIENT_APPROVER")]:
            membership = db.query(WorkspaceMember).filter(
                WorkspaceMember.workspace_id == default_ws.id,
                WorkspaceMember.user_id == u_obj.id
            ).first()
            if not membership:
                db.add(WorkspaceMember(workspace_id=default_ws.id, user_id=u_obj.id, role=role_name))

        default_brand_kit = db.query(BrandKit).filter(BrandKit.workspace_id == default_ws.id).first()
        if not default_brand_kit:
            default_brand_kit = BrandKit(
                workspace_id=default_ws.id,
                brand_name="MarketFlow AI",
                usp="Nền tảng điều phối chiến dịch tiếp thị thông minh tích hợp AI đa kênh",
                tone_of_voice="Chuyên nghiệp, hiện đại, tin cậy, thúc đẩy hành động",
                banned_keywords_json='["cam kết 100%", "chữa dứt điểm", "làm giàu nhanh", "đa cấp", "hoàn tiền không lý do", "bán phá giá", "trắng da cấp tốc"]'
            )
            db.add(default_brand_kit)
        db.commit()
        print("   + Đã kiểm tra/khởi tạo Workspace mặc định (ID=1) và Brand Kit tích hợp.")

        # 2. Product Categories & Products
        cat_edtech = db.query(ProductCategory).filter(ProductCategory.name == "Công nghệ Giáo dục (EdTech)").first()
        if not cat_edtech:
            cat_edtech = ProductCategory(
                name="Công nghệ Giáo dục (EdTech)",
                description="Các chương trình đào tạo công nghệ và kỹ năng số"
            )
            db.add(cat_edtech)

        cat_saas = db.query(ProductCategory).filter(ProductCategory.name == "Phần mềm Doanh nghiệp (SaaS)").first()
        if not cat_saas:
            cat_saas = ProductCategory(
                name="Phần mềm Doanh nghiệp (SaaS)",
                description="Giải pháp chuyển đổi số cho doanh nghiệp vừa và nhỏ"
            )
            db.add(cat_saas)
        db.commit()
        db.refresh(cat_edtech)
        db.refresh(cat_saas)

        prod_ai_course = db.query(Product).filter(Product.name == "Khóa học Lập trình AI Ứng Dụng").first()
        if not prod_ai_course:
            prod_ai_course = Product(
                category_id=cat_edtech.id,
                name="Khóa học Lập trình AI Ứng Dụng",
                description="Khóa học thực chiến xây dựng ứng dụng AI từ zero đến production.",
                usp="Thực hành dự án thực tế với Gemini & OpenAI, cam kết hỗ trợ 1:1",
                status="ACTIVE"
            )
            db.add(prod_ai_course)

        prod_crm = db.query(Product).filter(Product.name == "Hệ thống Mini CRM Marketing").first()
        if not prod_crm:
            prod_crm = Product(
                category_id=cat_saas.id,
                name="Hệ thống Mini CRM Marketing",
                description="Phần mềm quản lý khách hàng và tự động hóa email marketing.",
                usp="Giao diện kéo thả trực quan, tích hợp AI viết email tự động",
                status="ACTIVE"
            )
            db.add(prod_crm)
        db.commit()
        db.refresh(prod_ai_course)
        db.refresh(prod_crm)
        print("   + Đã kiểm tra/khởi tạo 2 danh mục và 2 sản phẩm mẫu.")

        # 3. Marketing Channels
        default_channels_spec = [
            ("facebook", "Facebook Ads & Fanpage", "Dưới 300 từ, có icon, hashtag và CTA rõ ràng"),
            ("email", "Email Marketing Newsletter", "Tiêu đề dưới 60 ký tự, có lời chào và nút CTA trung tâm"),
            ("blog", "Blog SEO & Website", "Bài viết chuyên sâu chuẩn SEO từ 1000-1500 từ"),
            ("google_ads", "Google Search Ads", "Tiêu đề 30 ký tự, mô tả 90 ký tự, từ khóa chính xác"),
            ("tiktok", "TikTok Short Video & Reels", "Kịch bản video ngắn phân cảnh chi tiết có Hook 3s, Visual action, Voiceover lời thoại và gợi ý âm thanh")
        ]
        channels = []
        for ch_code, ch_name, ch_rules in default_channels_spec:
            ch_obj = db.query(MarketingChannel).filter(MarketingChannel.code == ch_code).first()
            if not ch_obj:
                ch_obj = MarketingChannel(code=ch_code, name=ch_name, format_rules=ch_rules)
                db.add(ch_obj)
                db.commit()
                db.refresh(ch_obj)
            channels.append(ch_obj)
        print("   + Đã kiểm tra/khởi tạo 5 kênh truyền thông mẫu (Facebook, Email, Blog, Google Ads, TikTok).")

        # 4. Campaigns
        campaign_1 = db.query(Campaign).filter(Campaign.name == "Chiến dịch Tuyển sinh Khóa học AI K25").first()
        if not campaign_1:
            campaign_1 = Campaign(
                workspace_id=default_ws.id,
                product_id=prod_ai_course.id,
                owner_id=marketer.id,
                name="Chiến dịch Tuyển sinh Khóa học AI K25",
                objective="Thu hút 50 học viên đăng ký sớm trong vòng 30 ngày",
                audience="Sinh viên CNTT và kỹ sư phần mềm trẻ 20-28 tuổi",
                start_date="2026-09-01",
                end_date="2026-09-30",
                budget=15000000.0,
                status="ACTIVE"
            )
            db.add(campaign_1)
            db.commit()
            db.refresh(campaign_1)

        campaign_2 = db.query(Campaign).filter(Campaign.name == "Chiến dịch Ra mắt Bản thử nghiệm Mini CRM").first()
        if not campaign_2:
            campaign_2 = Campaign(
                workspace_id=default_ws.id,
                product_id=prod_crm.id,
                owner_id=manager.id,
                name="Chiến dịch Ra mắt Bản thử nghiệm Mini CRM",
                objective="Đạt 200 lượt đăng ký dùng thử từ các doanh nghiệp SME",
                audience="Chủ doanh nghiệp nhỏ, Trưởng phòng Marketing",
                start_date="2026-10-01",
                end_date="2026-10-31",
                budget=20000000.0,
                status="PLANNED"
            )
            db.add(campaign_2)
            db.commit()
            db.refresh(campaign_2)

        member = db.query(CampaignMember).filter(
            CampaignMember.campaign_id == campaign_1.id,
            CampaignMember.user_id == marketer.id
        ).first()
        if not member:
            member = CampaignMember(campaign_id=campaign_1.id, user_id=marketer.id, member_role="OWNER")
            db.add(member)
            db.commit()
        print("   + Đã kiểm tra/khởi tạo 2 chiến dịch mẫu.")

        # 5. Marketing Contents
        ch_fb = next(c for c in channels if c.code == "facebook")
        ch_mail = next(c for c in channels if c.code == "email")

        content_1 = db.query(MarketingContent).filter(
            MarketingContent.title == "🚀 Đột phá sự nghiệp cùng Khóa học Lập trình AI 2026!"
        ).first()
        if not content_1:
            content_1 = MarketingContent(
                workspace_id=default_ws.id,
                campaign_id=campaign_1.id,
                channel_id=ch_fb.id,
                created_by=marketer.id,
                title="🚀 Đột phá sự nghiệp cùng Khóa học Lập trình AI 2026!",
                body="Bạn muốn làm chủ công nghệ GenAI thay vì lo lắng bị thay thế?\nKhóa học Lập trình AI Ứng Dụng tại MarketFlow sẽ trang bị cho bạn kiến thức từ nền tảng đến dự án thực tế.\n\nƯu đãi giảm 30% cho 20 bạn đăng ký đầu tiên!",
                cta="Đăng ký ngay hôm nay",
                image_url="https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=1200&auto=format&fit=crop&q=80",
                status="IN_REVIEW",
                source_ids_json='["product_usp", "campaign_brief"]',
                warnings_json='["Nội dung cần Manager phê duyệt trước khi lập lịch"]',
                version_no=1
            )
            db.add(content_1)
            db.commit()
            print("   + Đã tạo nội dung marketing mẫu.")

        # 6. Campaign Metrics
        m1 = db.query(CampaignMetric).filter(
            CampaignMetric.campaign_id == campaign_1.id,
            CampaignMetric.channel_id == ch_fb.id,
            CampaignMetric.metric_date == "2026-09-10"
        ).first()
        if not m1:
            db.add(CampaignMetric(
                campaign_id=campaign_1.id,
                channel_id=ch_fb.id,
                metric_date="2026-09-10",
                views=12500,
                clicks=850,
                conversions=42,
                cost=1850000.0,
                revenue=8400000.0,
                source="seed"
            ))

        m2 = db.query(CampaignMetric).filter(
            CampaignMetric.campaign_id == campaign_1.id,
            CampaignMetric.channel_id == ch_mail.id,
            CampaignMetric.metric_date == "2026-09-11"
        ).first()
        if not m2:
            db.add(CampaignMetric(
                campaign_id=campaign_1.id,
                channel_id=ch_mail.id,
                metric_date="2026-09-11",
                views=3200,
                clicks=410,
                conversions=18,
                cost=500000.0,
                revenue=3600000.0,
                source="seed"
            ))
        db.commit()
        print("   + Đã kiểm tra/nạp chỉ số đo lường hiệu quả (Metrics) mẫu.")

        print("[OK] Nap du lieu ban dau hoan tat thanh cong 100%!")
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Loi khi nap du lieu: {e}")
        raise e
    finally:
        if should_close:
            db.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="MarketFlow AI Database Initializer & Seeder")
    parser.add_argument(
        "--reset",
        action="store_true",
        default=False,
        help="Xóa sạch toàn bộ bảng trước khi tạo lại (chỉ dùng cho môi trường dev/test, bị cấm trên production)"
    )
    args = parser.parse_args()

    if args.reset:
        init_db(reset=True, force=True)
    else:
        init_db(reset=False, force=args.reset)
