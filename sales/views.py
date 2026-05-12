import json
import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q
from django.core.paginator import Paginator
from django.utils import timezone
from django.http import JsonResponse
from .models import Sale, SaleItem
from inventory.models import Product, Category, SalesSheet
from inventory.services.conversion_engine import (
    get_selling_unit, get_selling_unit_label,
    validate_stock_input, calculate_amount,
)
from accounts.decorators import role_required
from accounts.models import ActivityLog
from branches.models import Branch, StockTransfer


def _get_branch_filter(request):
    branch = getattr(request, 'current_branch', None)
    if branch:
        return {'branch': branch}, branch
    return {}, None


@login_required
def pos_index(request):
    profile = request.user.profile
    _, current_branch = _get_branch_filter(request)
    products = Product.objects.filter(is_active=True).select_related('category')
    categories = Category.objects.filter(name__in=['Beers & Softs', 'Ciders & Wines', 'Spirits & Others'])

    products = profile.filter_products(products)
    categories = profile.filter_categories(categories)

    return render(request, 'sales/pos.html', {
        'products': products,
        'categories': categories,
        'current_branch': current_branch,
    })


@login_required
def search_products(request):
    q = request.GET.get('q', '')
    profile = request.user.profile
    products = Product.objects.filter(
        is_active=True
    ).filter(
        Q(name__icontains=q) | Q(barcode__icontains=q)
    )
    products = profile.filter_products(products)
    products = products.values('id', 'name', 'selling_price', 'quantity', 'barcode')
    return JsonResponse(list(products), safe=False)


@login_required
def create_sale(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        product_id = data.get('product_id')
        payment_method = data.get('payment_method', 'cash')
        amount_paid = float(data.get('amount_paid', 0))

        if not product_id:
            return JsonResponse({'error': 'No product specified'}, status=400)

        product = get_object_or_404(Product, pk=product_id)
        allowed_ids = request.user.profile.get_allowed_category_ids()
        if allowed_ids is not None and product.category_id not in allowed_ids:
            return JsonResponse({'error': f'Product "{product.name}" is not in your allowed categories'}, status=403)

        current_branch = getattr(request, 'current_branch', None)
        selling_unit = get_selling_unit(product)
        total_stock = product.quantity
        shots_per_bottle = product.shots_per_bottle or 1

        if selling_unit == 'Glass':
            remaining = int(data.get('remaining_glasses', 0))
            valid, result = validate_stock_input(remaining, total_stock)
            if not valid:
                return JsonResponse({'error': result}, status=400)
            sold_qty = result
            item_subtotal = calculate_amount(sold_qty, product.selling_price)
            product.bottle_quantity = remaining
            product.quantity = remaining
            product.pack_quantity = 0
            product.crate_quantity = 0

        elif selling_unit == 'Shot':
            remaining_bottles = int(data.get('remaining_bottles', 0))
            remaining_shots = int(data.get('remaining_shots', 0))
            remaining_base = remaining_bottles * shots_per_bottle + remaining_shots
            if remaining_base > total_stock:
                return JsonResponse({'error': f'Remaining stock cannot exceed total stock for {product.name}'}, status=400)
            if remaining_base < 0:
                return JsonResponse({'error': 'Negative values not allowed'}, status=400)
            sold_qty = total_stock - remaining_base
            if sold_qty == 0:
                return JsonResponse({'error': 'No stock sold. Remaining equals total.'}, status=400)
            item_subtotal = (float(product.selling_price) / shots_per_bottle) * sold_qty
            product.bottle_quantity = remaining_bottles
            product.shot_quantity = remaining_shots
            product.quantity = remaining_base
            product.pack_quantity = 0
            product.crate_quantity = 0

        else:
            remaining = int(data.get('remaining_bottles', 0))
            valid, result = validate_stock_input(remaining, total_stock)
            if not valid:
                return JsonResponse({'error': result}, status=400)
            sold_qty = result
            item_subtotal = calculate_amount(sold_qty, product.selling_price)
            product.bottle_quantity = remaining
            product.quantity = remaining
            product.pack_quantity = 0
            product.crate_quantity = 0

        # Create sale
        sale = Sale(
            cashier=request.user,
            payment_method=payment_method,
            amount_paid=amount_paid,
            subtotal=item_subtotal,
            total=item_subtotal,
            change_due=max(0, amount_paid - item_subtotal),
            branch=current_branch,
            status='pending',
        )
        sale.save()

        # Create sale item
        SaleItem.objects.create(
            sale=sale,
            product=product,
            product_name=product.name,
            quantity=sold_qty,
            price=float(product.selling_price),
            subtotal=item_subtotal,
            selling_unit=selling_unit,
        )

        # Update sale to completed (signal won't fire since status was pending during SaleItem creation)
        sale.status = 'completed'
        sale.save()

        # Persist stock changes
        product.save()

        # Directly update SalesSheet
        today = timezone.now().date()
        prev_date = today - datetime.timedelta(days=1)

        prev_sheets = SalesSheet.objects.filter(
            item=product, date=prev_date, branch=current_branch
        )
        prev_remain = prev_sheets.first().remaining_stock if prev_sheets.exists() else 0

        warehouse = Branch.objects.filter(branch_type='Warehouse', is_active=True).first()
        add_stock = 0
        if warehouse:
            pending = StockTransfer.objects.filter(
                from_branch=warehouse, to_branch=current_branch,
                product=product, status='pending'
            ).first()
            if pending:
                add_stock = pending.quantity

        SalesSheet.objects.update_or_create(
            item=product,
            date=today,
            branch=current_branch,
            defaults={
                'category': product.category,
                'open_stock': prev_remain,
                'add_stock': add_stock,
                'selling_price': product.selling_price,
                'sold_stock': sold_qty,
                'created_by': request.user,
            }
        )

        ActivityLog.objects.create(
            user=request.user,
            action=f'Created sale {sale.receipt_number}',
            model_name='Sale',
            object_id=sale.id,
            branch=current_branch,
            ip_address=request.META.get('REMOTE_ADDR')
        )

        resp = {
            'success': True,
            'receipt_number': sale.receipt_number,
            'sale_id': sale.id,
            'total': float(sale.total),
            'change_due': float(sale.change_due),
            'sold_qty': sold_qty,
            'amount': item_subtotal,
            'unit': get_selling_unit_label(product),
        }
        return JsonResponse(resp)

    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
def sale_detail(request, pk):
    sale = get_object_or_404(Sale.objects.prefetch_related('items'), pk=pk)
    return render(request, 'sales/sale_detail.html', {'sale': sale})


@login_required
def sale_receipt(request, pk):
    sale = get_object_or_404(Sale.objects.prefetch_related('items'), pk=pk)
    return render(request, 'sales/receipt.html', {'sale': sale})


@login_required
def sale_history(request):
    query = request.GET.get('q', '')
    status = request.GET.get('status', '')
    payment = request.GET.get('payment', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    branch_filter, _ = _get_branch_filter(request)

    sales = Sale.objects.select_related('cashier').filter(**branch_filter)

    if query:
        sales = sales.filter(
            Q(receipt_number__icontains=query) | Q(cashier__username__icontains=query)
        )
    if status:
        sales = sales.filter(status=status)
    if payment:
        sales = sales.filter(payment_method=payment)
    if date_from:
        sales = sales.filter(created_at__date__gte=date_from)
    if date_to:
        sales = sales.filter(created_at__date__lte=date_to)

    paginator = Paginator(sales, 20)
    page = request.GET.get('page')
    sales = paginator.get_page(page)

    return render(request, 'sales/sale_history.html', {'sales': sales})


@login_required
@role_required('super_admin', 'manager')
def refund_sale(request, pk):
    sale = get_object_or_404(Sale, pk=pk)
    if request.method == 'POST':
        if sale.status == 'refunded':
            messages.error(request, 'Sale already refunded.')
            return redirect('sales:sale_history')

        for item in sale.items.all():
            product = Product.objects.filter(name=item.product_name).first()
            if product:
                qty = item.quantity
                unit = item.selling_unit if hasattr(item, 'selling_unit') else 'Bottle'
                if unit == 'Crate':
                    product.crate_quantity += qty
                elif unit == 'Pack':
                    product.pack_quantity += qty
                elif unit == 'Shot':
                    product.shot_quantity += qty
                elif unit == 'Glass':
                    product.bottle_quantity += qty
                    product.quantity = product.bottle_quantity
                else:
                    product.bottle_quantity += qty
                product.save()

        sale.status = 'refunded'
        sale.save()

        ActivityLog.objects.create(
            user=request.user,
            action=f'Refunded sale {sale.receipt_number}',
            model_name='Sale',
            object_id=sale.id,
            branch=sale.branch,
            ip_address=request.META.get('REMOTE_ADDR')
        )
        messages.success(request, f'Sale {sale.receipt_number} refunded successfully.')
        return redirect('sales:sale_history')

    return render(request, 'sales/refund_confirm.html', {'sale': sale})
