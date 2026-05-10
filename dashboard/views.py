import django.db.models as models
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q, F
from django.utils import timezone
from datetime import timedelta, datetime
from inventory.models import Product, Category, StockSheet
from sales.models import Sale, SaleItem
from expenses.models import Expense
from django.db.models.functions import TruncDate

@login_required
def index(request):
    today = timezone.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    start_of_month = today.replace(day=1)

    daily_sales = Sale.objects.filter(created_at__date=today, status='completed').aggregate(
        total=Sum('total'), count=Count('id')
    )
    weekly_sales = Sale.objects.filter(created_at__date__gte=start_of_week, status='completed').aggregate(
        total=Sum('total'), count=Count('id')
    )
    monthly_sales = Sale.objects.filter(created_at__date__gte=start_of_month, status='completed').aggregate(
        total=Sum('total'), count=Count('id')
    )

    today_expenses = Expense.objects.filter(date=today).aggregate(total=Sum('amount'))
    monthly_expenses = Expense.objects.filter(date__gte=start_of_month).aggregate(total=Sum('amount'))

    total_products = Product.objects.filter(is_active=True).count()
    low_stock_products = Product.objects.filter(quantity__lte=models.F('reorder_level'), is_active=True)
    low_stock_count = low_stock_products.count()

    stock_value = Product.objects.filter(is_active=True).aggregate(
        total=Sum(models.F('quantity') * models.F('buying_price'))
    )

    top_selling = SaleItem.objects.values('product_name').annotate(
        total_qty=Sum('quantity'), total_revenue=Sum('subtotal')
    ).order_by('-total_qty')[:10]

    recent_sales = Sale.objects.filter(status='completed').select_related('cashier')[:10]

    today_stock_sheet = StockSheet.objects.filter(date=today).aggregate(
        total_sold=Sum('sold_stock'),
        total_revenue=Sum('total_amount'),
        total_remaining=Sum('remaining_stock'),
    )
    best_stock_items = StockSheet.objects.filter(date=today).values('item__name').annotate(
        total_sold=Sum('sold_stock'),
        total_revenue=Sum('total_amount'),
    ).order_by('-total_sold')[:5]

    sales_data = Sale.objects.filter(
        created_at__date__gte=today - timedelta(days=30),
        status='completed'
    ).annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(
        total=Sum('total')
    ).order_by('date')

    context = {
        'daily_sales': daily_sales['total'] or 0,
        'daily_sales_count': daily_sales['count'] or 0,
        'weekly_sales': weekly_sales['total'] or 0,
        'monthly_sales': monthly_sales['total'] or 0,
        'monthly_sales_count': monthly_sales['count'] or 0,
        'today_expenses': today_expenses['total'] or 0,
        'monthly_expenses': monthly_expenses['total'] or 0,
        'total_products': total_products,
        'low_stock_count': low_stock_count,
        'low_stock_products': low_stock_products[:10],
        'stock_value': stock_value['total'] or 0,
        'top_selling': top_selling,
        'recent_sales': recent_sales,
        'sales_data': list(sales_data),
        'ss_total_sold': today_stock_sheet['total_sold'] or 0,
        'ss_total_revenue': today_stock_sheet['total_revenue'] or 0,
        'ss_total_remaining': today_stock_sheet['total_remaining'] or 0,
        'ss_best_items': best_stock_items,
    }
    return render(request, 'dashboard/index.html', context)
