from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q, F
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from .models import Branch, StockTransfer
from .forms import BranchForm, StockTransferForm
from accounts.decorators import role_required
from accounts.models import ActivityLog
from inventory.models import Product, StockSheet
from sales.models import Sale, SaleItem
from expenses.models import Expense


@login_required
@role_required('super_admin')
def branch_list(request):
    branches = Branch.objects.all()
    now = timezone.now().date()
    total_product_count = Product.objects.filter(is_active=True).count()
    total_stock_value = Product.objects.filter(is_active=True).aggregate(
        total=Sum(F('quantity') * F('buying_price'))
    )['total'] or 0
    for b in branches:
        b.revenue = Sale.objects.filter(branch=b, created_at__date=now, status='completed').aggregate(
            total=Sum('total')
        )['total'] or 0
        b.product_count = total_product_count
        b.inventory_value = total_stock_value
    return render(request, 'branches/branch_list.html', {'branches': branches})


@login_required
@role_required('super_admin')
def branch_add(request):
    if request.method == 'POST':
        form = BranchForm(request.POST, request.FILES)
        if form.is_valid():
            branch = form.save()
            ActivityLog.objects.create(
                user=request.user,
                action=f'Created branch {branch.branch_name}',
                model_name='Branch',
                object_id=branch.id,
                ip_address=request.META.get('REMOTE_ADDR')
            )
            messages.success(request, f'Branch "{branch.branch_name}" created!')
            return redirect('branches:branch_list')
    else:
        form = BranchForm()
    return render(request, 'branches/branch_form.html', {'form': form, 'title': 'Add Branch'})


@login_required
@role_required('super_admin')
def branch_edit(request, pk):
    branch = get_object_or_404(Branch, pk=pk)
    if request.method == 'POST':
        form = BranchForm(request.POST, request.FILES, instance=branch)
        if form.is_valid():
            form.save()
            ActivityLog.objects.create(
                user=request.user,
                action=f'Updated branch {branch.branch_name}',
                model_name='Branch',
                object_id=branch.id,
                ip_address=request.META.get('REMOTE_ADDR')
            )
            messages.success(request, f'Branch "{branch.branch_name}" updated!')
            return redirect('branches:branch_list')
    else:
        form = BranchForm(instance=branch)
    return render(request, 'branches/branch_form.html', {'form': form, 'title': 'Edit Branch'})


@login_required
@role_required('super_admin')
def branch_toggle(request, pk):
    branch = get_object_or_404(Branch, pk=pk)
    branch.is_active = not branch.is_active
    branch.save()
    status = 'activated' if branch.is_active else 'deactivated'
    ActivityLog.objects.create(
        user=request.user,
        action=f'{status} branch {branch.branch_name}',
        model_name='Branch',
        object_id=branch.id,
        ip_address=request.META.get('REMOTE_ADDR')
    )
    messages.success(request, f'Branch "{branch.branch_name}" {status}.')
    return redirect('branches:branch_list')


@login_required
def switch_branch(request):
    if request.method == 'POST':
        branch_id = request.POST.get('branch_id')
    else:
        branch_id = request.GET.get('branch_id')

    if branch_id:
        branch = get_object_or_404(Branch, pk=branch_id, is_active=True)
        profile = request.user.profile
        allowed = (profile.role == 'super_admin' or
                   (profile.role == 'manager' and branch.manager == request.user) or
                   (profile.branch and profile.branch_id == branch.id))
        if allowed:
            request.session['active_branch'] = branch.id
            messages.success(request, f'Switched to {branch.branch_name}')
        else:
            messages.error(request, 'You do not have permission to switch to that branch.')
    return redirect(request.META.get('HTTP_REFERER', 'dashboard:index'))


@login_required
def branch_dashboard(request, pk):
    branch = get_object_or_404(Branch, pk=pk, is_active=True)
    today = timezone.now().date()
    start_of_month = today.replace(day=1)

    profile = request.user.profile
    if profile.role != 'super_admin':
        if profile.branch_id != branch.id:
            messages.error(request, 'Access denied.')
            return redirect('dashboard:index')

    daily_sales = Sale.objects.filter(branch=branch, created_at__date=today, status='completed').aggregate(
        total=Sum('total'), count=Count('id')
    )
    monthly_sales = Sale.objects.filter(branch=branch, created_at__date__gte=start_of_month, status='completed').aggregate(
        total=Sum('total'), count=Count('id')
    )
    today_expenses = Expense.objects.filter(branch=branch, date=today).aggregate(total=Sum('amount'))
    monthly_expenses = Expense.objects.filter(branch=branch, date__gte=start_of_month).aggregate(total=Sum('amount'))

    total_products = Product.objects.filter(is_active=True).count()
    low_stock_products = Product.objects.filter(quantity__lte=F('reorder_level'), is_active=True)
    stock_value = Product.objects.filter(is_active=True).aggregate(
        total=Sum(F('quantity') * F('buying_price'))
    )

    top_selling = SaleItem.objects.filter(sale__branch=branch).values('product_name').annotate(
        total_qty=Sum('quantity'), total_revenue=Sum('subtotal')
    ).order_by('-total_qty')[:10]

    recent_sales = Sale.objects.filter(branch=branch, status='completed').select_related('cashier')[:10]

    today_stock_sheet = StockSheet.objects.filter(branch=branch, date=today).aggregate(
        total_sold=Sum('moved_stock'),
        total_revenue=Sum(F('moved_stock') * F('selling_price')),
        total_remaining=Sum('remaining_stock'),
    )

    sales_data = Sale.objects.filter(
        branch=branch, created_at__date__gte=today - timedelta(days=30), status='completed'
    ).extra(
        select={'date': "date(created_at)"}
    ).values('date').annotate(
        total=Sum('total')
    ).order_by('date')

    low_stock_count = low_stock_products.count()
    context = {
        'branch': branch,
        'daily_sales': daily_sales['total'] or 0,
        'daily_sales_count': daily_sales['count'] or 0,
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
    }
    return render(request, 'branches/branch_dashboard.html', context)


@login_required
def transfer_list(request):
    profile = request.user.profile
    is_admin = profile.role == 'super_admin'

    if is_admin:
        transfers = StockTransfer.objects.select_related('from_branch', 'to_branch', 'product', 'requested_by')
    else:
        branch_ids = []
        if profile.branch:
            branch_ids.append(profile.branch_id)
        if profile.role == 'manager':
            branch_ids.extend(Branch.objects.filter(manager=request.user).values_list('id', flat=True))
        transfers = StockTransfer.objects.filter(
            Q(from_branch_id__in=branch_ids) | Q(to_branch_id__in=branch_ids)
        ).select_related('from_branch', 'to_branch', 'product', 'requested_by')

    status = request.GET.get('status', '')
    if status:
        transfers = transfers.filter(status=status)

    return render(request, 'branches/transfer_list.html', {
        'transfers': transfers,
        'current_status': status,
    })


@login_required
def transfer_add(request):
    profile = request.user.profile
    is_admin = profile.role == 'super_admin'

    if request.method == 'POST':
        form = StockTransferForm(request.POST)
        if form.is_valid():
            transfer = form.save(commit=False)
            transfer.requested_by = request.user
            # Convert warehouse units to base units for correct stock math
            if transfer.product:
                transfer.quantity = transfer.product.convert_purchase_to_base(transfer.quantity)
            transfer.save()
            ActivityLog.objects.create(
                user=request.user,
                action=f'Requested transfer of {transfer.product.name} from {transfer.from_branch.branch_name} to {transfer.to_branch.branch_name}',
                model_name='StockTransfer',
                object_id=transfer.id,
                ip_address=request.META.get('REMOTE_ADDR')
            )
            messages.success(request, 'Transfer request created!')
            return redirect('branches:transfer_list')
    else:
        initial = {}
        if not is_admin and profile.branch:
            initial['from_branch'] = profile.branch
        form = StockTransferForm(initial=initial)

    if is_admin:
        form.fields['from_branch'].queryset = Branch.objects.filter(is_active=True)
        form.fields['to_branch'].queryset = Branch.objects.filter(is_active=True)
    elif profile.branch:
        form.fields['from_branch'].queryset = Branch.objects.filter(id=profile.branch_id, is_active=True)
        form.fields['to_branch'].queryset = Branch.objects.filter(is_active=True).exclude(id=profile.branch_id)

    return render(request, 'branches/transfer_form.html', {'form': form, 'title': 'New Transfer'})


@login_required
def transfer_approve(request, pk):
    transfer = get_object_or_404(StockTransfer, pk=pk, status='pending')
    if request.method == 'POST':
        transfer.status = 'approved'
        transfer.approved_by = request.user
        transfer.save()
        ActivityLog.objects.create(
            user=request.user,
            action=f'Approved transfer of {transfer.product.name} from {transfer.from_branch.branch_name}',
            model_name='StockTransfer',
            object_id=transfer.id,
            ip_address=request.META.get('REMOTE_ADDR')
        )
        messages.success(request, 'Transfer approved.')
    return redirect('branches:transfer_list')


@login_required
def transfer_reject(request, pk):
    transfer = get_object_or_404(StockTransfer, pk=pk, status='pending')
    if request.method == 'POST':
        transfer.status = 'rejected'
        transfer.approved_by = request.user
        transfer.save()
        ActivityLog.objects.create(
            user=request.user,
            action=f'Rejected transfer of {transfer.product.name} from {transfer.from_branch.branch_name}',
            model_name='StockTransfer',
            object_id=transfer.id,
            ip_address=request.META.get('REMOTE_ADDR')
        )
        messages.success(request, 'Transfer rejected.')
    return redirect('branches:transfer_list')


@login_required
def transfer_complete(request, pk):
    transfer = get_object_or_404(StockTransfer, pk=pk, status='approved')
    if request.method == 'POST':
        from_product = Product.objects.filter(name=transfer.product.name).first()
        to_product = from_product

        if not from_product:
            messages.error(request, f'Source branch has no product: {transfer.product.name}')
            return redirect('branches:transfer_list')

        if from_product.quantity < transfer.quantity:
            messages.error(request, f'Insufficient stock at source. Available: {from_product.quantity}')
            return redirect('branches:transfer_list')

        from_product.quantity -= transfer.quantity
        from_product.save()

        if to_product:
            to_product.quantity += transfer.quantity
            to_product.save()
        else:
            Product.objects.create(
                name=transfer.product.name,
                category=transfer.product.category,
                buying_price=transfer.product.buying_price,
                selling_price=transfer.product.selling_price,
                quantity=transfer.quantity,
                branch=transfer.to_branch,
                unit_type=transfer.product.unit_type,
                units_per_crate=transfer.product.units_per_crate,
                units_per_pack=transfer.product.units_per_pack,
                shots_per_bottle=transfer.product.shots_per_bottle,
                selling_unit=transfer.product.selling_unit,
                reorder_level=transfer.product.reorder_level,
                is_active=True,
            )

        transfer.status = 'completed'
        transfer.save()
        ActivityLog.objects.create(
            user=request.user,
            action=f'Completed transfer of {transfer.quantity} x {transfer.product.name} from {transfer.from_branch.branch_name} to {transfer.to_branch.branch_name}',
            model_name='StockTransfer',
            object_id=transfer.id,
            ip_address=request.META.get('REMOTE_ADDR')
        )
        messages.success(request, 'Transfer completed successfully!')
    return redirect('branches:transfer_list')
