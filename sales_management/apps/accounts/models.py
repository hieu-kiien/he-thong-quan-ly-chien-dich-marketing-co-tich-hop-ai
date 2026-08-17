from django.conf import settings
from django.db import models


class Role(models.Model):
    role_code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=100)
    permissions = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["role_code"]
        indexes = [
            models.Index(fields=["role_code"]),
        ]

    def __str__(self):
        return f"{self.role_code} - {self.name}"

    def allows(self, permission):
        return permission in self.permissions


class UserProfile(models.Model):
    class UserStatus(models.TextChoices):
        ACTIVE = "active", "Active"
        LOCKED = "locked", "Locked"
        INACTIVE = "inactive", "Inactive"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    status = models.CharField(
        max_length=20,
        choices=UserStatus.choices,
        default=UserStatus.ACTIVE,
    )
    roles = models.ManyToManyField(Role, related_name="users", blank=True)

    class Meta:
        ordering = ["user__username"]
        indexes = [
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return self.user.get_username()

    def has_role(self, role_code):
        if self.status != self.UserStatus.ACTIVE:
            return False
        return self.roles.filter(role_code=role_code).exists()

    def has_permission(self, permission):
        if self.status != self.UserStatus.ACTIVE:
            return False
        return any(role.allows(permission) for role in self.roles.all())


class AuditLog(models.Model):
    class EventType(models.TextChoices):
        LOGIN = "login", "Login"
        LOGOUT = "logout", "Logout"
        BUSINESS = "business", "Business"
        AUTHORIZATION = "authorization", "Authorization"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
        null=True,
        blank=True,
    )
    event_type = models.CharField(max_length=30, choices=EventType.choices)
    action = models.CharField(max_length=100)
    message = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["event_type", "-created_at"]),
            models.Index(fields=["user", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.event_type}: {self.action}"


class AIEventLog(models.Model):
    class AIStatus(models.TextChoices):
        SUCCESS = "success", "Success"
        FALLBACK = "fallback", "Fallback"
        ERROR = "error", "Error"
        HUMAN_REVIEW = "human_review", "Human review"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="ai_event_logs",
        null=True,
        blank=True,
    )
    purpose = models.CharField(max_length=80)
    prompt_summary = models.CharField(max_length=255)
    response_summary = models.TextField(blank=True)
    status = models.CharField(max_length=30, choices=AIStatus.choices)
    fallback_message = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["purpose", "-created_at"]),
            models.Index(fields=["status", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.purpose} - {self.status}"
