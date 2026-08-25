from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class Invoice(models.Model):
    class PaymentMethod(models.TextChoices):
        CASH = "cash", "Cash"
        CARD = "card", "Card"
        BANK_TRANSFER = "bank_transfer", "Bank transfer"
        E_WALLET = "e_wallet", "E-wallet"

    class InvoiceStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        CONFIRMED = "confirmed", "Confirmed"
        CANCELLED = "cancelled", "Cancelled"

    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        related_name="invoices",
        null=True,
        blank=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_invoices",
        null=True,
        blank=True,
    )
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_method = models.CharField(
        max_length=30,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CASH,
    )
    status = models.CharField(
        max_length=20,
        choices=InvoiceStatus.choices,
        default=InvoiceStatus.DRAFT,
    )
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["customer", "-created_at"]),
            models.Index(fields=["payment_method", "-created_at"]),
        ]

    def __str__(self):
        return f"Invoice #{self.pk or 'new'}"

    def calculate_total(self):
        subtotal = sum((item.line_total() for item in self.items.all()), Decimal("0"))
        total = subtotal - self.discount
        return max(total, Decimal("0"))

    def confirm(self):
        if self.status == self.InvoiceStatus.CONFIRMED:
            return
        if not self.items.exists():
            raise ValueError("Invoice must have at least one item before confirmation.")
        self.total_amount = self.calculate_total()
        self.status = self.InvoiceStatus.CONFIRMED
        self.confirmed_at = timezone.now()
        self.save(update_fields=["total_amount", "status", "confirmed_at", "updated_at"])


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.PROTECT,
        related_name="invoice_items",
    )
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    line_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        ordering = ["id"]
        indexes = [
            models.Index(fields=["invoice"]),
            models.Index(fields=["product"]),
        ]

    def __str__(self):
        return f"{self.product} x {self.quantity}"

    def line_total(self):
        if self.quantity <= 0:
            raise ValueError("Quantity must be greater than zero.")
        return self.quantity * self.unit_price

    def save(self, *args, **kwargs):
        self.line_amount = self.line_total()
        super().save(*args, **kwargs)
