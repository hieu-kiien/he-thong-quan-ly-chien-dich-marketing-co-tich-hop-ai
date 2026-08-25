from django.contrib import admin

from .models import Supplier


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "email", "tax_code")
    search_fields = ("name", "phone", "email", "tax_code")
    readonly_fields = ("created_at", "updated_at")
