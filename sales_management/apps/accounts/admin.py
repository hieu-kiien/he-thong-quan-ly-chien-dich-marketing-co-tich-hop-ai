from django.contrib import admin

from .models import AIEventLog, AuditLog, Role, UserProfile


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("role_code", "name")
    search_fields = ("role_code", "name")


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "status")
    list_filter = ("status", "roles")
    search_fields = ("user__username", "user__email")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("event_type", "action", "user", "created_at")
    list_filter = ("event_type", "created_at")
    search_fields = ("action", "message", "user__username")
    readonly_fields = ("created_at",)


@admin.register(AIEventLog)
class AIEventLogAdmin(admin.ModelAdmin):
    list_display = ("purpose", "status", "user", "created_at")
    list_filter = ("purpose", "status", "created_at")
    search_fields = ("purpose", "prompt_summary", "response_summary")
    readonly_fields = ("created_at",)
