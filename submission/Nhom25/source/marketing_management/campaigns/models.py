from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Sum


class Channel(models.Model):
    class Type(models.TextChoices):
        FACEBOOK = "facebook", "Facebook"
        EMAIL = "email", "Email"
        TIKTOK = "tiktok", "TikTok"
        WEBSITE = "website", "Website"
        OTHER = "other", "Khác"

    name = models.CharField("Tên kênh", max_length=100, unique=True)
    channel_type = models.CharField("Loại kênh", max_length=20, choices=Type.choices, default=Type.OTHER)
    is_active = models.BooleanField("Đang hoạt động", default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Kênh truyền thông"
        verbose_name_plural = "Kênh truyền thông"

    def __str__(self):
        return self.name


class Campaign(models.Model):
    class Status(models.TextChoices):
        PLANNED = "planned", "Đã lập kế hoạch"
        ACTIVE = "active", "Đang chạy"
        PAUSED = "paused", "Tạm dừng"
        COMPLETED = "completed", "Đã kết thúc"
        ARCHIVED = "archived", "Lưu trữ"

    name = models.CharField("Tên chiến dịch", max_length=200)
    objective = models.TextField("Mục tiêu")
    audience = models.TextField("Đối tượng mục tiêu")
    product = models.CharField("Sản phẩm/dịch vụ", max_length=200)
    start_date = models.DateField("Ngày bắt đầu")
    end_date = models.DateField("Ngày kết thúc")
    budget = models.DecimalField(
        "Ngân sách",
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    status = models.CharField("Trạng thái", max_length=20, choices=Status.choices, default=Status.PLANNED)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="marketing_campaigns",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Chiến dịch marketing"
        verbose_name_plural = "Chiến dịch marketing"

    def __str__(self):
        return self.name

    def clean(self):
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError({"end_date": "Ngày kết thúc phải sau hoặc bằng ngày bắt đầu."})

    @staticmethod
    def _percent(value, total):
        if not total:
            return Decimal("0.00")
        return (Decimal(value) * Decimal("100") / Decimal(total)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def performance_summary(self):
        totals = self.metrics.aggregate(
            impressions=Sum("impressions"),
            clicks=Sum("clicks"),
            conversions=Sum("conversions"),
            cost=Sum("cost"),
        )
        impressions = totals["impressions"] or 0
        clicks = totals["clicks"] or 0
        conversions = totals["conversions"] or 0
        cost = totals["cost"] or Decimal("0")
        return {
            "impressions": impressions,
            "clicks": clicks,
            "conversions": conversions,
            "cost": cost,
            "ctr_percent": self._percent(clicks, impressions),
            "conversion_rate_percent": self._percent(conversions, clicks),
            "cost_per_conversion": (cost / conversions).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if conversions
            else Decimal("0.00"),
        }


class Content(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Bản nháp"
        PENDING_REVIEW = "pending_review", "Chờ duyệt"
        APPROVED = "approved", "Đã duyệt"
        REJECTED = "rejected", "Từ chối"
        PUBLISHED = "published", "Đã đăng"

    class Source(models.TextChoices):
        MANUAL = "manual", "Con người viết"
        AI = "ai", "AI sinh"

    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="contents")
    channel = models.ForeignKey(Channel, on_delete=models.PROTECT, related_name="contents")
    title = models.CharField("Tiêu đề", max_length=200)
    body = models.TextField("Nội dung")
    content_type = models.CharField("Định dạng", max_length=30, default="post")
    status = models.CharField("Trạng thái duyệt", max_length=20, choices=Status.choices, default=Status.DRAFT)
    source = models.CharField("Nguồn", max_length=10, choices=Source.choices, default=Source.MANUAL)
    scheduled_at = models.DateTimeField("Thời điểm đăng", null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_marketing_contents",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Nội dung marketing"
        verbose_name_plural = "Nội dung marketing"

    def __str__(self):
        return f"{self.title} — {self.channel.name}"

    def approve(self, user):
        from django.utils import timezone

        self.status = self.Status.APPROVED
        self.approved_by = user
        self.approved_at = timezone.now()
        self.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])

    def reject(self):
        self.status = self.Status.REJECTED
        self.approved_by = None
        self.approved_at = None
        self.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])

    def publish(self):
        if self.status != self.Status.APPROVED:
            raise ValidationError("Nội dung phải được người phụ trách duyệt trước khi đăng.")
        self.status = self.Status.PUBLISHED
        self.save(update_fields=["status", "updated_at"])


class Metric(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="metrics")
    channel = models.ForeignKey(Channel, on_delete=models.PROTECT, related_name="metrics")
    metric_date = models.DateField("Ngày ghi nhận")
    impressions = models.PositiveIntegerField("Lượt xem", default=0)
    clicks = models.PositiveIntegerField("Lượt click", default=0)
    conversions = models.PositiveIntegerField("Lượt chuyển đổi", default=0)
    cost = models.DecimalField(
        "Chi phí",
        max_digits=15,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
    )

    class Meta:
        ordering = ["-metric_date", "channel__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["campaign", "channel", "metric_date"],
                name="unique_campaign_channel_metric_day",
            )
        ]
        verbose_name = "Chỉ số chiến dịch"
        verbose_name_plural = "Chỉ số chiến dịch"

    def __str__(self):
        return f"{self.campaign.name} — {self.channel.name} — {self.metric_date}"

    def clean(self):
        errors = {}
        if self.clicks > self.impressions:
            errors["clicks"] = "Lượt click không thể lớn hơn lượt xem."
        if self.conversions > self.clicks:
            errors["conversions"] = "Lượt chuyển đổi không thể lớn hơn lượt click."
        if errors:
            raise ValidationError(errors)
