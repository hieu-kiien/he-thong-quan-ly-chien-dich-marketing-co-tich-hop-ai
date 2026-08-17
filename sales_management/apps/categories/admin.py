from django.contrib import admin

from .models import Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "status", "created_at", "updated_at")
    list_filter = ("status",)
    search_fields = ("code", "name", "description")
    readonly_fields = ("created_at", "updated_at")
