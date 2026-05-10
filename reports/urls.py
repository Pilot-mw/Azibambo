from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.reports_index, name='reports_index'),
    path('daily/', views.daily_report, name='daily_report'),
    path('weekly/', views.weekly_report, name='weekly_report'),
    path('monthly/', views.monthly_report, name='monthly_report'),
    path('profit/', views.profit_report, name='profit_report'),
    path('stock/', views.stock_report, name='stock_report'),
    path('movement/', views.product_movement, name='product_movement'),
    path('cashier/', views.cashier_report, name='cashier_report'),
    path('low-stock/', views.low_stock_report, name='low_stock_report'),
]
