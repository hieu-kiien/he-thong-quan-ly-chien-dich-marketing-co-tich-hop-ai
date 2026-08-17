from django.contrib import admin

from .models import GoodsReceipt, GoodsReceiptLine, StockMovement


class GoodsReceiptLineInline(admin.TabularInline):
    model = GoodsReceiptLine
    extra = 1


@admin.register(GoodsReceipt)
class GoodsReceiptAdmin(admin.ModelAdmin):
    list_display = ("id", "supplier", "status", "created_by", "created_at")
    list_filter = ("status", "supplier", "created_at")
    readonly_fields = ("confirmed_at", "created_at", "updated_at")
    inlines = [GoodsReceiptLineInline]


@admin.register(GoodsReceiptLine)
class GoodsReceiptLineAdmin(admin.ModelAdmin):
    list_display = ("receipt", "product", "quantity", "unit_price")
    search_fields = ("product__code", "product__name")


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("product", "movement_type", "quantity", "reason", "occurred_at")
    list_filter = ("movement_type", "occurred_at")
    search_fields = ("product__code", "product__name", "reason")
    readonly_fields = ("occurred_at",)
