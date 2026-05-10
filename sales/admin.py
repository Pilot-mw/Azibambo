from django.contrib import admin
from .models import Sale, SaleItem

class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    readonly_fields = ['product_name', 'quantity', 'price', 'subtotal', 'selling_unit']

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ['receipt_number', 'cashier', 'total', 'payment_method', 'status', 'created_at']
    list_filter = ['payment_method', 'status', 'created_at']
    search_fields = ['receipt_number', 'cashier__username']
    inlines = [SaleItemInline]
    readonly_fields = ['receipt_number', 'subtotal', 'total', 'change_due']
