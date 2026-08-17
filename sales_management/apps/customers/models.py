from django.db import models


class Customer(models.Model):
    full_name = models.CharField(max_length=150)
    phone_masked = models.CharField(max_length=30, blank=True)
    group_name = models.CharField(max_length=80, blank=True)
    email = models.EmailField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["full_name"]
        indexes = [
            models.Index(fields=["full_name"]),
            models.Index(fields=["group_name"]),
        ]

    def __str__(self):
        return self.full_name

    def add_purchase(self, invoice):
        if invoice.status != invoice.InvoiceStatus.CONFIRMED:
            raise ValueError("Only confirmed invoices can be added to purchase history.")
        invoice.customer = self
        invoice.save(update_fields=["customer", "updated_at"])
