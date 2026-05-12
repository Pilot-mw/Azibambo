from django import forms
from .models import Supplier, Purchase
from inventory.models import Product


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'phone', 'email', 'address', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Supplier Name'}),
            'phone': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Phone'}),
            'email': forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'Email'}),
            'address': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
            'notes': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
        }


class PurchaseForm(forms.ModelForm):
    class Meta:
        model = Purchase
        fields = ['supplier', 'product', 'warehouse_unit_type', 'quantity', 'unit_price', 'total_amount', 'paid_amount', 'notes', 'date']
        widgets = {
            'supplier': forms.Select(attrs={'class': 'form-input'}),
            'product': forms.Select(attrs={'class': 'form-input', 'id': 'id_product'}),
            'warehouse_unit_type': forms.Select(attrs={'class': 'form-input', 'id': 'id_warehouse_unit_type'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-input', 'id': 'id_quantity', 'min': '1'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-input', 'id': 'id_unit_price', 'step': '0.01'}),
            'total_amount': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
            'paid_amount': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
            'notes': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
            'date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
        }

    def clean(self):
        cleaned = super().clean()
        product = cleaned.get('product')
        warehouse_unit_type = cleaned.get('warehouse_unit_type')
        if product and warehouse_unit_type:
            expected = product.warehouse_unit_type
            if warehouse_unit_type != expected:
                raise forms.ValidationError(
                    f'Unit type for "{product.name}" must be "{expected}" (not "{warehouse_unit_type}")'
                )
        return cleaned
