from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q, F
from django.utils import timezone
from datetime import timedelta, datetime
from sales.models import Sale, SaleItem
from inventory.models import Product, Category, StockSheet
from expenses.models import Expense
from branches.models import Branch
from accounts.decorators import role_required
import json


def _get_branch_filter(request):
    branch = getattr(request, 'current_branch', None)
    if branch:
        return {'branch': branch}, branch
    return {}, None


@login_required
@role_required('super_admin', 'manager')
def reports_index(request):
    today = timezone.now().date()
    start_of_month = today.replace(day=1)
    branch_filter, current_branch = _get_branch_filter(request)

    daily_sales = Sale.objects.filter(created_at__date=today, status='completed', **branch_filter).aggregate(
        total=Sum('total'), count=Count('id')
    )
    monthly_sales = Sale.objects.filter(created_at__date__gte=start_of_month, status='completed', **branch_filter).aggregate(
        total=Sum('total'), count=Count('id')
    )

    branch_reports = []
    if not current_branch:
        for b in Branch.objects.filter(is_active=True):
            bs = Sale.objects.filter(branch=b, created_at__date=today, status='completed').aggregate(
                total=Sum('total'), count=Count('id')
            )
            be = Expense.objects.filter(branch=b, date=today).aggregate(total=Sum('amount'))
            branch_reports.append({
                'branch': b,
                'sales': bs['total'] or 0,
                'count': bs['count'] or 0,
                'expenses': be['total'] or 0,
            })

    context = {
        'daily_sales': daily_sales['total'] or 0,
        'daily_count': daily_sales['count'] or 0,
        'monthly_sales': monthly_sales['total'] or 0,
        'monthly_count': monthly_sales['count'] or 0,
        'branch_reports': branch_reports,
        'current_branch': current_branch,
    }
    return render(request, 'reports/index.html', context)


@login_required
@role_required('super_admin', 'manager')
def daily_report(request):
    date_str = request.GET.get('date', timezone.now().date())
    if isinstance(date_str, str):
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        date = date_str
    branch_filter, current_branch = _get_branch_filter(request)

    sales = Sale.objects.filter(created_at__date=date, status='completed', **branch_filter)
    expenses = Expense.objects.filter(date=date, **branch_filter)
    total_sales = sales.aggregate(total=Sum('total'))['total'] or 0
    total_expenses = expenses.aggregate(total=Sum('amount'))['total'] or 0

    stock_sheets = StockSheet.objects.filter(date=date, **branch_filter).select_related('item', 'category')
    ss_totals = stock_sheets.aggregate(
        total_sold=Sum('moved_stock'), total_revenue=Sum(F('moved_stock') * F('selling_price'))
    )

    return render(request, 'reports/daily_report.html', {
        'date': date, 'sales': sales, 'expenses': expenses,
        'total_sales': total_sales, 'total_expenses': total_expenses,
        'profit': total_sales - total_expenses,
        'stock_sheets': stock_sheets,
        'ss_total_sold': ss_totals['total_sold'] or 0,
        'ss_total_revenue': ss_totals['total_revenue'] or 0,
        'current_branch': current_branch,
    })


@login_required
@role_required('super_admin', 'manager')
def weekly_report(request):
    date_str = request.GET.get('date', timezone.now().date())
    if isinstance(date_str, str):
        today = datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        today = date_str
    branch_filter, current_branch = _get_branch_filter(request)

    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    sales = Sale.objects.filter(
        created_at__date__gte=start_of_week, created_at__date__lte=end_of_week,
        status='completed', **branch_filter
    )
    expenses = Expense.objects.filter(date__gte=start_of_week, date__lte=end_of_week, **branch_filter)
    total_sales = sales.aggregate(total=Sum('total'))['total'] or 0
    total_expenses = expenses.aggregate(total=Sum('amount'))['total'] or 0

    stock_sheets = StockSheet.objects.filter(date__gte=start_of_week, date__lte=end_of_week, **branch_filter)
    ss_totals = stock_sheets.aggregate(
        total_sold=Sum('moved_stock'), total_revenue=Sum(F('moved_stock') * F('selling_price'))
    )

    return render(request, 'reports/weekly_report.html', {
        'start_date': start_of_week, 'end_date': end_of_week,
        'sales': sales, 'expenses': expenses,
        'total_sales': total_sales, 'total_expenses': total_expenses,
        'profit': total_sales - total_expenses,
        'ss_total_sold': ss_totals['total_sold'] or 0,
        'ss_total_revenue': ss_totals['total_revenue'] or 0,
        'current_branch': current_branch,
    })


@login_required
@role_required('super_admin', 'manager')
def monthly_report(request):
    year = int(request.GET.get('year', timezone.now().year))
    month = int(request.GET.get('month', timezone.now().month))
    branch_filter, current_branch = _get_branch_filter(request)

    sales = Sale.objects.filter(
        created_at__year=year, created_at__month=month, status='completed', **branch_filter
    )
    expenses = Expense.objects.filter(date__year=year, date__month=month, **branch_filter)
    total_sales = sales.aggregate(total=Sum('total'))['total'] or 0
    total_expenses = expenses.aggregate(total=Sum('amount'))['total'] or 0

    stock_sheets = StockSheet.objects.filter(date__year=year, date__month=month, **branch_filter)
    ss_totals = stock_sheets.aggregate(
        total_sold=Sum('moved_stock'), total_revenue=Sum(F('moved_stock') * F('selling_price'))
    )

    return render(request, 'reports/monthly_report.html', {
        'year': year, 'month': month,
        'sales': sales, 'expenses': expenses,
        'total_sales': total_sales, 'total_expenses': total_expenses,
        'profit': total_sales - total_expenses,
        'ss_total_sold': ss_totals['total_sold'] or 0,
        'ss_total_revenue': ss_totals['total_revenue'] or 0,
        'current_branch': current_branch,
    })


@login_required
@role_required('super_admin', 'manager')
def profit_report(request):
    date_from = request.GET.get('date_from', timezone.now().replace(day=1).date())
    date_to = request.GET.get('date_to', timezone.now().date())
    branch_filter, current_branch = _get_branch_filter(request)

    sales_total = Sale.objects.filter(
        created_at__date__gte=date_from, created_at__date__lte=date_to, status='completed', **branch_filter
    ).aggregate(total=Sum('total'))['total'] or 0

    expenses_total = Expense.objects.filter(
        date__gte=date_from, date__lte=date_to, **branch_filter
    ).aggregate(total=Sum('amount'))['total'] or 0

    cogs = SaleItem.objects.filter(
        sale__created_at__date__gte=date_from, sale__created_at__date__lte=date_to,
        sale__status='completed'
    ).aggregate(
        total=Sum(F('quantity') * F('product__buying_price'))
    )['total'] or 0

    return render(request, 'reports/profit_report.html', {
        'date_from': date_from, 'date_to': date_to,
        'revenue': sales_total, 'expenses': expenses_total,
        'cogs': cogs, 'gross_profit': sales_total - cogs,
        'net_profit': sales_total - cogs - expenses_total,
        'current_branch': current_branch,
    })


@login_required
@role_required('super_admin', 'manager')
def stock_report(request):
    _, current_branch = _get_branch_filter(request)
    products = Product.objects.filter(is_active=True).select_related('category', 'supplier')
    total_value = products.aggregate(total=Sum(F('quantity') * F('buying_price')))['total'] or 0
    total_revenue = products.aggregate(total=Sum(F('quantity') * F('selling_price')))['total'] or 0

    return render(request, 'reports/stock_report.html', {
        'products': products,
        'total_value': total_value,
        'total_revenue': total_revenue,
        'potential_profit': total_revenue - total_value,
        'current_branch': current_branch,
    })


@login_required
@role_required('super_admin', 'manager')
def product_movement(request):
    date_from = request.GET.get('date_from', (timezone.now() - timedelta(days=30)).date())
    date_to = request.GET.get('date_to', timezone.now().date())
    branch_filter, current_branch = _get_branch_filter(request)

    sale_filter = {'sale__created_at__date__gte': date_from, 'sale__created_at__date__lte': date_to, 'sale__status': 'completed'}
    if current_branch:
        sale_filter['sale__branch'] = current_branch

    movement = SaleItem.objects.filter(**sale_filter).values('product_name').annotate(
        total_qty=Sum('quantity'),
        total_revenue=Sum('subtotal')
    ).order_by('-total_qty')

    return render(request, 'reports/product_movement.html', {
        'movement': movement, 'date_from': date_from, 'date_to': date_to,
        'current_branch': current_branch,
    })


@login_required
@role_required('super_admin', 'manager')
def cashier_report(request):
    date_from = request.GET.get('date_from', timezone.now().date())
    date_to = request.GET.get('date_to', timezone.now().date())
    branch_filter, current_branch = _get_branch_filter(request)

    cashiers = Sale.objects.filter(
        created_at__date__gte=date_from, created_at__date__lte=date_to,
        status='completed', **branch_filter
    ).values('cashier__username').annotate(
        total_sales=Sum('total'),
        count=Count('id')
    ).order_by('-total_sales')

    return render(request, 'reports/cashier_report.html', {
        'cashiers': cashiers, 'date_from': date_from, 'date_to': date_to,
        'current_branch': current_branch,
    })


@login_required
@role_required('super_admin', 'manager')
def low_stock_report(request):
    _, current_branch = _get_branch_filter(request)
    products = Product.objects.filter(
        quantity__lte=F('reorder_level'), is_active=True
    ).select_related('category', 'supplier')
    return render(request, 'reports/low_stock_report.html', {
        'products': products,
        'current_branch': current_branch,
    })
