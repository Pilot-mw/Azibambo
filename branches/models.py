from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class Branch(models.Model):
    BRANCH_TYPES = [
        ('Bar', 'Bar'),
        ('Bottle Store', 'Bottle Store'),
        ('Restaurant', 'Restaurant'),
        ('Club', 'Club'),
        ('Warehouse', 'Warehouse'),
    ]

    THEME_MODES = [
        ('dark', 'Dark'),
        ('light', 'Light'),
    ]

    branch_name = models.CharField(max_length=200, unique=True)
    branch_code = models.CharField(max_length=20, unique=True)
    branch_type = models.CharField(max_length=50, choices=BRANCH_TYPES, default='Bar')
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_branches')
    logo = models.ImageField(upload_to='branches/logos/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    theme_color = models.CharField(max_length=7, default='#2563eb', help_text='Primary brand color (hex)')
    secondary_color = models.CharField(max_length=7, default='#1d4ed8', help_text='Secondary brand color (hex)')
    logo_background_color = models.CharField(max_length=7, default='#1e293b', help_text='Background color for logo area')
    theme_mode = models.CharField(max_length=10, choices=THEME_MODES, default='dark', help_text='UI theme mode')
    sidebar_bg = models.CharField(max_length=7, default='#1e293b', help_text='Sidebar background color (hex)')
    sidebar_text = models.CharField(max_length=7, default='#cbd5e1', help_text='Sidebar text color (hex)')
    header_bg = models.CharField(max_length=7, default='#2563eb', help_text='Header/navbar background color (hex)')
    header_text = models.CharField(max_length=7, default='#ffffff', help_text='Header text color (hex)')
    selection_bg = models.CharField(max_length=7, default='#2563eb', help_text='Selection/highlight background (hex)')
    selection_text = models.CharField(max_length=7, default='#ffffff', help_text='Selection/highlight text color (hex)')
    button_color = models.CharField(max_length=7, default='#2563eb', help_text='Button primary color (hex)')
    card_accent = models.CharField(max_length=7, default='#2563eb', help_text='Card accent color (hex)')
    widget_bg = models.CharField(max_length=7, default='#16213e', help_text='Dashboard widget background (hex)')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['branch_name']
        verbose_name_plural = 'Branches'

    def __str__(self):
        return f"{self.branch_name} ({self.get_branch_type_display()})"


class StockTransfer(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
    ]

    from_branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='transfers_out')
    to_branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='transfers_in')
    product = models.ForeignKey('inventory.Product', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True)
    requested_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='transfer_requests')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='transfer_approvals')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Transfer {self.product.name}: {self.from_branch.branch_code} -> {self.to_branch.branch_code}"

    @property
    def warehouse_quantity(self):
        wh, _ = self.product.convert_base_to_warehouse(self.quantity)
        return wh
