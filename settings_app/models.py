from django.db import models

class SiteSettings(models.Model):
    THEME_CHOICES = [
        ('dark', 'Dark'),
        ('light', 'Light'),
    ]

    SIDEBAR_COLORS = [
        ('dark', 'Dark'),
        ('gradient', 'Gradient'),
        ('light', 'Light'),
    ]

    business_name = models.CharField(max_length=200, default='Azibambo Stop_Over')
    business_tagline = models.TextField(default='Smart Stock. Smooth Service.', blank=True)
    business_logo = models.ImageField(upload_to='logos/', blank=True, null=True)
    business_phone = models.CharField(max_length=20, default='+265 000 000 000', blank=True)
    business_email = models.EmailField(default='info@azibambo.com', blank=True)
    business_address = models.TextField(default='Malawi', blank=True)
    currency = models.CharField(max_length=10, default='MWK')
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    receipt_footer = models.TextField(default='Thank you for your patronage!', blank=True)
    theme = models.CharField(max_length=10, choices=THEME_CHOICES, default='dark')
    sidebar_color = models.CharField(max_length=10, choices=SIDEBAR_COLORS, default='dark')
    enable_notifications = models.BooleanField(default=True)
    low_stock_alert = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Site Settings"

    def __str__(self):
        return self.business_name

    def save(self, *args, **kwargs):
        if not self.pk and SiteSettings.objects.exists():
            return
        super().save(*args, **kwargs)

class Backup(models.Model):
    file = models.FileField(upload_to='backups/')
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Backup {self.created_at}"
