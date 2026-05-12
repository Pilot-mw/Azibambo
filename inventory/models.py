from django.db import models
from django.contrib.auth.models import User
from suppliers.models import Supplier
from .services.conversion_engine import (
    get_conversion_rate, get_purchase_unit, get_selling_unit,
    get_purchase_unit_label, get_selling_unit_label,
    convert_purchase_to_base as engine_purchase_to_base,
    convert_base_to_warehouse as engine_base_to_warehouse,
)

PURCHASE_UNIT_CHOICES = [
    ('Crate', 'Crate'),
    ('Pack', 'Pack'),
    ('Bottle', 'Bottle'),
    ('Container', 'Container'),
]

UNIT_TYPE_CHOICES = [
    ('Crate', 'Crate'),
    ('Carton', 'Carton'),
    ('Box', 'Box'),
    ('Piece', 'Piece'),
    ('Bottle', 'Bottle'),
    ('Pack', 'Pack'),
    ('wine_glass', 'Wine (Liters → Glasses)'),
]

SELLING_UNIT_CHOICES = [
    ('Bottle', 'Bottle'),
    ('Crate', 'Crate'),
    ('Piece', 'Piece'),
    ('Pack', 'Pack'),
    ('Bottle/Can', 'Bottle/Can'),
    ('Shot', 'Shot'),
    ('Glass', 'Glass'),
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
    branch = models.ForeignKey('branches.Branch', on_delete=models.CASCADE, null=True, blank=True, related_name='products')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    unit_type = models.CharField(max_length=50, choices=UNIT_TYPE_CHOICES, default='Crate')
    liters_per_unit = models.PositiveIntegerField(default=5, help_text='Liters per wine container')
    glasses_per_liter = models.PositiveIntegerField(default=28, help_text='Glasses per liter (for wine products)')
    pack_size = models.PositiveIntegerField(default=6, help_text='Bottles per pack')
    crate_size = models.PositiveIntegerField(default=20, help_text='Bottles per crate')
    units_per_crate = models.PositiveIntegerField(default=20)
    crate_quantity = models.PositiveIntegerField(default=0)
    units_per_pack = models.PositiveIntegerField(default=6)
    pack_quantity = models.PositiveIntegerField(default=0)
    bottle_quantity = models.PositiveIntegerField(default=0)
    shots_per_bottle = models.PositiveIntegerField(default=1)
    shot_quantity = models.PositiveIntegerField(default=0)
    selling_unit = models.CharField(max_length=50, choices=SELLING_UNIT_CHOICES, default='Bottle')
    purchase_unit = models.CharField(max_length=20, choices=PURCHASE_UNIT_CHOICES, blank=True, help_text='Warehouse receiving unit (overrides auto-detection)')
    conversion_rate = models.PositiveIntegerField(null=True, blank=True, help_text='1 purchase_unit = conversion_rate selling_units (overrides auto-detection)')

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
        if self.unit_type == 'wine_glass':
            return f"{self.bottle_quantity} Glasses ({self.total_liters}L)"
        if self.unit_type == 'Crate' and self.crate_size > 0:
            return f"{self.crate_quantity} Crates ({self.quantity} Bottles)"
        if self.unit_type == 'Pack' and self.pack_size > 0:
            return f"{self.pack_quantity} Packs ({self.quantity} Bottles/Cans)"
        if self.unit_type == 'Bottle' and self.shots_per_bottle > 1:
            return f"{self.bottle_quantity} Bottles ({self.quantity} Shots)"
        return str(self.quantity)

    @property
    def total_glasses(self):
        if self.unit_type == 'wine_glass':
            return self.bottle_quantity
        return 0

    @property
    def total_liters(self):
        if self.unit_type == 'wine_glass' and self.glasses_per_liter:
            containers = self.bottle_quantity // self.glasses_per_liter
            return containers * self.liters_per_unit
        return 0

    @property
    def effective_pack_size(self):
        return self.pack_size or 6

    @property
    def effective_crate_size(self):
        return self.crate_size or 20

    def bottles_to_packs(self, bottles):
        return divmod(bottles, self.effective_pack_size)

    def bottles_to_crates(self, bottles):
        return divmod(bottles, self.effective_crate_size)

    @property
    def warehouse_unit_type(self):
        return get_purchase_unit(self)

    def convert_purchase_to_base(self, warehouse_qty):
        return engine_purchase_to_base(warehouse_qty, self)

    def convert_base_to_warehouse(self, base_qty):
        return engine_base_to_warehouse(base_qty, self)

    @property
    def selling_unit_label(self):
        return get_selling_unit_label(self)

    @property
    def warehouse_unit_label(self):
        return get_purchase_unit_label(self)


class StockSheet(models.Model):
    item = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, related_name='stock_sheets')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    open_stock = models.IntegerField(default=0)
    order_stock = models.IntegerField(default=0)
    total_stock = models.IntegerField(default=0)
    buying_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    selling_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    moved_stock = models.IntegerField(default=0)
    remaining_stock = models.IntegerField(default=0)
    sold_stock = models.PositiveIntegerField(default=0)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    date = models.DateField()
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    branch = models.ForeignKey('branches.Branch', on_delete=models.CASCADE, null=True, blank=True, related_name='stock_sheets')
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
        self.remaining_stock = self.total_stock - self.moved_stock
        self.total_amount = self.moved_stock * float(self.selling_price)
        super().save(*args, **kwargs)


class SalesSheet(models.Model):
    item = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, related_name='sales_sheets')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    open_stock = models.IntegerField(default=0)
    add_stock = models.IntegerField(default=0)
    total_stock = models.IntegerField(default=0)
    selling_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sold_stock = models.IntegerField(default=0)
    remaining_stock = models.IntegerField(default=0)
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    date = models.DateField()
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    branch = models.ForeignKey('branches.Branch', on_delete=models.CASCADE, null=True, blank=True, related_name='sales_sheets')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', 'item__display_order']
        verbose_name = 'Sales Sheet'
        verbose_name_plural = 'Sales Sheets'

    def __str__(self):
        return f"{self.item.name if self.item else 'N/A'} - {self.date} - {self.branch.branch_name if self.branch else 'N/A'}"

    def save(self, *args, **kwargs):
        self.total_stock = self.open_stock + self.add_stock
        self.remaining_stock = self.total_stock - self.sold_stock
        self.amount = self.sold_stock * float(self.selling_price)
        super().save(*args, **kwargs)
