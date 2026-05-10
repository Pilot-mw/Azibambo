from django.contrib import admin
from .models import Supplier, Purchase

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'email', 'outstanding_balance', 'is_active']
    search_fields = ['name', 'phone', 'email']

@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ['supplier', 'product', 'quantity', 'total_amount', 'date']
    list_filter = ['date', 'supplier']
