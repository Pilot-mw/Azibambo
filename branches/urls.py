from django.urls import path
from . import views

app_name = 'branches'

urlpatterns = [
    path('', views.branch_list, name='branch_list'),
    path('add/', views.branch_add, name='branch_add'),
    path('<int:pk>/edit/', views.branch_edit, name='branch_edit'),
    path('<int:pk>/toggle/', views.branch_toggle, name='branch_toggle'),
    path('<int:pk>/dashboard/', views.branch_dashboard, name='branch_dashboard'),
    path('switch/', views.switch_branch, name='switch_branch'),
    path('transfers/', views.transfer_list, name='transfer_list'),
    path('transfers/add/', views.transfer_add, name='transfer_add'),
    path('transfers/<int:pk>/approve/', views.transfer_approve, name='transfer_approve'),
    path('transfers/<int:pk>/reject/', views.transfer_reject, name='transfer_reject'),
    path('transfers/<int:pk>/complete/', views.transfer_complete, name='transfer_complete'),
]
