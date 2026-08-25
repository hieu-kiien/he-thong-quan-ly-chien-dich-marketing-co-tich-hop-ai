from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from io import StringIO

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

    def test_reject_moves_content_to_rejected_and_clears_approval(self):
        content = Content.objects.create(
            campaign=self.campaign,
            channel=self.channel,
            title="Bản nháp cần sửa",
            body="Nội dung chưa đạt yêu cầu.",
            source=Content.Source.AI,
        )
        content.approve(self.user)

        content.reject()

        content.refresh_from_db()
        self.assertEqual(content.status, Content.Status.REJECTED)
        self.assertIsNone(content.approved_by)
        self.assertIsNone(content.approved_at)


class MetricValidationTests(TestCase):
    def setUp(self):
        self.channel = Channel.objects.create(name="Website", channel_type="website")
        self.campaign = Campaign.objects.create(
            name="Kiểm tra metric",
            objective="Đo lường hiệu quả",
            audience="Người dùng thử nghiệm",
            product="Sản phẩm A",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=3),
            budget=Decimal("1000000"),
        )

    def test_metric_rejects_invalid_funnel_order(self):
        metric = Metric(
            campaign=self.campaign,
            channel=self.channel,
            metric_date=date.today(),
            impressions=10,
            clicks=11,
            conversions=2,
            cost=Decimal("100"),
        )

        with self.assertRaises(ValidationError):
            metric.full_clean()


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

    def test_invalid_provider_contract_uses_safe_fallback(self):
        service = MarketingAIService(api_key="secret", provider="provider", base_url="https://example.test")
        invalid_result = {"provider": "provider", "ideas": []}

        with patch.object(service, "_call_openai_compatible", return_value=invalid_result):
            result = service.generate_content_ideas("Ra mắt sản phẩm A", "Facebook")

        self.assertEqual(result["provider"], "fallback")
        self.assertEqual(len(result["ideas"]), 5)
        self.assertTrue(result["needs_human_approval"])

    def test_provider_contract_accepts_valid_reviewable_result(self):
        service = MarketingAIService(api_key="secret", provider="provider", base_url="https://example.test")
        ideas = [
            {"title": "Ý tưởng", "channel": "Facebook", "hook": "Hook", "draft": "Bản nháp", "cta": "CTA"}
            for _ in range(5)
        ]
        valid_result = {
            "provider": "provider",
            "prompt_version": "AI-CAM-001-v1",
            "ideas": ideas,
            "needs_human_approval": True,
        }

        with patch.object(service, "_call_openai_compatible", return_value=valid_result):
            result = service.generate_content_ideas("Ra mắt sản phẩm A", "Facebook")

        self.assertEqual(result["provider"], "provider")
        self.assertEqual(len(result["ideas"]), 5)
        self.assertTrue(result["needs_human_approval"])


class DemoSeedCommandTests(TestCase):
    def test_seed_demo_is_idempotent_and_console_safe(self):
        output = StringIO()

        call_command("seed_demo", stdout=output)
        call_command("seed_demo", stdout=output)

        self.assertIn("Demo marketing data is ready.", output.getvalue())
        self.assertEqual(Channel.objects.filter(name="Facebook").count(), 1)
        self.assertEqual(Campaign.objects.filter(name="Ra mắt sản phẩm A").count(), 1)
        self.assertEqual(Metric.objects.count(), 1)
        self.assertEqual(Content.objects.count(), 1)


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

    def test_staff_can_record_metric_for_campaign(self):
        channel = Channel.objects.create(name="TikTok", channel_type="tiktok")
        campaign = Campaign.objects.create(
            name="Chiến dịch metric",
            objective="Tăng click",
            audience="Người dùng TikTok",
            product="Sản phẩm B",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=5),
            budget=Decimal("2000000"),
        )

        response = self.client.post(
            reverse("campaigns:metric-create", args=[campaign.pk]),
            data={
                "channel": channel.pk,
                "metric_date": date.today().isoformat(),
                "impressions": 100,
                "clicks": 10,
                "conversions": 2,
                "cost": "500000",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Metric.objects.filter(campaign=campaign, channel=channel).exists())

    def test_manager_can_approve_content_from_detail_flow(self):
        channel = Channel.objects.create(name="Email", channel_type="email")
        campaign = Campaign.objects.create(
            name="Chiến dịch duyệt",
            objective="Tăng chuyển đổi",
            audience="Khách hàng đăng ký",
            product="Sản phẩm C",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=5),
            budget=Decimal("2000000"),
        )
        content = Content.objects.create(
            campaign=campaign,
            channel=channel,
            title="Email nháp",
            body="Nội dung cần duyệt.",
            source=Content.Source.AI,
            status=Content.Status.PENDING_REVIEW,
        )

        response = self.client.post(reverse("campaigns:content-approve", args=[content.pk]))

        self.assertEqual(response.status_code, 302)
        content.refresh_from_db()
        self.assertEqual(content.status, Content.Status.APPROVED)
        self.assertEqual(
            self.client.get(reverse("campaigns:detail", args=[campaign.pk])).status_code,
            200,
        )

    def test_ai_endpoint_rejects_empty_brief(self):
        response = self.client.post(reverse("campaigns:ai-ideas"), data={"campaign_brief": ""})

        self.assertEqual(response.status_code, 400)

    def test_dashboard_rejects_authenticated_user_without_marketing_role(self):
        self.user.is_staff = False
        self.user.save(update_fields=["is_staff"])
        self.client.logout()
        self.client.login(username="staff", password="test-password")

        response = self.client.get(reverse("campaigns:dashboard"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_campaign_crud_supports_update_and_delete(self):
        campaign = Campaign.objects.create(
            name="Chiến dịch cũ",
            objective="Mục tiêu cũ",
            audience="Đối tượng cũ",
            product="Sản phẩm cũ",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=5),
            budget=Decimal("2000000"),
        )

        update_response = self.client.post(
            reverse("campaigns:update", args=[campaign.pk]),
            data={
                "name": "Chiến dịch mới",
                "objective": "Mục tiêu mới",
                "audience": "Đối tượng mới",
                "product": "Sản phẩm mới",
                "start_date": date.today().isoformat(),
                "end_date": (date.today() + timedelta(days=7)).isoformat(),
                "budget": "3500000",
                "status": Campaign.Status.ACTIVE,
            },
        )

        self.assertEqual(update_response.status_code, 302)
        campaign.refresh_from_db()
        self.assertEqual(campaign.name, "Chiến dịch mới")
        self.assertEqual(campaign.budget, Decimal("3500000.00"))

        delete_response = self.client.post(reverse("campaigns:delete", args=[campaign.pk]))

        self.assertEqual(delete_response.status_code, 302)
        self.assertFalse(Campaign.objects.filter(pk=campaign.pk).exists())

    def test_channel_crud_supports_update_and_delete(self):
        channel = Channel.objects.create(name="Kênh cũ", channel_type=Channel.Type.OTHER)

        update_response = self.client.post(
            reverse("campaigns:channel-update", args=[channel.pk]),
            data={"name": "Kênh mới", "channel_type": Channel.Type.TIKTOK, "is_active": "on"},
        )

        self.assertEqual(update_response.status_code, 302)
        channel.refresh_from_db()
        self.assertEqual(channel.name, "Kênh mới")
        self.assertEqual(channel.channel_type, Channel.Type.TIKTOK)

        delete_response = self.client.post(reverse("campaigns:channel-delete", args=[channel.pk]))

        self.assertEqual(delete_response.status_code, 302)
        self.assertFalse(Channel.objects.filter(pk=channel.pk).exists())

    def test_content_crud_supports_update_and_delete(self):
        channel = Channel.objects.create(name="Content channel", channel_type=Channel.Type.EMAIL)
        campaign = Campaign.objects.create(
            name="Chiến dịch content",
            objective="Tăng chuyển đổi",
            audience="Khách hàng thử nghiệm",
            product="Sản phẩm content",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=5),
            budget=Decimal("2000000"),
        )
        content = Content.objects.create(
            campaign=campaign,
            channel=channel,
            title="Tiêu đề cũ",
            body="Nội dung cũ",
            source=Content.Source.MANUAL,
        )

        update_response = self.client.post(
            reverse("campaigns:content-update", args=[content.pk]),
            data={
                "channel": channel.pk,
                "title": "Tiêu đề mới",
                "body": "Nội dung mới",
                "content_type": "email",
                "scheduled_at": "",
            },
        )

        self.assertEqual(update_response.status_code, 302)
        content.refresh_from_db()
        self.assertEqual(content.title, "Tiêu đề mới")

        delete_response = self.client.post(reverse("campaigns:content-delete", args=[content.pk]))

        self.assertEqual(delete_response.status_code, 302)
        self.assertFalse(Content.objects.filter(pk=content.pk).exists())

    def test_metric_crud_supports_update_and_delete(self):
        channel = Channel.objects.create(name="Metric channel", channel_type=Channel.Type.WEBSITE)
        campaign = Campaign.objects.create(
            name="Chiến dịch metric CRUD",
            objective="Đo lường",
            audience="Người dùng thử nghiệm",
            product="Sản phẩm metric",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=5),
            budget=Decimal("2000000"),
        )
        metric = Metric.objects.create(
            campaign=campaign,
            channel=channel,
            metric_date=date.today(),
            impressions=100,
            clicks=10,
            conversions=2,
            cost=Decimal("500000"),
        )

        update_response = self.client.post(
            reverse("campaigns:metric-update", args=[metric.pk]),
            data={
                "channel": channel.pk,
                "metric_date": date.today().isoformat(),
                "impressions": 200,
                "clicks": 20,
                "conversions": 4,
                "cost": "750000",
            },
        )

        self.assertEqual(update_response.status_code, 302)
        metric.refresh_from_db()
        self.assertEqual(metric.impressions, 200)
        self.assertEqual(metric.cost, Decimal("750000.00"))

        delete_response = self.client.post(reverse("campaigns:metric-delete", args=[metric.pk]))

        self.assertEqual(delete_response.status_code, 302)
        self.assertFalse(Metric.objects.filter(pk=metric.pk).exists())

    def test_campaign_list_supports_keyword_channel_date_and_sort_filters(self):
        channel = Channel.objects.create(name="Facebook filter", channel_type=Channel.Type.FACEBOOK)
        matching = Campaign.objects.create(
            name="Chiến dịch lọc đúng",
            objective="Tăng nhận diện",
            audience="Người dùng Facebook",
            product="Sản phẩm mục tiêu",
            start_date=date(2026, 8, 20),
            end_date=date(2026, 8, 25),
            budget=Decimal("1000000"),
            status=Campaign.Status.ACTIVE,
        )
        Metric.objects.create(
            campaign=matching,
            channel=channel,
            metric_date=date(2026, 8, 21),
            impressions=100,
            clicks=10,
            conversions=1,
            cost=Decimal("100000"),
        )
        Campaign.objects.create(
            name="Chiến dịch không khớp",
            objective="Mục tiêu khác",
            audience="Đối tượng khác",
            product="Sản phẩm khác",
            start_date=date(2026, 9, 1),
            end_date=date(2026, 9, 5),
            budget=Decimal("1000000"),
            status=Campaign.Status.ACTIVE,
        )

        response = self.client.get(
            reverse("campaigns:list"),
            data={
                "q": "Sản phẩm mục tiêu",
                "status": Campaign.Status.ACTIVE,
                "channel": channel.pk,
                "date_from": "2026-08-19",
                "date_to": "2026-08-26",
                "sort": "name",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["campaigns"]), [matching])

    def test_invalid_campaign_filter_returns_error_message_without_crash(self):
        response = self.client.get(reverse("campaigns:list"), data={"date_from": "not-a-date"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ngày bắt đầu lọc không hợp lệ.")

    def test_dashboard_exposes_aggregated_kpis(self):
        channel = Channel.objects.create(name="Dashboard channel", channel_type=Channel.Type.FACEBOOK)
        campaign = Campaign.objects.create(
            name="Chiến dịch dashboard",
            objective="Tăng click",
            audience="Người dùng thử nghiệm",
            product="Sản phẩm dashboard",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=5),
            budget=Decimal("2000000"),
            status=Campaign.Status.ACTIVE,
        )
        Metric.objects.create(
            campaign=campaign,
            channel=channel,
            metric_date=date.today(),
            impressions=100,
            clicks=25,
            conversions=5,
            cost=Decimal("700000"),
        )
        Content.objects.create(
            campaign=campaign,
            channel=channel,
            title="Nội dung chờ duyệt",
            body="Bản nháp",
            status=Content.Status.PENDING_REVIEW,
        )

        response = self.client.get(reverse("campaigns:dashboard"))

        self.assertEqual(response.status_code, 200)
        summary = response.context["dashboard_summary"]
        self.assertEqual(summary["active_campaigns"], 1)
        self.assertEqual(summary["pending_review"], 1)
        self.assertEqual(summary["clicks"], 25)
        self.assertEqual(summary["cost"], Decimal("700000"))

    def test_dashboard_filters_metrics_by_date_and_builds_channel_report(self):
        channel = Channel.objects.create(name="Dashboard date channel", channel_type=Channel.Type.FACEBOOK)
        campaign = Campaign.objects.create(
            name="Chiến dịch dashboard theo ngày",
            objective="Tăng click",
            audience="Người dùng thử nghiệm",
            product="Sản phẩm dashboard ngày",
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 31),
            budget=Decimal("2000000"),
            status=Campaign.Status.ACTIVE,
        )
        Metric.objects.create(
            campaign=campaign,
            channel=channel,
            metric_date=date(2026, 8, 10),
            impressions=100,
            clicks=25,
            conversions=5,
            cost=Decimal("700000"),
        )
        Metric.objects.create(
            campaign=campaign,
            channel=channel,
            metric_date=date(2026, 8, 20),
            impressions=200,
            clicks=40,
            conversions=8,
            cost=Decimal("900000"),
        )

        response = self.client.get(
            reverse("campaigns:dashboard"),
            data={"date_from": "2026-08-15", "date_to": "2026-08-25"},
        )

        self.assertEqual(response.status_code, 200)
        summary = response.context["dashboard_summary"]
        self.assertEqual(summary["impressions"], 200)
        self.assertEqual(summary["clicks"], 40)
        self.assertEqual(summary["cost"], Decimal("900000"))
        self.assertEqual(response.context["date_from"], "2026-08-15")
        self.assertEqual(response.context["date_to"], "2026-08-25")
        self.assertEqual(len(response.context["channel_report"]), 1)
        self.assertEqual(response.context["channel_report"][0]["clicks"], 40)
        self.assertEqual(response.context["channel_report"][0]["bar_width"], 100)
        self.assertContains(response, "Cập nhật báo cáo")
        self.assertContains(response, "Hiệu quả theo kênh")
        self.assertContains(response, 'role="img"')

    def test_dashboard_rejects_invalid_date_range_without_crash(self):
        response = self.client.get(
            reverse("campaigns:dashboard"),
            data={"date_from": "not-a-date", "date_to": "2026-08-01"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ngày bắt đầu lọc không hợp lệ.")

    def test_campaign_list_paginates_results_and_preserves_filters(self):
        for index in range(9):
            Campaign.objects.create(
                name=f"Chiến dịch phân trang {index}",
                objective="Kiểm tra danh sách",
                audience="Người dùng thử nghiệm",
                product="Sản phẩm phân trang",
                start_date=date(2026, 8, 1),
                end_date=date(2026, 8, 5),
                budget=Decimal("1000000"),
            )

        response = self.client.get(
            reverse("campaigns:list"),
            data={"q": "phân trang", "page": 2},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].number, 2)
        self.assertEqual(response.context["page_obj"].paginator.count, 9)
        self.assertEqual(len(response.context["campaigns"]), 1)
        self.assertEqual(response.context["filter_query"], "q=ph%C3%A2n+trang")
        self.assertContains(response, "Trang 2 / 2")

    def test_channel_delete_handles_protected_data_without_crash(self):
        channel = Channel.objects.create(name="Protected channel", channel_type=Channel.Type.EMAIL)
        campaign = Campaign.objects.create(
            name="Chiến dịch protected",
            objective="Đo lường",
            audience="Người dùng thử nghiệm",
            product="Sản phẩm protected",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=5),
            budget=Decimal("2000000"),
        )
        Metric.objects.create(
            campaign=campaign,
            channel=channel,
            metric_date=date.today(),
            impressions=10,
            clicks=1,
            conversions=0,
            cost=Decimal("100"),
        )

        response = self.client.post(reverse("campaigns:channel-delete", args=[channel.pk]))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Channel.objects.filter(pk=channel.pk).exists())
        self.assertContains(self.client.get(reverse("campaigns:channel-list")), "Không thể xóa kênh", status_code=200)

    def test_marketing_staff_cannot_use_manager_only_delete_routes(self):
        from django.contrib.auth.models import Group

        self.user.is_staff = False
        self.user.save(update_fields=["is_staff"])
        self.user.groups.add(Group.objects.create(name="Marketing Staff"))
        campaign = Campaign.objects.create(
            name="Staff không được xóa",
            objective="Kiểm tra quyền",
            audience="Nhân viên marketing",
            product="Sản phẩm quyền",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=5),
            budget=Decimal("1000000"),
        )

        response = self.client.post(reverse("campaigns:delete", args=[campaign.pk]))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])
        self.assertTrue(Campaign.objects.filter(pk=campaign.pk).exists())
