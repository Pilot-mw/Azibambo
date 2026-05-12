from django import forms
from .models import Branch, StockTransfer


class BranchForm(forms.ModelForm):
    class Meta:
        model = Branch
        fields = ['branch_name', 'branch_code', 'branch_type', 'phone', 'email', 'address', 'manager', 'logo', 'is_active']
        widgets = {
            'branch_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Branch Name'}),
            'branch_code': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'BRC-001'}),
            'branch_type': forms.Select(attrs={'class': 'form-input'}),
            'phone': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '+265 XXX XXX XXX'}),
            'email': forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'branch@example.com'}),
            'address': forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': 'Physical Address'}),
            'manager': forms.Select(attrs={'class': 'form-input'}),
            'logo': forms.FileInput(attrs={'class': 'form-input'}),
        }


class StockTransferForm(forms.ModelForm):
    class Meta:
        model = StockTransfer
        fields = ['from_branch', 'to_branch', 'product', 'quantity', 'notes']
        widgets = {
            'from_branch': forms.Select(attrs={'class': 'form-input'}),
            'to_branch': forms.Select(attrs={'class': 'form-input'}),
            'product': forms.Select(attrs={'class': 'form-input'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-input', 'min': '1'}),
            'notes': forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': 'Optional notes...'}),
        }

    def clean(self):
        cleaned = super().clean()
        from_branch = cleaned.get('from_branch')
        to_branch = cleaned.get('to_branch')
        if from_branch and to_branch and from_branch == to_branch:
            raise forms.ValidationError("Source and destination branches cannot be the same.")
        return cleaned
