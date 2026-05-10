from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from .models import SiteSettings, Backup
from .forms import SiteSettingsForm
from accounts.models import ActivityLog
from django.db import connection
import datetime
import os

@login_required
def settings_view(request):
    settings = SiteSettings.objects.first()
    if request.method == 'POST':
        form = SiteSettingsForm(request.POST, request.FILES, instance=settings)
        if form.is_valid():
            form.save()
            ActivityLog.objects.create(
                user=request.user, action='Updated site settings',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            messages.success(request, 'Settings updated successfully!')
            return redirect('settings_app:settings')
    else:
        form = SiteSettingsForm(instance=settings)
    return render(request, 'settings_app/settings.html', {'form': form, 'settings': settings})

@login_required
def backup_database(request):
    import subprocess
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
    return redirect('settings_app:settings')

@login_required
def activity_logs(request):
    logs = ActivityLog.objects.select_related('user')[:100]
    return render(request, 'settings_app/activity_logs.html', {'logs': logs})
