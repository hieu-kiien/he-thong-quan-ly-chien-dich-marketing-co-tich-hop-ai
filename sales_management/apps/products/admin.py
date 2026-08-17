from django.contrib import admin

from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "category", "sale_price", "stock_qty", "status")
    list_filter = ("status", "category")
    search_fields = ("code", "name", "description")
    readonly_fields = ("created_at", "updated_at")
