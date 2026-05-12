from django.contrib import admin
from .models import Branch, StockTransfer


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ['branch_name', 'branch_code', 'branch_type', 'phone', 'email', 'manager', 'is_active']
    list_filter = ['branch_type', 'is_active']
    search_fields = ['branch_name', 'branch_code', 'phone', 'email']


@admin.register(StockTransfer)
class StockTransferAdmin(admin.ModelAdmin):
    list_display = ['product', 'from_branch', 'to_branch', 'quantity', 'status', 'requested_by', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['product__name', 'from_branch__branch_name', 'to_branch__branch_name']
