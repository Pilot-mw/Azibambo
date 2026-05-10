from django.db import models
from django.contrib.auth.models import User
from inventory.models import Product
from django.utils import timezone

class Sale(models.Model):
    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('airtel_money', 'Airtel Money'),
        ('tnm_mpamba', 'TNM Mpamba'),
        ('card', 'Card'),
    ]

    STATUS_CHOICES = [
        ('completed', 'Completed'),
        ('refunded', 'Refunded'),
        ('cancelled', 'Cancelled'),
    ]

    receipt_number = models.CharField(max_length=50, unique=True, editable=False)
    cashier = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='sales')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='cash')
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    change_due = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Sale {self.receipt_number} - {self.cashier}"

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            today = timezone.now().strftime('%Y%m%d')
            last_sale = Sale.objects.filter(receipt_number__startswith=f'RCP-{today}').order_by('-id').first()
            if last_sale:
                last_num = int(last_sale.receipt_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            self.receipt_number = f'RCP-{today}-{new_num:04d}'
        super().save(*args, **kwargs)

class SaleItem(models.Model):
    SELLING_UNITS = [
        ('Bottle', 'Bottle'),
        ('Crate', 'Crate'),
        ('Piece', 'Piece'),
    ]

    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    product_name = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    selling_unit = models.CharField(max_length=20, choices=SELLING_UNITS, default='Bottle')

    def __str__(self):
        unit = f" {self.selling_unit}" if self.selling_unit else ""
        return f"{self.product_name} x {self.quantity}{unit}"
