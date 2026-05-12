from django.db import models
from django.contrib.auth.models import User

class Supplier(models.Model):
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    outstanding_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

WAREHOUSE_UNIT_CHOICES = [
    ('Crate', 'Crate'),
    ('Pack', 'Pack'),
    ('Bottle', 'Bottle'),
    ('Container', 'Wine Container'),
]


class Purchase(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, related_name='purchases')
    product = models.ForeignKey('inventory.Product', on_delete=models.SET_NULL, null=True)
    warehouse_unit_type = models.CharField(max_length=20, choices=WAREHOUSE_UNIT_CHOICES, default='Crate')
    quantity = models.PositiveIntegerField(help_text='Quantity in warehouse units (crates/packs/bottles/containers)')
    converted_quantity = models.PositiveIntegerField(default=0, editable=False, help_text='Auto-converted to base stock units')
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    purchased_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    branch = models.ForeignKey('branches.Branch', on_delete=models.SET_NULL, null=True, blank=True, related_name='purchases')
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"Purchase from {self.supplier} - {self.date}"

    @property
    def balance(self):
        return self.total_amount - self.paid_amount

    @property
    def warehouse_display(self):
        return f"{self.quantity} {self.get_warehouse_unit_type_display()}"

    @property
    def selling_display(self):
        if not self.product:
            return f"{self.converted_quantity} units"
        return f"{self.converted_quantity} {self.product.selling_unit_label}"
