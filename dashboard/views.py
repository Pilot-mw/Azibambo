import django.db.models as models
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Sum, Count, Q, F
from django.utils import timezone
from datetime import timedelta, datetime
from inventory.models import Product, Category, StockSheet
from sales.models import Sale, SaleItem
from expenses.models import Expense
from branches.models import Branch
from django.db.models.functions import TruncDate


def _get_branch_filter(request):
    branch = getattr(request, 'current_branch', None)
    if branch:
        return {'branch': branch}, branch
    return {}, None


@login_required
def welcome(request):
    from accounts.models import Profile, ActivityLog
    from sales.models import Sale
    from datetime import datetime

    profile = request.user.profile
    current_branch = getattr(request, 'current_branch', None)
    today = timezone.now().date()

    daily_sales = Sale.objects.filter(created_at__date=today, status='completed').aggregate(
        total=Sum('total'), count=Count('id')
    )
    cashiers = User.objects.filter(
        profile__role='cashier', is_active=True
    ).select_related('profile__branch').order_by('username')

    cashier_data = []
    for c in cashiers:
        branch_name = c.profile.branch.branch_name if c.profile.branch else 'Unassigned'
        last_seen = ActivityLog.objects.filter(
            user=c, action='User Login'
        ).order_by('-created_at').first()
        cashier_data.append({
            'user': c,
            'branch_name': branch_name,
            'last_seen': last_seen.created_at if last_seen else None,
            'is_online': bool(last_seen),
        })

    context = {
        'profile': profile,
        'current_branch': current_branch,
        'daily_sales': daily_sales['total'] or 0,
        'daily_sales_count': daily_sales['count'] or 0,
        'cashiers': cashier_data,
        'now': datetime.now(),
    }
    return render(request, 'dashboard/welcome.html', context)


@login_required
def index(request):
    if hasattr(request.user, 'profile') and request.user.profile.role == 'cashier':
        return redirect('sales:pos')
    today = timezone.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    start_of_month = today.replace(day=1)

    branch_filter, current_branch = _get_branch_filter(request)

    daily_sales = Sale.objects.filter(created_at__date=today, status='completed', **branch_filter).aggregate(
        total=Sum('total'), count=Count('id')
    )
    weekly_sales = Sale.objects.filter(created_at__date__gte=start_of_week, status='completed', **branch_filter).aggregate(
        total=Sum('total'), count=Count('id')
    )
    monthly_sales = Sale.objects.filter(created_at__date__gte=start_of_month, status='completed', **branch_filter).aggregate(
        total=Sum('total'), count=Count('id')
    )

    today_expenses = Expense.objects.filter(date=today, **branch_filter).aggregate(total=Sum('amount'))
    monthly_expenses = Expense.objects.filter(date__gte=start_of_month, **branch_filter).aggregate(total=Sum('amount'))

    total_products = Product.objects.filter(is_active=True).count()
    low_stock_products = Product.objects.filter(quantity__lte=models.F('reorder_level'), is_active=True)
    low_stock_count = low_stock_products.count()

    stock_value = Product.objects.filter(is_active=True).aggregate(
        total=Sum(models.F('quantity') * models.F('buying_price'))
    )

    top_selling = SaleItem.objects.filter(sale__status='completed').values('product_name').annotate(
        total_qty=Sum('quantity'), total_revenue=Sum('subtotal')
    ).order_by('-total_qty')[:10]
    if current_branch:
        top_selling = SaleItem.objects.filter(sale__branch=current_branch, sale__status='completed').values('product_name').annotate(
            total_qty=Sum('quantity'), total_revenue=Sum('subtotal')
        ).order_by('-total_qty')[:10]

    recent_sales = Sale.objects.filter(status='completed', **branch_filter).select_related('cashier')[:10]

    today_stock_sheet = StockSheet.objects.filter(date=today, **branch_filter).aggregate(
        total_sold=Sum('moved_stock'),
        total_revenue=Sum(F('moved_stock') * F('selling_price')),
        total_remaining=Sum('remaining_stock'),
    )
    best_stock_items = StockSheet.objects.filter(date=today, **branch_filter).values('item__name').annotate(
        total_sold=Sum('moved_stock'),
        total_revenue=Sum(F('moved_stock') * F('selling_price')),
    ).order_by('-total_sold')[:5]

    sales_data = Sale.objects.filter(
        created_at__date__gte=today - timedelta(days=30),
        status='completed',
        **branch_filter
    ).annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(
        total=Sum('total')
    ).order_by('date')

    branch_revenues = []
    if not current_branch:
        for b in Branch.objects.filter(is_active=True):
            rev = Sale.objects.filter(branch=b, created_at__date=today, status='completed').aggregate(
                total=Sum('total')
            )['total'] or 0
            exp = Expense.objects.filter(branch=b, date=today).aggregate(total=Sum('amount'))['total'] or 0
            branch_revenues.append({
                'branch': b,
                'revenue': rev,
                'expenses': exp,
                'profit': rev - exp,
            })
        branch_revenues.sort(key=lambda x: x['revenue'], reverse=True)

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
        'branch_revenues': branch_revenues,
        'current_branch': current_branch,
    }
    return render(request, 'dashboard/index.html', context)
