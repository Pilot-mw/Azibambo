from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import Profile
from branches.models import Branch
from inventory.models import Category


class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Username'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Password'}))


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'Email'}))
    first_name = forms.CharField(max_length=30, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'First Name'}))
    last_name = forms.CharField(max_length=30, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Last Name'}))
    role = forms.ChoiceField(choices=Profile.ROLE_CHOICES, widget=forms.Select(attrs={'class': 'form-input'}))
    branch = forms.ModelChoiceField(
        queryset=Branch.objects.filter(is_active=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-input'})
    )
    allowed_categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.filter(name__in=['Beers & Softs', 'Ciders & Wines', 'Spirits & Others']),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-input', 'size': 5}),
        label='Allowed Categories (for Cashiers)'
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'form-input', 'placeholder': 'Username'})
        self.fields['password1'].widget.attrs.update({'class': 'form-input', 'placeholder': 'Password'})
        self.fields['password2'].widget.attrs.update({'class': 'form-input', 'placeholder': 'Confirm Password'})
        self.fields['branch'].empty_label = "No Branch (Super Admin)"

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
            profile = Profile.objects.get(user=user)
            profile.role = self.cleaned_data['role']
            profile.branch = self.cleaned_data.get('branch')
            profile.save()
            profile.allowed_categories.set(self.cleaned_data.get('allowed_categories', []))
        return user


class ProfileUpdateForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)
    email = forms.EmailField()

    class Meta:
        model = Profile
        fields = ['phone', 'avatar', 'role']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email

    def save(self, commit=True):
        profile = super().save(commit=False)
        profile.user.first_name = self.cleaned_data['first_name']
        profile.user.last_name = self.cleaned_data['last_name']
        profile.user.email = self.cleaned_data['email']
        if commit:
            profile.user.save()
            profile.save()
        return profile


class UserEditForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, widget=forms.TextInput(attrs={'class': 'form-input'}))
    last_name = forms.CharField(max_length=30, widget=forms.TextInput(attrs={'class': 'form-input'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-input'}))
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-input'}))

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            profile = Profile.objects.get(user=self.instance)
            self.fields['role'] = forms.ChoiceField(
                choices=Profile.ROLE_CHOICES,
                initial=profile.role,
                widget=forms.Select(attrs={'class': 'form-input'})
            )
            self.fields['branch'] = forms.ModelChoiceField(
                queryset=Branch.objects.filter(is_active=True),
                initial=profile.branch,
                required=False,
                widget=forms.Select(attrs={'class': 'form-input'})
            )
            self.fields['branch'].empty_label = "No Branch (Super Admin)"
            self.fields['allowed_categories'] = forms.ModelMultipleChoiceField(
                queryset=Category.objects.filter(name__in=['Beers & Softs', 'Ciders & Wines', 'Spirits & Others']),
                initial=profile.allowed_categories.all(),
                required=False,
                widget=forms.SelectMultiple(attrs={'class': 'form-input', 'size': 5}),
                label='Allowed Categories (for Cashiers)'
            )

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            profile = Profile.objects.get(user=user)
            if 'role' in self.cleaned_data:
                profile.role = self.cleaned_data['role']
            if 'branch' in self.cleaned_data:
                profile.branch = self.cleaned_data['branch']
            profile.save()
            if 'allowed_categories' in self.cleaned_data:
                profile.allowed_categories.set(self.cleaned_data['allowed_categories'])
        return user
