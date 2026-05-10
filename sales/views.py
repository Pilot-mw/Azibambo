from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q
from django.core.paginator import Paginator
from django.utils import timezone
from django.http import JsonResponse
from .models import Sale, SaleItem
from inventory.models import Product
from accounts.models import ActivityLog
import json

@login_required
def pos_index(request):
    products = Product.objects.filter(is_active=True, quantity__gt=0).select_related('category')
    categories = products.values('category__name', 'category__id').distinct()
    return render(request, 'sales/pos.html', {
        'products': products,
        'categories': categories,
    })

@login_required
def search_products(request):
    q = request.GET.get('q', '')
    products = Product.objects.filter(
        is_active=True, quantity__gt=0
    ).filter(
        Q(name__icontains=q) | Q(barcode__icontains=q)
    ).values('id', 'name', 'selling_price', 'quantity', 'barcode')
    return JsonResponse(list(products), safe=False)

@login_required
def create_sale(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        items = data.get('items', [])
        payment_method = data.get('payment_method', 'cash')
        amount_paid = float(data.get('amount_paid', 0))

        if not items:
            return JsonResponse({'error': 'No items in cart'}, status=400)

        sale = Sale(
            cashier=request.user,
            payment_method=payment_method,
            amount_paid=amount_paid,
        )

        subtotal = 0
        sale_items_data = []

        for item in items:
            product = get_object_or_404(Product, pk=item['product_id'])
            qty = int(item['quantity'])
            selling_unit = item.get('selling_unit', product.selling_unit)
            units_in_pack = product.units_per_pack
            bottles_per_crate = product.units_per_crate

            if selling_unit == 'Pack':
                bottle_qty = qty * units_in_pack
            elif selling_unit == 'Crate':
                bottle_qty = qty * bottles_per_crate
            elif selling_unit in ('Bottle', 'Bottle/Can'):
                bottle_qty = qty * product.shots_per_bottle
            elif selling_unit == 'Shot':
                bottle_qty = qty
            else:
                bottle_qty = qty

            if bottle_qty > product.quantity:
                available_display = product.display_stock if hasattr(product, 'display_stock') else str(product.quantity)
                return JsonResponse({
                    'error': f'Insufficient stock for {product.name}. Available: {available_display}'
                }, status=400)

            if selling_unit == 'Shot':
                item_subtotal = (float(product.selling_price) / product.shots_per_bottle) * qty
            else:
                item_subtotal = float(product.selling_price) * qty
            subtotal += item_subtotal

            sale_items_data.append({
                'product': product,
                'product_name': product.name,
                'quantity': qty,
                'price': float(product.selling_price),
                'subtotal': item_subtotal,
                'selling_unit': selling_unit,
            })

        sale.subtotal = subtotal
        sale.total = subtotal
        sale.change_due = max(0, amount_paid - subtotal)
        sale.save()

        for item_data in sale_items_data:
            SaleItem.objects.create(
                sale=sale,
                product=item_data['product'],
                product_name=item_data['product_name'],
                quantity=item_data['quantity'],
                price=item_data['price'],
                subtotal=item_data['subtotal'],
                selling_unit=item_data.get('selling_unit', 'Bottle'),
            )
            product = item_data['product']
            selling_unit = item_data.get('selling_unit', product.selling_unit)
            qty = item_data['quantity']
            if selling_unit == 'Crate':
                product.crate_quantity = max(0, product.crate_quantity - qty)
            elif selling_unit == 'Pack':
                product.pack_quantity = max(0, product.pack_quantity - qty)
            elif selling_unit in ('Bottle', 'Bottle/Can'):
                product.bottle_quantity = max(0, product.bottle_quantity - qty)
            elif selling_unit == 'Shot':
                product.shot_quantity = max(0, product.shot_quantity - qty)
            else:
                product.bottle_quantity = max(0, product.bottle_quantity - qty)
            product.save()

        ActivityLog.objects.create(
            user=request.user,
            action=f'Created sale {sale.receipt_number}',
            model_name='Sale',
            object_id=sale.id,
            ip_address=request.META.get('REMOTE_ADDR')
        )

        return JsonResponse({
            'success': True,
            'receipt_number': sale.receipt_number,
            'sale_id': sale.id,
            'total': float(sale.total),
            'change_due': float(sale.change_due),
        })

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

    sales = Sale.objects.select_related('cashier')

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
                if hasattr(item, 'selling_unit') and item.selling_unit == 'Crate':
                    product.crate_quantity += qty
                elif hasattr(item, 'selling_unit') and item.selling_unit == 'Pack':
                    product.pack_quantity += qty
                elif hasattr(item, 'selling_unit') and item.selling_unit == 'Shot':
                    product.shot_quantity += qty
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
            ip_address=request.META.get('REMOTE_ADDR')
        )
        messages.success(request, f'Sale {sale.receipt_number} refunded successfully.')
        return redirect('sales:sale_history')

    return render(request, 'sales/refund_confirm.html', {'sale': sale})
