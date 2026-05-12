from django import forms
from .models import Product, Category, StockSheet, SalesSheet


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Category Name'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': 'Description'}),
        }


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['category', 'name', 'barcode', 'description', 'image', 'buying_price',
                  'selling_price', 'unit_type', 'units_per_crate', 'crate_quantity',
                  'units_per_pack', 'pack_quantity',
                  'bottle_quantity', 'shots_per_bottle', 'shot_quantity',
                  'reorder_level', 'selling_unit', 'expiry_date', 'supplier']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Product Name'}),
            'barcode': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Barcode'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
            'buying_price': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
            'selling_price': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
            'unit_type': forms.Select(attrs={'class': 'form-input'}),
            'units_per_crate': forms.NumberInput(attrs={'class': 'form-input'}),
            'crate_quantity': forms.NumberInput(attrs={'class': 'form-input'}),
            'units_per_pack': forms.NumberInput(attrs={'class': 'form-input'}),
            'pack_quantity': forms.NumberInput(attrs={'class': 'form-input'}),
            'bottle_quantity': forms.NumberInput(attrs={'class': 'form-input'}),
            'shots_per_bottle': forms.NumberInput(attrs={'class': 'form-input'}),
            'shot_quantity': forms.NumberInput(attrs={'class': 'form-input'}),
            'reorder_level': forms.NumberInput(attrs={'class': 'form-input'}),
            'selling_unit': forms.Select(attrs={'class': 'form-input'}),
            'expiry_date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'category': forms.Select(attrs={'class': 'form-input'}),
            'supplier': forms.Select(attrs={'class': 'form-input'}),
            'image': forms.FileInput(attrs={'class': 'form-input'}),
        }


class SalesSheetForm(forms.ModelForm):
    class Meta:
        model = SalesSheet
        fields = ['item', 'category', 'open_stock', 'add_stock', 'selling_price', 'sold_stock', 'date']
        widgets = {
            'item': forms.Select(attrs={'class': 'form-input'}),
            'category': forms.Select(attrs={'class': 'form-input'}),
            'open_stock': forms.NumberInput(attrs={'class': 'form-input', 'data-field': 'open'}),
            'add_stock': forms.NumberInput(attrs={'class': 'form-input', 'data-field': 'add'}),
            'selling_price': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'data-field': 'selling_price'}),
            'sold_stock': forms.NumberInput(attrs={'class': 'form-input', 'data-field': 'sold'}),
            'date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
        }


class StockSheetForm(forms.ModelForm):
    class Meta:
        model = StockSheet
        fields = ['item', 'category', 'open_stock', 'order_stock', 'buying_price', 'selling_price', 'moved_stock', 'date']
        widgets = {
            'item': forms.Select(attrs={'class': 'form-input'}),
            'category': forms.Select(attrs={'class': 'form-input'}),
            'open_stock': forms.NumberInput(attrs={'class': 'form-input', 'data-field': 'open'}),
            'order_stock': forms.NumberInput(attrs={'class': 'form-input', 'data-field': 'order'}),
            'buying_price': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'data-field': 'buying_price'}),
            'selling_price': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'data-field': 'selling_price'}),
            'moved_stock': forms.NumberInput(attrs={'class': 'form-input', 'data-field': 'moved'}),
            'date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
        }
