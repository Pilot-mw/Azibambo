from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Product, StockSheet, SalesSheet

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['display_order', 'name', 'category', 'unit_type', 'crate_quantity', 'pack_quantity', 'bottle_quantity', 'shot_quantity', 'quantity', 'buying_price', 'selling_price', 'reorder_level', 'is_low_stock', 'is_active', 'admin_actions']
    list_filter = ['category', 'is_active', 'unit_type', 'supplier']
    search_fields = ['name', 'barcode']
    list_editable = ['display_order', 'crate_quantity', 'pack_quantity', 'bottle_quantity', 'selling_price', 'buying_price']
    readonly_fields = ['quantity']
    list_display_links = ['name']

    def admin_actions(self, obj):
        up_url = f'/admin/inventory/product/{obj.id}/move-up/'
        down_url = f'/admin/inventory/product/{obj.id}/move-down/'
        return format_html(
            '<a class="button" href="{}">▲ Up</a> '
            '<a class="button" href="{}">▼ Down</a>',
            up_url, down_url
        )
    admin_actions.short_description = 'Reorder'

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('<int:pk>/move-up/', self.admin_site.admin_view(self.move_up), name='product-move-up'),
            path('<int:pk>/move-down/', self.admin_site.admin_view(self.move_down), name='product-move-down'),
        ]
        return custom_urls + urls

    def move_up(self, request, pk):
        from django.shortcuts import redirect
        from django.contrib import messages
        product = Product.objects.get(pk=pk)
        prev = Product.objects.filter(
            category=product.category, display_order__lt=product.display_order
        ).order_by('-display_order').first()
        if prev:
            prev.display_order, product.display_order = product.display_order, prev.display_order
            prev.save(update_fields=['display_order'])
            product.save(update_fields=['display_order'])
            messages.success(request, f'{product.name} moved up')
        else:
            messages.info(request, f'{product.name} is already at the top')
        return redirect('/admin/inventory/product/')

    def move_down(self, request, pk):
        from django.shortcuts import redirect
        from django.contrib import messages
        product = Product.objects.get(pk=pk)
        nxt = Product.objects.filter(
            category=product.category, display_order__gt=product.display_order
        ).order_by('display_order').first()
        if nxt:
            nxt.display_order, product.display_order = product.display_order, nxt.display_order
            nxt.save(update_fields=['display_order'])
            product.save(update_fields=['display_order'])
            messages.success(request, f'{product.name} moved down')
        else:
            messages.info(request, f'{product.name} is already at the bottom')
        return redirect('/admin/inventory/product/')
    fieldsets = (
        (None, {
            'fields': ('category', 'name', 'barcode', 'description', 'image')
        }),
        ('Pricing', {
            'fields': ('buying_price', 'selling_price')
        }),
        ('Unit Management', {
            'fields': ('unit_type', 'units_per_crate', 'crate_quantity', 'units_per_pack', 'pack_quantity', 'shots_per_bottle', 'bottle_quantity', 'shot_quantity', 'quantity', 'selling_unit', 'reorder_level'),
            'description': 'Quantity is auto-calculated from crates, packs, bottles, and shots.'
        }),
        ('Additional', {
            'fields': ('expiry_date', 'supplier', 'is_active')
        }),
    )


@admin.register(StockSheet)
class StockSheetAdmin(admin.ModelAdmin):
    list_display = ['item', 'date', 'open_stock', 'order_stock', 'total_stock', 'buying_price', 'selling_price', 'moved_stock', 'remaining_stock']
    list_filter = ['date', 'category']
    search_fields = ['item__name']
    readonly_fields = ['total_stock', 'remaining_stock']
    date_hierarchy = 'date'


@admin.register(SalesSheet)
class SalesSheetAdmin(admin.ModelAdmin):
    list_display = ['item', 'branch', 'date', 'open_stock', 'add_stock', 'total_stock', 'sold_stock', 'remaining_stock', 'amount']
    list_filter = ['date', 'branch', 'category']
    search_fields = ['item__name']
    readonly_fields = ['total_stock', 'remaining_stock', 'amount']
    date_hierarchy = 'date'
