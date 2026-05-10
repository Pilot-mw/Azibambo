from django import forms
from .models import SiteSettings

class SiteSettingsForm(forms.ModelForm):
    class Meta:
        model = SiteSettings
        fields = ['business_name', 'business_tagline', 'business_logo', 'business_phone',
                  'business_email', 'business_address', 'currency', 'tax_rate',
                  'receipt_footer', 'theme', 'sidebar_color', 'enable_notifications',
                  'low_stock_alert']
        widgets = {
            'business_name': forms.TextInput(attrs={'class': 'form-input'}),
            'business_tagline': forms.TextInput(attrs={'class': 'form-input'}),
            'business_phone': forms.TextInput(attrs={'class': 'form-input'}),
            'business_email': forms.EmailInput(attrs={'class': 'form-input'}),
            'business_address': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
            'currency': forms.TextInput(attrs={'class': 'form-input'}),
            'tax_rate': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
            'receipt_footer': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
            'theme': forms.Select(attrs={'class': 'form-input'}),
            'sidebar_color': forms.Select(attrs={'class': 'form-input'}),
            'business_logo': forms.FileInput(attrs={'class': 'form-input'}),
            'enable_notifications': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'low_stock_alert': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }
