from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class Profile(models.Model):
    ROLE_CHOICES = [
        ('super_admin', 'Super Admin'),
        ('manager', 'Manager'),
        ('cashier', 'Cashier'),
        ('store_keeper', 'Store Keeper'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='cashier')
    phone = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    branch = models.ForeignKey('branches.Branch', on_delete=models.SET_NULL, null=True, blank=True, related_name='profiles')
    allowed_categories = models.ManyToManyField('inventory.Category', blank=True, related_name='allowed_profiles')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"

    @property
    def role_display(self):
        return dict(self.ROLE_CHOICES).get(self.role, self.role)

    @property
    def is_admin(self):
        return self.role == 'super_admin'

    @property
    def is_manager(self):
        return self.role == 'manager'

    @property
    def is_cashier(self):
        return self.role == 'cashier'

    @property
    def is_store_keeper(self):
        return self.role == 'store_keeper'

    def get_allowed_category_ids(self):
        if self.role in ('super_admin', 'manager', 'store_keeper'):
            return None
        return list(self.allowed_categories.values_list('id', flat=True))

    def get_allowed_categories(self):
        from inventory.models import Category
        if self.role in ('super_admin', 'manager', 'store_keeper'):
            return Category.objects.filter(name__in=['Beers & Softs', 'Ciders & Wines', 'Spirits & Others'])
        return self.allowed_categories.all()

    def filter_products(self, qs):
        cat_ids = self.get_allowed_category_ids()
        if cat_ids is not None:
            return qs.filter(category_id__in=cat_ids)
        return qs

    def filter_categories(self, qs):
        cat_ids = self.get_allowed_category_ids()
        if cat_ids is not None:
            return qs.filter(id__in=cat_ids)
        return qs

    PERMISSIONS_MATRIX = {
        'super_admin': ['*'],
        'manager': [
            'product_manage', 'reports_access', 'stock_sheet_manage',
            'expense_manage', 'supplier_manage', 'purchase_manage',
            'sales_access', 'dashboard_access',
        ],
        'cashier': [
            'sales_access', 'dashboard_access',
        ],
        'store_keeper': [
            'product_manage', 'stock_sheet_manage', 'supplier_manage',
            'purchase_manage', 'dashboard_access',
        ],
    }

    def has_permission(self, perm):
        if self.role == 'super_admin':
            return True
        return perm in self.PERMISSIONS_MATRIX.get(self.role, [])

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()

class ActivityLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=255)
    model_name = models.CharField(max_length=100, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    details = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    branch = models.ForeignKey('branches.Branch', on_delete=models.SET_NULL, null=True, blank=True, related_name='activity_logs')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} - {self.action} - {self.created_at}"
