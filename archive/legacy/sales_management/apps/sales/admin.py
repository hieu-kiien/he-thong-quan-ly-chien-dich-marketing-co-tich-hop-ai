from django.contrib import admin

from .models import Invoice, InvoiceItem


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "payment_method", "status", "total_amount", "created_at")
    list_filter = ("payment_method", "status", "created_at")
    search_fields = ("customer__full_name",)
    readonly_fields = ("total_amount", "confirmed_at", "created_at", "updated_at")
    inlines = [InvoiceItemInline]


@admin.register(InvoiceItem)
class InvoiceItemAdmin(admin.ModelAdmin):
    list_display = ("invoice", "product", "quantity", "unit_price", "line_amount")
    list_filter = ("product",)
    search_fields = ("product__code", "product__name")
