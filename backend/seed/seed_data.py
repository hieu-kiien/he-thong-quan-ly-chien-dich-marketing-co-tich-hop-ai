import sys
from pathlib import Path

# Đảm bảo đường dẫn gốc backend nằm trong sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Cấu hình UTF-8 cho Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from datetime import datetime
from app.core.database import engine, SessionLocal, Base, ensure_sqlite_schema_compatibility
from app.core.security import hash_password
from app.models.entities import (
    User, ProductCategory, Product, MarketingChannel,
    Campaign, CampaignMember, MarketingContent, ContentReview,
    MarketingSchedule, CampaignMetric, AILog,
    Workspace, WorkspaceMember, BrandKit
)

def init_db():
    print("[*] Dang khoi tao cac bang co so du lieu...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    ensure_sqlite_schema_compatibility(engine)
    print("[OK] Da tao thanh cong cac bang co so du lieu!")

def seed_data(session=None):
    should_close = False
    if session is not None:
        db = session
    else:
        db = SessionLocal()
        should_close = True
    try:
        print("[*] Dang nap du lieu mau (Seed Data)...")

        # 1. Users
        manager = User(
            email="manager@ictu.edu.vn",
            full_name="Nguyễn Văn Quản Lý",
            password_hash=hash_password("Manager@123"),
            role="MANAGER",
            status="ACTIVE"
        )
        marketer = User(
            email="marketer@ictu.edu.vn",
            full_name="Trần Thị Marketing",
            password_hash=hash_password("Marketer@123"),
            role="MARKETER",
            status="ACTIVE"
        )
        approver = User(
            email="approver@ictu.edu.vn",
            full_name="Đại Diện Khách Hàng (Approver)",
            password_hash=hash_password("Approver@123"),
            role="CLIENT_APPROVER",
            status="ACTIVE"
        )
        db.add_all([manager, marketer, approver])
        db.commit()
        db.refresh(manager)
        db.refresh(marketer)
        db.refresh(approver)
        print(f"   + Đã tạo 3 tài khoản: {manager.email} (MANAGER), {marketer.email} (MARKETER), {approver.email} (CLIENT_APPROVER)")

        # 1.5. Khởi tạo Default Workspace & Brand Kit
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

        ws_mem_mgr = WorkspaceMember(workspace_id=default_ws.id, user_id=manager.id, role="AGENCY_MANAGER")
        ws_mem_mkt = WorkspaceMember(workspace_id=default_ws.id, user_id=marketer.id, role="MARKETER")
        ws_mem_app = WorkspaceMember(workspace_id=default_ws.id, user_id=approver.id, role="CLIENT_APPROVER")
        db.add_all([ws_mem_mgr, ws_mem_mkt, ws_mem_app])

        default_brand_kit = BrandKit(
            workspace_id=default_ws.id,
            brand_name="MarketFlow AI",
            usp="Nền tảng điều phối chiến dịch tiếp thị thông minh tích hợp AI đa kênh",
            tone_of_voice="Chuyên nghiệp, hiện đại, tin cậy, thúc đẩy hành động",
            banned_keywords_json='["cam kết 100%", "chữa dứt điểm", "làm giàu nhanh", "đa cấp", "hoàn tiền không lý do", "bán phá giá", "trắng da cấp tốc"]'
        )
        db.add(default_brand_kit)
        db.commit()
        print("   + Đã tạo Workspace mặc định (ID=1) và Brand Kit tích hợp.")


        # 2. Product Categories & Products
        cat_edtech = ProductCategory(
            name="Công nghệ Giáo dục (EdTech)",
            description="Các chương trình đào tạo công nghệ và kỹ năng số"
        )
        cat_saas = ProductCategory(
            name="Phần mềm Doanh nghiệp (SaaS)",
            description="Giải pháp chuyển đổi số cho doanh nghiệp vừa và nhỏ"
        )
        db.add_all([cat_edtech, cat_saas])
        db.commit()

        prod_ai_course = Product(
            category_id=cat_edtech.id,
            name="Khóa học Lập trình AI Ứng Dụng",
            description="Khóa học thực chiến xây dựng ứng dụng AI từ zero đến production.",
            usp="Thực hành dự án thực tế với Gemini & OpenAI, cam kết hỗ trợ 1:1",
            status="ACTIVE"
        )
        prod_crm = Product(
            category_id=cat_saas.id,
            name="Hệ thống Mini CRM Marketing",
            description="Phần mềm quản lý khách hàng và tự động hóa email marketing.",
            usp="Giao diện kéo thả trực quan, tích hợp AI viết email tự động",
            status="ACTIVE"
        )
        db.add_all([prod_ai_course, prod_crm])
        db.commit()
        print("   + Đã tạo 2 danh mục và 2 sản phẩm mẫu.")

        # 3. Marketing Channels
        channels = [
            MarketingChannel(code="facebook", name="Facebook Ads & Fanpage", format_rules="Dưới 300 từ, có icon, hashtag và CTA rõ ràng"),
            MarketingChannel(code="email", name="Email Marketing Newsletter", format_rules="Tiêu đề dưới 60 ký tự, có lời chào và nút CTA trung tâm"),
            MarketingChannel(code="blog", name="Blog SEO & Website", format_rules="Bài viết chuyên sâu chuẩn SEO từ 1000-1500 từ"),
            MarketingChannel(code="google_ads", name="Google Search Ads", format_rules="Tiêu đề 30 ký tự, mô tả 90 ký tự, từ khóa chính xác"),
            MarketingChannel(code="tiktok", name="TikTok Short Video & Reels", format_rules="Kịch bản video ngắn phân cảnh chi tiết có Hook 3s, Visual action, Voiceover lời thoại và gợi ý âm thanh")
        ]
        db.add_all(channels)
        db.commit()
        print("   + Đã tạo 5 kênh truyền thông mẫu (Facebook, Email, Blog, Google Ads, TikTok).")

        # 4. Campaigns
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
        db.add_all([campaign_1, campaign_2])
        db.commit()

        # Members
        member = CampaignMember(campaign_id=campaign_1.id, user_id=marketer.id, member_role="OWNER")
        db.add(member)
        db.commit()
        print("   + Đã tạo 2 chiến dịch mẫu.")

        # 5. Marketing Contents
        ch_fb = next(c for c in channels if c.code == "facebook")
        ch_mail = next(c for c in channels if c.code == "email")

        content_1 = MarketingContent(
            workspace_id=default_ws.id,
            campaign_id=campaign_1.id,
            channel_id=ch_fb.id,
            created_by=marketer.id,
            title="🚀 Đột phá sự nghiệp cùng Khóa học Lập trình AI 2026!",
            body="Bạn muốn làm chủ công nghệ GenAI thay vì lo lắng bị thay thế?\nKhóa học Lập trình AI Ứng Dụng tại ICTU sẽ trang bị cho bạn kiến thức từ nền tảng đến dự án thực tế.\n\nƯu đãi giảm 30% cho 20 bạn đăng ký đầu tiên!",
            cta="Đăng ký ngay hôm nay",
            image_url="https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=1200&auto=format&fit=crop&q=80",
            status="IN_REVIEW",
            source_ids_json='["product_usp", "campaign_brief"]',
            warnings_json='["Nội dung cần Manager phê duyệt trước khi lập lịch"]',
            version_no=1
        )
        db.add(content_1)
        db.commit()


        # 6. Campaign Metrics
        metrics = [
            CampaignMetric(
                campaign_id=campaign_1.id,
                channel_id=ch_fb.id,
                metric_date="2026-09-10",
                views=12500,
                clicks=850,
                conversions=42,
                cost=1850000.0,
                revenue=8400000.0
            ),
            CampaignMetric(
                campaign_id=campaign_1.id,
                channel_id=ch_mail.id,
                metric_date="2026-09-11",
                views=3200,
                clicks=410,
                conversions=18,
                cost=500000.0,
                revenue=3600000.0
            )
        ]
        db.add_all(metrics)
        db.commit()
        print("   + Đã nạp chỉ số đo lường hiệu quả (Metrics) mẫu.")

        print("[OK] Nap du lieu ban dau hoan tat thanh cong 100%!")
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Loi khi nap du lieu: {e}")
        raise e
    finally:
        if should_close:
            db.close()

if __name__ == "__main__":
    init_db()
    seed_data()
