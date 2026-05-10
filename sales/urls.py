from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [
    path('pos/', views.pos_index, name='pos'),
    path('api/products/search/', views.search_products, name='search_products'),
    path('api/create-sale/', views.create_sale, name='create_sale'),
    path('<int:pk>/', views.sale_detail, name='sale_detail'),
    path('<int:pk>/receipt/', views.sale_receipt, name='sale_receipt'),
    path('<int:pk>/refund/', views.refund_sale, name='refund_sale'),
    path('history/', views.sale_history, name='sale_history'),
]
