from django.contrib import admin

from .models import Campaign, Channel, Content, Metric


@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = ("name", "channel_type", "is_active")
    list_filter = ("channel_type", "is_active")
    search_fields = ("name",)


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "start_date", "end_date", "budget", "created_by")
    list_filter = ("status",)
    search_fields = ("name", "product", "objective")


@admin.register(Content)
class ContentAdmin(admin.ModelAdmin):
    list_display = ("title", "campaign", "channel", "source", "status", "scheduled_at")
    list_filter = ("source", "status", "channel")
    search_fields = ("title", "body")


@admin.register(Metric)
class MetricAdmin(admin.ModelAdmin):
    list_display = ("campaign", "channel", "metric_date", "impressions", "clicks", "conversions", "cost")
    list_filter = ("channel", "metric_date")
