from django.db import models


class Category(models.Model):
    class CategoryStatus(models.TextChoices):
        ACTIVE = "active", "Hoạt động"
        INACTIVE = "inactive", "Không hoạt động"

    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=20,
        choices=CategoryStatus.choices,
        default=CategoryStatus.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["status", "name"]),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"

    def rename(self, name):
        if not name or not name.strip():
            raise ValueError("Category name must not be empty.")
        self.name = name.strip()
