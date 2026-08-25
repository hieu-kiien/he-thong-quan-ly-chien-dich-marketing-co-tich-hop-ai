from django.conf import settings
from django.db import models


class SalesReportSnapshot(models.Model):
    from_date = models.DateField()
    to_date = models.DateField()
    revenue = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    top_products = models.JSONField(default=list, blank=True)
    markdown_context = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="sales_report_snapshots",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["from_date", "to_date"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        return f"Sales report {self.from_date} - {self.to_date}"

    def to_markdown_context(self):
        if self.markdown_context:
            return self.markdown_context
        return (
            f"Sales report from {self.from_date} to {self.to_date}: "
            f"revenue {self.revenue}."
        )
