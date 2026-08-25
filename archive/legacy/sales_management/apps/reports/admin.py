from django.contrib import admin

from .models import SalesReportSnapshot


@admin.register(SalesReportSnapshot)
class SalesReportSnapshotAdmin(admin.ModelAdmin):
    list_display = ("from_date", "to_date", "revenue", "created_by", "created_at")
    list_filter = ("from_date", "to_date", "created_at")
    search_fields = ("markdown_context",)
    readonly_fields = ("created_at",)
