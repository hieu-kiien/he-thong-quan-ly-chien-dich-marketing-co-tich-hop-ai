from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand

from campaigns.models import Campaign, Channel, Content, Metric


class Command(BaseCommand):
    help = "Tạo dữ liệu demo tối thiểu cho hệ thống marketing AI."

    def handle(self, *args, **options):
        facebook, _ = Channel.objects.get_or_create(
            name="Facebook", defaults={"channel_type": Channel.Type.FACEBOOK}
        )
        email, _ = Channel.objects.get_or_create(
            name="Email", defaults={"channel_type": Channel.Type.EMAIL}
        )
        campaign, _ = Campaign.objects.get_or_create(
            name="Ra mắt sản phẩm A",
            defaults={
                "objective": "Tăng nhận diện thương hiệu và thu thập khách hàng tiềm năng.",
                "audience": "Sinh viên và người đi làm trẻ tại Thái Nguyên.",
                "product": "Sản phẩm A",
                "start_date": date.today(),
                "end_date": date.today() + timedelta(days=14),
                "budget": Decimal("10000000"),
                "status": Campaign.Status.ACTIVE,
            },
        )
        Metric.objects.get_or_create(
            campaign=campaign,
            channel=facebook,
            metric_date=date.today(),
            defaults={"impressions": 1200, "clicks": 96, "conversions": 12, "cost": Decimal("850000")},
        )
        Content.objects.get_or_create(
            campaign=campaign,
            channel=email,
            title="Email giới thiệu sản phẩm A",
            defaults={
                "body": "Bản nháp cần người phụ trách kiểm tra thông tin trước khi sử dụng.",
                "source": Content.Source.AI,
                "status": Content.Status.PENDING_REVIEW,
            },
        )
        # Keep management-command output ASCII-safe on Windows consoles whose
        # active code page may not be UTF-8. The command's data changes are
        # already verified separately; this message must not turn a successful
        # seed into a UnicodeEncodeError.
        self.stdout.write(self.style.SUCCESS("Demo marketing data is ready."))
