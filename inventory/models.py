from django.db import models
from django.contrib.auth.models import User
from suppliers.models import Supplier

UNIT_TYPE_CHOICES = [
    ('Crate', 'Crate'),
    ('Carton', 'Carton'),
    ('Box', 'Box'),
    ('Piece', 'Piece'),
    ('Bottle', 'Bottle'),
    ('Pack', 'Pack'),
]

SELLING_UNIT_CHOICES = [
    ('Bottle', 'Bottle'),
    ('Crate', 'Crate'),
    ('Piece', 'Piece'),
    ('Pack', 'Pack'),
    ('Bottle/Can', 'Bottle/Can'),
    ('Shot', 'Shot'),
]

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name

class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    name = models.CharField(max_length=200)
    barcode = models.CharField(max_length=100, unique=True, blank=True, null=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    buying_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    selling_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    quantity = models.PositiveIntegerField(default=0, editable=False)
    reorder_level = models.PositiveIntegerField(default=10)
    expiry_date = models.DateField(null=True, blank=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    unit_type = models.CharField(max_length=50, choices=UNIT_TYPE_CHOICES, default='Crate')
    units_per_crate = models.PositiveIntegerField(default=20)
    crate_quantity = models.PositiveIntegerField(default=0)
    units_per_pack = models.PositiveIntegerField(default=6)
    pack_quantity = models.PositiveIntegerField(default=0)
    bottle_quantity = models.PositiveIntegerField(default=0)
    shots_per_bottle = models.PositiveIntegerField(default=1)
    shot_quantity = models.PositiveIntegerField(default=0)
    selling_unit = models.CharField(max_length=50, choices=SELLING_UNIT_CHOICES, default='Bottle')

    class Meta:
        ordering = ['category__name', 'display_order']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.quantity = (
            self.crate_quantity * self.units_per_crate
            + self.pack_quantity * self.units_per_pack
            + self.bottle_quantity * self.shots_per_bottle
            + self.shot_quantity
        )
        super().save(*args, **kwargs)

    @property
    def profit_margin(self):
        if self.buying_price > 0:
            return ((self.selling_price - self.buying_price) / self.buying_price) * 100
        return 0

    @property
    def is_low_stock(self):
        return self.quantity <= self.reorder_level

    @property
    def stock_value(self):
        return self.quantity * self.buying_price

    @property
    def potential_revenue(self):
        return self.quantity * self.selling_price

    @property
    def total_crates(self):
        return self.crate_quantity

    @property
    def total_bottles(self):
        return self.bottle_quantity

    @property
    def display_stock(self):
        if self.unit_type == 'Crate' and self.units_per_crate > 0:
            return f"{self.crate_quantity} Crates ({self.quantity} Bottles)"
        if self.unit_type == 'Pack' and self.units_per_pack > 0:
            return f"{self.pack_quantity} Packs ({self.quantity} Bottles/Cans)"
        if self.unit_type == 'Bottle' and self.shots_per_bottle > 1:
            return f"{self.bottle_quantity} Bottles ({self.quantity} Shots)"
        return str(self.quantity)


class StockSheet(models.Model):
    item = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, related_name='stock_sheets')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    open_stock = models.PositiveIntegerField(default=0)
    order_stock = models.PositiveIntegerField(default=0)
    total_stock = models.PositiveIntegerField(default=0)
    selling_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sold_stock = models.PositiveIntegerField(default=0)
    remaining_stock = models.PositiveIntegerField(default=0)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    date = models.DateField()
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', 'item__display_order']
        verbose_name = 'Stock Sheet'
        verbose_name_plural = 'Stock Sheets'

    def __str__(self):
        return f"{self.item.name if self.item else 'N/A'} - {self.date}"

    def save(self, *args, **kwargs):
        self.total_stock = self.open_stock + self.order_stock
        self.remaining_stock = self.total_stock - self.sold_stock
        self.total_amount = self.sold_stock * float(self.selling_price)
        super().save(*args, **kwargs)
