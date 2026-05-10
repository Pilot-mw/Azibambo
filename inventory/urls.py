from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    path('products/', views.product_list, name='product_list'),
    path('products/add/', views.product_add, name='product_add'),
    path('products/<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('products/<int:pk>/delete/', views.product_delete, name='product_delete'),
    path('categories/', views.category_list, name='category_list'),
    path('categories/add/', views.category_add, name='category_add'),
    path('categories/<int:pk>/edit/', views.category_edit, name='category_edit'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),
    path('stock-sheet/', views.stock_sheet, name='stock_sheet'),
    path('stock-sheet/save/', views.stock_sheet_save, name='stock_sheet_save'),
    path('stock-sheet/delete/', views.stock_sheet_delete, name='stock_sheet_delete'),
    path('stock-sheet/data/', views.stock_sheet_data, name='stock_sheet_data'),
    path('api/products-by-category/', views.api_products_by_category, name='api_products_by_category'),
]
