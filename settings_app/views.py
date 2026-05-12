from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.contrib.auth.models import User
from django.db.models import Q
from .models import SiteSettings, Backup
from .forms import SiteSettingsForm
from branches.models import Branch
from accounts.decorators import role_required
from accounts.models import ActivityLog, Profile
from django.db import connection
import datetime
import os


def _settings_render(request, template, extra_context=None):
    """Render within the settings layout."""
    settings_obj = SiteSettings.objects.first()
    context = {
        'form': SiteSettingsForm(instance=settings_obj),
        'settings': settings_obj,
        'settings_tab': template,
    }
    if extra_context:
        context.update(extra_context)
    return render(request, 'settings_app/settings.html', context)


@login_required
@role_required('super_admin')
def settings_view(request):
    settings_obj = SiteSettings.objects.first()
    if request.method == 'POST':
        form = SiteSettingsForm(request.POST, request.FILES, instance=settings_obj)
        if form.is_valid():
            form.save()
            ActivityLog.objects.create(
                user=request.user, action='Updated site settings',
                branch=getattr(request, 'current_branch', None),
                ip_address=request.META.get('REMOTE_ADDR')
            )
            messages.success(request, 'Settings updated successfully!')
            return redirect('settings_app:general')
    else:
        form = SiteSettingsForm(instance=settings_obj)
    return render(request, 'settings_app/settings.html', {
        'form': form, 'settings': settings_obj, 'settings_tab': 'general',
    })


@login_required
@role_required('super_admin')
def settings_backup(request):
    backups = Backup.objects.all().order_by('-created_at')[:10]
    return render(request, 'settings_app/settings.html', {
        'backups': backups, 'settings_tab': 'backup',
        'settings': SiteSettings.objects.first(),
    })


@login_required
@role_required('super_admin')
def settings_theme(request):
    if request.method == 'POST':
        branch_id = request.POST.get('branch_id')
        branch = get_object_or_404(Branch, pk=branch_id)
        theme_fields = [
            'theme_color', 'secondary_color', 'logo_background_color',
            'theme_mode', 'sidebar_bg', 'sidebar_text',
            'header_bg', 'header_text', 'selection_bg', 'selection_text',
            'button_color', 'card_accent', 'widget_bg',
        ]
        for field in theme_fields:
            val = request.POST.get(field)
            if val is not None:
                setattr(branch, field, val)
        branch.save()
        ActivityLog.objects.create(
            user=request.user, action=f'Updated theme for branch {branch.branch_name}',
            branch=getattr(request, 'current_branch', None),
            ip_address=request.META.get('REMOTE_ADDR')
        )
        messages.success(request, f'Theme for "{branch.branch_name}" updated!')
        return redirect('settings_app:theme')

    branches = Branch.objects.filter(is_active=True)
    return render(request, 'settings_app/settings.html', {
        'branches': branches, 'settings_tab': 'theme',
        'settings': SiteSettings.objects.first(),
    })


@login_required
@role_required('super_admin')
def backup_database(request):
    try:
        filename = f"backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.sqlite3"
        backup_path = os.path.join('backups', filename)
        os.makedirs('backups', exist_ok=True)
        import shutil
        shutil.copy2('db.sqlite3', backup_path)
        Backup.objects.create(file=backup_path, notes='Manual backup')
        messages.success(request, f'Database backed up as {filename}')
    except Exception as e:
        messages.error(request, f'Backup failed: {str(e)}')
    return redirect('settings_app:general')


@login_required
@role_required('super_admin')
def activity_logs(request):
    logs = ActivityLog.objects.select_related('user')[:100]
    return render(request, 'settings_app/settings.html', {
        'logs': logs, 'settings_tab': 'activity_logs',
        'settings': SiteSettings.objects.first(),
    })


@login_required
@role_required('super_admin')
def settings_users(request):
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
    return render(request, 'settings_app/settings.html', {
        'users': users, 'query': query,
        'role_filter': role_filter, 'status_filter': status_filter,
        'role_choices': Profile.ROLE_CHOICES,
        'settings_tab': 'users',
        'settings': SiteSettings.objects.first(),
    })


@login_required
@role_required('super_admin')
def settings_user_create(request):
    from accounts.forms import UserRegistrationForm
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
            return redirect('settings_app:users')
    else:
        form = UserRegistrationForm()
    return render(request, 'settings_app/settings.html', {
        'form': form, 'title': 'Create User', 'settings_tab': 'user_form',
        'settings': SiteSettings.objects.first(),
    })


@login_required
@role_required('super_admin')
def settings_user_edit(request, pk):
    from accounts.forms import UserEditForm
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
            return redirect('settings_app:users')
    else:
        form = UserEditForm(instance=user)
    return render(request, 'settings_app/settings.html', {
        'form': form, 'title': 'Edit User', 'edit_user': user,
        'settings_tab': 'user_form', 'settings': SiteSettings.objects.first(),
    })


@login_required
@role_required('super_admin')
def settings_user_toggle_active(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        messages.error(request, 'You cannot deactivate yourself.')
        return redirect('settings_app:users')
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
    return redirect('settings_app:users')


@login_required
@role_required('super_admin')
def settings_user_reset_password(request, pk):
    from django.contrib.auth.hashers import make_password
    import secrets
    import string
    user = get_object_or_404(User, pk=pk)
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
    return redirect('settings_app:users')


@login_required
@role_required('super_admin')
def settings_user_change_role(request, pk):
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
        return redirect('settings_app:users')
    return render(request, 'settings_app/settings.html', {
        'role_user': user, 'role_choices': Profile.ROLE_CHOICES,
        'settings_tab': 'user_change_role', 'settings': SiteSettings.objects.first(),
    })


@login_required
@role_required('super_admin')
def settings_user_delete(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        messages.error(request, 'You cannot delete yourself.')
        return redirect('settings_app:users')
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
        return redirect('settings_app:users')
    return render(request, 'settings_app/settings.html', {
        'del_user': user, 'settings_tab': 'user_delete',
        'settings': SiteSettings.objects.first(),
    })
