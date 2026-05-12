from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from .forms import LoginForm, UserRegistrationForm, ProfileUpdateForm, UserEditForm
from .models import ActivityLog, Profile
from .decorators import role_required
from inventory.models import Product
from sales.models import Sale
from expenses.models import Expense
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from django.db.models.functions import TruncDate

def landing(request):
    if request.user.is_authenticated:
        return redirect('dashboard:welcome')
    return render(request, 'landing/index.html')

def user_login(request):
    if request.user.is_authenticated:
        return redirect('dashboard:welcome')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                ActivityLog.objects.create(
                    user=user,
                    action='User Login',
                    branch=getattr(request, 'current_branch', None),
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                messages.success(request, f'Welcome back, {user.username}!')
                return redirect('dashboard:welcome')
        messages.error(request, 'Invalid username or password.')
    else:
        form = LoginForm()
    return render(request, 'accounts/login.html', {'form': form})

def user_logout(request):
    if request.user.is_authenticated:
        ActivityLog.objects.create(
            user=request.user,
            action='User Logout',
            branch=getattr(request, 'current_branch', None),
            ip_address=request.META.get('REMOTE_ADDR')
        )
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('accounts:login')

@login_required
def register(request):
    if request.user.profile.role != 'super_admin':
        messages.error(request, 'You do not have permission to register users.')
        return redirect('dashboard:welcome')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            ActivityLog.objects.create(
                user=request.user,
                action=f'Created user {user.username}',
                model_name='User',
                object_id=user.id,
                branch=getattr(request, 'current_branch', None),
                ip_address=request.META.get('REMOTE_ADDR')
            )
            messages.success(request, f'User {user.username} created successfully!')
            return redirect('accounts:register')
    else:
        form = UserRegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})

@login_required
def profile_view(request):
    return render(request, 'accounts/profile.html')

@login_required
def profile_edit(request):
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('accounts:profile')
    else:
        form = ProfileUpdateForm(instance=request.user.profile)
    return render(request, 'accounts/profile_edit.html', {'form': form})

@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            ActivityLog.objects.create(
                user=request.user,
                action='Password changed',
                branch=getattr(request, 'current_branch', None),
                ip_address=request.META.get('REMOTE_ADDR')
            )
            messages.success(request, 'Password changed successfully!')
            return redirect('accounts:profile')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'accounts/change_password.html', {'form': form})


@login_required
@role_required('super_admin')
def user_list(request):
    users = User.objects.select_related('profile').all().order_by('username')
    query = request.GET.get('q', '')
    role_filter = request.GET.get('role', '')
    status_filter = request.GET.get('status', '')
    if query:
        users = users.filter(Q(username__icontains=query) | Q(email__icontains=query) | Q(first_name__icontains=query) | Q(last_name__icontains=query))
    if role_filter:
        users = users.filter(profile__role=role_filter)
    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)
    return render(request, 'accounts/user_list.html', {
        'users': users, 'query': query,
        'role_filter': role_filter, 'status_filter': status_filter,
        'role_choices': Profile.ROLE_CHOICES,
    })


@login_required
@role_required('super_admin')
def user_create(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            ActivityLog.objects.create(
                user=request.user, action=f'Created user {user.username}',
                model_name='User', object_id=user.id,
                branch=getattr(request, 'current_branch', None),
                ip_address=request.META.get('REMOTE_ADDR')
            )
            messages.success(request, f'User {user.username} created!')
            return redirect('accounts:user_list')
    else:
        form = UserRegistrationForm()
    return render(request, 'accounts/user_form.html', {'form': form, 'title': 'Create User'})


@login_required
@role_required('super_admin')
def user_edit(request, pk):
    user = get_object_or_404(User.objects.select_related('profile'), pk=pk)
    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            ActivityLog.objects.create(
                user=request.user, action=f'Edited user {user.username}',
                model_name='User', object_id=user.id,
                branch=getattr(request, 'current_branch', None),
                ip_address=request.META.get('REMOTE_ADDR')
            )
            messages.success(request, f'User {user.username} updated!')
            return redirect('accounts:user_list')
    else:
        form = UserEditForm(instance=user)
    return render(request, 'accounts/user_form.html', {'form': form, 'title': 'Edit User', 'edit_user': user})


@login_required
@role_required('super_admin')
def user_toggle_active(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        messages.error(request, 'You cannot deactivate yourself.')
        return redirect('accounts:user_list')
    user.is_active = not user.is_active
    user.save()
    status = 'activated' if user.is_active else 'deactivated'
    ActivityLog.objects.create(
        user=request.user, action=f'{status} user {user.username}',
        model_name='User', object_id=user.id,
        branch=getattr(request, 'current_branch', None),
        ip_address=request.META.get('REMOTE_ADDR')
    )
    messages.success(request, f'User {user.username} {status}.')
    return redirect('accounts:user_list')


@login_required
@role_required('super_admin')
def user_reset_password(request, pk):
    import secrets
    import string
    user = get_object_or_404(User, pk=pk)
    from django.contrib.auth.hashers import make_password
    new_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10))
    user.password = make_password(new_password)
    user.save()
    ActivityLog.objects.create(
        user=request.user, action=f'Reset password for user {user.username}',
        model_name='User', object_id=user.id,
        branch=getattr(request, 'current_branch', None),
        ip_address=request.META.get('REMOTE_ADDR')
    )
    messages.success(request, f'Password reset for {user.username}. New password: {new_password}')
    return redirect('accounts:user_list')


@login_required
@role_required('super_admin')
def user_change_role(request, pk):
    user = get_object_or_404(User.objects.select_related('profile'), pk=pk)
    if request.method == 'POST':
        new_role = request.POST.get('role')
        if new_role in dict(Profile.ROLE_CHOICES):
            user.profile.role = new_role
            user.profile.save()
            ActivityLog.objects.create(
                user=request.user, action=f'Changed role of {user.username} to {new_role}',
                model_name='User', object_id=user.id,
                branch=getattr(request, 'current_branch', None),
                ip_address=request.META.get('REMOTE_ADDR')
            )
            messages.success(request, f'{user.username} role changed to {new_role}.')
        return redirect('accounts:user_list')
    return render(request, 'accounts/user_change_role.html', {'role_user': user, 'role_choices': Profile.ROLE_CHOICES})


@login_required
@role_required('super_admin')
def user_delete(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        messages.error(request, 'You cannot delete yourself.')
        return redirect('accounts:user_list')
    if request.method == 'POST':
        name = user.username
        user.delete()
        ActivityLog.objects.create(
            user=request.user, action=f'Deleted user {name}',
            model_name='User', object_id=pk,
            branch=getattr(request, 'current_branch', None),
            ip_address=request.META.get('REMOTE_ADDR')
        )
        messages.success(request, f'User {name} deleted.')
        return redirect('accounts:user_list')
    return render(request, 'accounts/user_confirm_delete.html', {'del_user': user})
