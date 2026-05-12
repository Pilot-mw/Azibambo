from django.urls import path
from . import views

app_name = 'settings_app'

urlpatterns = [
    path('', views.settings_view, name='settings'),
    path('general/', views.settings_view, name='general'),
    path('users/', views.settings_users, name='users'),
    path('users/create/', views.settings_user_create, name='user_create'),
    path('users/<int:pk>/edit/', views.settings_user_edit, name='user_edit'),
    path('users/<int:pk>/toggle-active/', views.settings_user_toggle_active, name='user_toggle_active'),
    path('users/<int:pk>/reset-password/', views.settings_user_reset_password, name='user_reset_password'),
    path('users/<int:pk>/change-role/', views.settings_user_change_role, name='user_change_role'),
    path('users/<int:pk>/delete/', views.settings_user_delete, name='user_delete'),
    path('backup/', views.settings_backup, name='backup'),
    path('backup/run/', views.backup_database, name='backup_run'),
    path('logs/', views.activity_logs, name='activity_logs'),
    path('theme/', views.settings_theme, name='theme'),
]
