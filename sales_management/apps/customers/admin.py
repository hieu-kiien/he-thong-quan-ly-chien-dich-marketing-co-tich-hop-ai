from django.contrib import admin

from .models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("full_name", "phone_masked", "group_name", "email")
    list_filter = ("group_name",)
    search_fields = ("full_name", "phone_masked", "email")
    readonly_fields = ("created_at", "updated_at")
