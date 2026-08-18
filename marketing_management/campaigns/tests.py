from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from campaigns.ai_service import MarketingAIService
from campaigns.models import Campaign, Channel, Content, Metric


class CampaignModelTests(TestCase):
    def setUp(self):
        self.channel = Channel.objects.create(name="Facebook", channel_type="facebook")
        self.campaign = Campaign.objects.create(
            name="Ra mắt sản phẩm A",
            objective="Tăng nhận diện thương hiệu",
            audience="Sinh viên và người đi làm trẻ",
            product="Sản phẩm A",
            start_date=date(2026, 8, 18),
            end_date=date(2026, 8, 31),
            budget=Decimal("10000000"),
        )

    def test_performance_summary_aggregates_metrics_and_handles_rates(self):
        Metric.objects.create(
            campaign=self.campaign,
            channel=self.channel,
            metric_date=date(2026, 8, 18),
            impressions=1000,
            clicks=80,
            conversions=8,
            cost=Decimal("800000"),
        )
        Metric.objects.create(
            campaign=self.campaign,
            channel=self.channel,
            metric_date=date(2026, 8, 19),
            impressions=500,
            clicks=20,
            conversions=2,
            cost=Decimal("200000"),
        )

        summary = self.campaign.performance_summary()

        self.assertEqual(summary["impressions"], 1500)
        self.assertEqual(summary["clicks"], 100)
        self.assertEqual(summary["conversions"], 10)
        self.assertEqual(summary["cost"], Decimal("1000000"))
        self.assertEqual(summary["ctr_percent"], Decimal("6.67"))
        self.assertEqual(summary["conversion_rate_percent"], Decimal("10.00"))
        self.assertEqual(summary["cost_per_conversion"], Decimal("100000"))


class ContentApprovalTests(TestCase):
    def setUp(self):
        self.channel = Channel.objects.create(name="Email", channel_type="email")
        self.campaign = Campaign.objects.create(
            name="Khuyến mãi tháng 8",
            objective="Tăng chuyển đổi",
            audience="Khách hàng đã đăng ký",
            product="Gói dịch vụ A",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=7),
            budget=Decimal("3000000"),
        )
        self.user = get_user_model().objects.create_user(
            username="marketing-manager",
            password="test-password",
        )

    def test_ai_content_requires_human_approval_before_publish(self):
        content = Content.objects.create(
            campaign=self.campaign,
            channel=self.channel,
            title="Bản nháp AI",
            body="Nội dung cần người phụ trách kiểm duyệt.",
            source=Content.Source.AI,
        )

        with self.assertRaises(ValidationError):
            content.publish()

        content.approve(self.user)
        content.refresh_from_db()
        self.assertEqual(content.status, Content.Status.APPROVED)
        self.assertEqual(content.approved_by, self.user)

        content.publish()
        content.refresh_from_db()
        self.assertEqual(content.status, Content.Status.PUBLISHED)


class MarketingAIServiceTests(TestCase):
    def test_fallback_returns_five_reviewable_ideas_without_external_api(self):
        service = MarketingAIService(api_key="")
        result = service.generate_content_ideas(
            campaign_brief="Ra mắt sản phẩm A cho người trẻ",
            channel_name="Facebook",
            tone="thân thiện",
            count=5,
        )

        self.assertEqual(result["provider"], "fallback")
        self.assertEqual(len(result["ideas"]), 5)
        self.assertTrue(result["needs_human_approval"])
        self.assertTrue(all("Facebook" in idea["channel"] for idea in result["ideas"]))


class CampaignViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="staff",
            password="test-password",
            is_staff=True,
        )
        self.client.login(username="staff", password="test-password")

    def test_campaign_list_is_available_to_authenticated_marketing_staff(self):
        Campaign.objects.create(
            name="Chiến dịch thử nghiệm",
            objective="Tăng nhận diện",
            audience="Khách hàng mục tiêu",
            product="Sản phẩm A",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=5),
            budget=Decimal("1000000"),
        )

        response = self.client.get(reverse("campaigns:list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Chiến dịch thử nghiệm")
