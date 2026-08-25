from django.conf import settings
from django.db import models, transaction
from django.utils import timezone


class GoodsReceipt(models.Model):
    class ReceiptStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        CONFIRMED = "confirmed", "Confirmed"
        CANCELLED = "cancelled", "Cancelled"

    supplier = models.ForeignKey(
        "suppliers.Supplier",
        on_delete=models.SET_NULL,
        related_name="goods_receipts",
        null=True,
        blank=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="goods_receipts",
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=ReceiptStatus.choices,
        default=ReceiptStatus.DRAFT,
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["supplier", "-created_at"]),
        ]

    def __str__(self):
        return f"Receipt #{self.pk or 'new'}"

    @transaction.atomic
    def confirm(self):
        if self.status == self.ReceiptStatus.CONFIRMED:
            return
        if not self.lines.exists():
            raise ValueError("Goods receipt must have at least one line.")
        for line in self.lines.select_related("product"):
            movement = StockMovement.objects.create(
                product=line.product,
                movement_type=StockMovement.MovementType.IN,
                quantity=line.quantity,
                unit_price=line.unit_price,
                reason="goods_receipt",
                source_receipt=self,
            )
            movement.apply_to(line.product)
        self.status = self.ReceiptStatus.CONFIRMED
        self.confirmed_at = timezone.now()
        self.save(update_fields=["status", "confirmed_at", "updated_at"])


class GoodsReceiptLine(models.Model):
    receipt = models.ForeignKey(GoodsReceipt, on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.PROTECT,
        related_name="receipt_lines",
    )
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ["id"]
        indexes = [
            models.Index(fields=["receipt"]),
            models.Index(fields=["product"]),
        ]

    def __str__(self):
        return f"{self.product} x {self.quantity}"


class StockMovement(models.Model):
    class MovementType(models.TextChoices):
        IN = "in", "In"
        OUT = "out", "Out"
        ADJUSTMENT = "adjustment", "Adjustment"

    product = models.ForeignKey(
        "products.Product",
        on_delete=models.PROTECT,
        related_name="stock_movements",
    )
    movement_type = models.CharField(max_length=20, choices=MovementType.choices)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    reason = models.CharField(max_length=150)
    source_invoice = models.ForeignKey(
        "sales.Invoice",
        on_delete=models.SET_NULL,
        related_name="stock_movements",
        null=True,
        blank=True,
    )
    source_receipt = models.ForeignKey(
        GoodsReceipt,
        on_delete=models.SET_NULL,
        related_name="stock_movements",
        null=True,
        blank=True,
    )
    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-occurred_at"]
        indexes = [
            models.Index(fields=["product", "-occurred_at"]),
            models.Index(fields=["movement_type", "-occurred_at"]),
        ]

    def __str__(self):
        return f"{self.product} {self.movement_type} {self.quantity}"

    def apply_to(self, product=None):
        target = product or self.product
        if self.movement_type == self.MovementType.IN:
            target.stock_qty += self.quantity
        elif self.movement_type == self.MovementType.OUT:
            if target.stock_qty < self.quantity:
                raise ValueError("Not enough stock for this movement.")
            target.stock_qty -= self.quantity
        else:
            target.stock_qty = self.quantity
        target.save(update_fields=["stock_qty", "updated_at"])
