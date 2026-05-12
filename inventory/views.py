import json, datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, F, Count
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from .models import Product, Category, StockSheet, SalesSheet
from .forms import ProductForm, CategoryForm, StockSheetForm
from .services.conversion_engine import get_selling_unit_label, get_purchase_unit_label, get_conversion_rate, convert_base_to_warehouse
from accounts.decorators import role_required
from accounts.models import ActivityLog
from branches.models import Branch, StockTransfer


def _get_branch_filter(request):
    branch = getattr(request, 'current_branch', None)
    if branch:
        return {'branch': branch}, branch
    return {}, None


@login_required
@role_required('super_admin', 'manager', 'store_keeper')
def product_list(request):
    query = request.GET.get('q', '')
    category_id = request.GET.get('category', '')
    _, current_branch = _get_branch_filter(request)
    products = Product.objects.filter(is_active=True).select_related('category', 'supplier')

    if query:
        products = products.filter(
            Q(name__icontains=query) | Q(barcode__icontains=query)
        )
    if category_id:
        products = products.filter(category_id=category_id)

    paginator = Paginator(products, 20)
    page = request.GET.get('page')
    products = paginator.get_page(page)

    categories = Category.objects.all()

    context = {
        'products': products,
        'categories': categories,
        'query': query,
        'selected_category': category_id,
        'current_branch': current_branch,
    }
    return render(request, 'inventory/product_list.html', context)


@login_required
@role_required('super_admin', 'manager', 'store_keeper')
def product_add(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            branch = getattr(request, 'current_branch', None)
            if branch:
                product.branch = branch
            product.save()
            ActivityLog.objects.create(
                user=request.user,
                action=f'Added product {product.name}',
                model_name='Product',
                object_id=product.id,
                branch=getattr(request, 'current_branch', None),
                ip_address=request.META.get('REMOTE_ADDR')
            )
            messages.success(request, f'Product "{product.name}" added successfully!')
            return redirect('inventory:product_list')
    else:
        form = ProductForm()
    return render(request, 'inventory/product_form.html', {'form': form, 'title': 'Add Product'})


@login_required
@role_required('super_admin', 'manager', 'store_keeper')
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            product = form.save()
            ActivityLog.objects.create(
                user=request.user,
                action=f'Updated product {product.name}',
                model_name='Product',
                object_id=product.id,
                branch=getattr(request, 'current_branch', None),
                ip_address=request.META.get('REMOTE_ADDR')
            )
            messages.success(request, f'Product "{product.name}" updated successfully!')
            return redirect('inventory:product_list')
    else:
        form = ProductForm(instance=product)
    return render(request, 'inventory/product_form.html', {'form': form, 'title': 'Edit Product'})


@login_required
@role_required('super_admin', 'manager', 'store_keeper')
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        name = product.name
        product.is_active = False
        product.save()
        ActivityLog.objects.create(
            user=request.user,
            action=f'Deleted product {name}',
            model_name='Product',
            object_id=pk,
            branch=getattr(request, 'current_branch', None),
            ip_address=request.META.get('REMOTE_ADDR')
        )
        messages.success(request, f'Product "{name}" deleted successfully!')
        return redirect('inventory:product_list')
    return render(request, 'inventory/product_confirm_delete.html', {'product': product})


@login_required
@role_required('super_admin', 'manager', 'store_keeper')
def category_list(request):
    categories = Category.objects.all().annotate(product_count=Count('products'))
    return render(request, 'inventory/category_list.html', {'categories': categories})


@login_required
@role_required('super_admin', 'manager', 'store_keeper')
def category_add(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Category "{category.name}" created!')
            return redirect('inventory:category_list')
    else:
        form = CategoryForm()
    return render(request, 'inventory/category_form.html', {'form': form, 'title': 'Add Category'})


@login_required
@role_required('super_admin', 'manager', 'store_keeper')
def category_edit(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, 'Category updated!')
            return redirect('inventory:category_list')
    else:
        form = CategoryForm(instance=category)
    return render(request, 'inventory/category_form.html', {'form': form, 'title': 'Edit Category'})


@login_required
@role_required('super_admin', 'manager', 'store_keeper')
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        category.delete()
        messages.success(request, 'Category deleted!')
        return redirect('inventory:category_list')
    return render(request, 'inventory/category_confirm_delete.html', {'category': category})


def _get_warehouse():
    return Branch.objects.filter(branch_type='Warehouse', is_active=True).first()


@login_required
@role_required('super_admin', 'manager', 'store_keeper')
def stock_sheet(request):
    warehouse = _get_warehouse()
    if not warehouse:
        messages.error(request, 'No warehouse branch configured.')
        return redirect('dashboard:index')

    current_branch = getattr(request, 'current_branch', None)
    if current_branch and current_branch.id != warehouse.id:
        messages.error(request, 'Stock Sheet is only available for Main Warehouse.')
        return redirect('dashboard:index')

    today = datetime.date.today()
    categories = Category.objects.filter(name__in=['Beers & Softs', 'Ciders & Wines', 'Spirits & Others'])
    selected_date = request.GET.get('date', today.isoformat())
    cat_filter = request.GET.get('category', '')
    search_q = request.GET.get('q', '')
    parsed_date = datetime.date.fromisoformat(selected_date) if isinstance(selected_date, str) else selected_date
    prev_date = parsed_date - datetime.timedelta(days=1)

    cat_ids = categories.values_list('id', flat=True)
    products = Product.objects.filter(is_active=True, category_id__in=cat_ids).select_related('category')
    if cat_filter:
        products = products.filter(category__name=cat_filter)
    if search_q:
        products = products.filter(name__icontains=search_q)

    existing_sheets = {}
    for s in StockSheet.objects.filter(date=selected_date, item_id__in=products.values('id'), branch=warehouse):
        existing_sheets[s.item_id] = s

    prev_sheets = {}
    for s in StockSheet.objects.filter(date=prev_date.isoformat(), item_id__in=products.values('id'), branch=warehouse):
        prev_sheets[s.item_id] = s

    transfer_branches = Branch.objects.filter(is_active=True).exclude(id=warehouse.id)

    rows = []
    totals = {'open': 0, 'order': 0, 'total': 0, 'buying_value': 0, 'selling_value': 0, 'moved': 0, 'remain': 0}

    for product in products:
        rate = get_conversion_rate(product) or 1
        sheet = existing_sheets.get(product.id)
        if sheet:
            wh = lambda v: v // rate
            rows.append({
                'id': sheet.id,
                'item': sheet.item,
                'category': sheet.category,
                'open_stock': wh(sheet.open_stock),
                'order_stock': wh(sheet.order_stock),
                'total_stock': wh(sheet.total_stock),
                'buying_price': sheet.buying_price,
                'selling_price': sheet.selling_price,
                'moved_stock': wh(sheet.moved_stock),
                'remaining_stock': wh(sheet.remaining_stock),
                'date': sheet.date,
            })
        else:
            prev_sheet = prev_sheets.get(product.id)
            open_val = (prev_sheet.remaining_stock if prev_sheet else product.quantity) // rate
            rows.append({
                'id': None,
                'item': product,
                'category': product.category,
                'open_stock': open_val,
                'order_stock': 0,
                'total_stock': open_val,
                'buying_price': product.buying_price,
                'selling_price': product.selling_price,
                'moved_stock': 0,
                'remaining_stock': open_val,
                'date': parsed_date,
            })

    for r in rows:
        o = r.get('open_stock', 0)
        od = r.get('order_stock', 0)
        bp = float(r.get('buying_price', 0))
        sp = float(r.get('selling_price', 0))
        mv = r.get('moved_stock', 0)
        t = o + od
        rm = t - mv
        totals['open'] += o
        totals['order'] += od
        totals['total'] += t
        totals['buying_value'] += bp * t
        totals['selling_value'] += sp * t
        totals['moved'] += mv
        totals['remain'] += rm

    import json as json_lib
    cats_json = json_lib.dumps([{'name': c.name} for c in categories])

    return render(request, 'inventory/stock_sheet.html', {
        'rows': rows,
        'categories': categories,
        'categories_json': cats_json,
        'selected_date': selected_date,
        'selected_category': cat_filter,
        'search_q': search_q,
        'totals': totals,
        'transfer_branches': transfer_branches,
        'current_branch': warehouse,
    })


@login_required
@role_required('super_admin', 'manager', 'store_keeper')
@require_POST
def stock_sheet_save(request):
    try:
        warehouse = _get_warehouse()
        if not warehouse:
            return JsonResponse({'success': False, 'error': 'No warehouse configured'}, status=400)

        data = json.loads(request.body)
        item_id = data.get('item_id')
        open_wh = int(data.get('open_stock', 0))
        order_wh = int(data.get('order_stock', 0))
        moved_wh = int(data.get('moved_stock', 0))
        buying_price = float(data.get('buying_price', 0))
        selling_price = float(data.get('selling_price', 0))
        sheet_date = data.get('date', datetime.date.today().isoformat())
        transfer_to_id = data.get('transfer_to_branch_id')

        if moved_wh > (open_wh + order_wh):
            return JsonResponse({'success': False, 'error': 'MOVED cannot exceed TOTAL'}, status=400)
        if open_wh < 0 or order_wh < 0 or moved_wh < 0 or buying_price < 0 or selling_price < 0:
            return JsonResponse({'success': False, 'error': 'Negative values not allowed'}, status=400)

        item = get_object_or_404(Product, pk=item_id) if item_id else None
        if not item:
            return JsonResponse({'success': False, 'error': 'Item required'}, status=400)

        # Convert warehouse units to base units for DB storage
        rate = get_conversion_rate(item) or 1
        open_stock = open_wh * rate
        order_stock = order_wh * rate
        moved_stock = moved_wh * rate

        sheet, created = StockSheet.objects.get_or_create(
            item=item,
            date=sheet_date,
            branch=warehouse,
            defaults={
                'category': item.category,
                'open_stock': open_stock,
                'order_stock': order_stock,
                'buying_price': buying_price,
                'selling_price': selling_price,
                'moved_stock': moved_stock,
                'created_by': request.user,
            }
        )

        if not created:
            sheet.open_stock = open_stock
            sheet.order_stock = order_stock
            sheet.buying_price = buying_price
            sheet.selling_price = selling_price
            sheet.moved_stock = moved_stock
            sheet.save()

        if moved_stock > 0 and transfer_to_id:
            from_branch = warehouse
            to_branch = get_object_or_404(Branch, pk=transfer_to_id)
            existing_transfer = StockTransfer.objects.filter(
                from_branch=from_branch,
                to_branch=to_branch,
                product=item,
                status='pending',
            ).first()
            if existing_transfer:
                existing_transfer.quantity = moved_stock
                existing_transfer.save()
            else:
                StockTransfer.objects.create(
                    from_branch=from_branch,
                    to_branch=to_branch,
                    product=item,
                    quantity=moved_stock,
                    status='pending',
                    requested_by=request.user,
                )

        total = sheet.open_stock + sheet.order_stock

        return JsonResponse({
            'success': True,
            'id': sheet.id,
            'total_wh': total // rate,
            'remain_wh': sheet.remaining_stock // rate,
            'open_wh': open_wh,
            'order_wh': order_wh,
            'moved_wh': moved_wh,
            'item_id': item.id,
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@role_required('super_admin', 'manager', 'store_keeper')
@require_POST
def stock_sheet_delete(request):
    try:
        data = json.loads(request.body)
        sheet = get_object_or_404(StockSheet, pk=data.get('id'))
        sheet.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@role_required('super_admin', 'manager', 'store_keeper')
def stock_sheet_data(request):
    date_str = request.GET.get('date', datetime.date.today().isoformat())
    cat_filter = request.GET.get('category', '')
    branch_filter, _ = _get_branch_filter(request)
    sheets = StockSheet.objects.filter(date=date_str, **branch_filter).select_related('item', 'category')
    if cat_filter:
        sheets = sheets.filter(category__name=cat_filter)

    data = []
    for s in sheets:
        data.append({
            'id': s.id,
            'item_id': s.item.id if s.item else None,
            'item_name': s.item.name if s.item else '',
            'category': s.category.name if s.category else '',
            'open_stock': s.open_stock,
            'order_stock': s.order_stock,
            'total_stock': s.total_stock,
            'buying_price': float(s.buying_price),
            'selling_price': float(s.selling_price),
            'moved_stock': s.moved_stock,
            'remaining_stock': s.remaining_stock,
        })

    return JsonResponse({'data': data})


@login_required
@role_required('super_admin', 'manager', 'store_keeper', 'cashier')
def sales_sheet(request):
    from sales.models import SaleItem, Sale

    profile = request.user.profile
    is_cashier = profile.role == 'cashier'
    current_branch = getattr(request, 'current_branch', None)
    if not current_branch:
        messages.error(request, 'Please select a branch first.')
        return redirect('dashboard:index')

    warehouse = _get_warehouse()
    today = datetime.date.today()
    categories = Category.objects.filter(name__in=['Beers & Softs', 'Ciders & Wines', 'Spirits & Others'])
    categories = profile.filter_categories(categories)
    selected_date = request.GET.get('date', today.isoformat())
    cat_filter = request.GET.get('category', '')
    search_q = request.GET.get('q', '')
    parsed_date = datetime.date.fromisoformat(selected_date) if isinstance(selected_date, str) else selected_date
    prev_date = parsed_date - datetime.timedelta(days=1)

    cat_ids = categories.values_list('id', flat=True)
    products = Product.objects.filter(is_active=True, category_id__in=cat_ids).select_related('category')
    products = profile.filter_products(products)
    if cat_filter:
        products = products.filter(category__name=cat_filter)
    if search_q:
        products = products.filter(name__icontains=search_q)

    existing_sheets = {}
    for s in SalesSheet.objects.filter(date=selected_date, branch=current_branch).select_related('item', 'category'):
        existing_sheets[s.item_id] = s

    prev_sheets = {}
    for s in SalesSheet.objects.filter(date=prev_date.isoformat(), branch=current_branch).select_related('item', 'category'):
        prev_sheets[s.item_id] = s

    transfers = StockTransfer.objects.filter(
        from_branch=warehouse,
        to_branch=current_branch,
        status='pending',
    )
    transfer_map = {t.product_id: t.quantity for t in transfers}

    pos_sales_map = {}
    if is_cashier:
        pos_items = SaleItem.objects.filter(
            sale__branch=current_branch,
            sale__created_at__date=parsed_date,
            sale__status='completed',
        ).values('product_id').annotate(total_qty=Sum('quantity'))
        for item in pos_items:
            pos_sales_map[item['product_id']] = item['total_qty']

    rows = []
    totals = {'open': 0, 'add': 0, 'total': 0, 'sold': 0, 'remain': 0, 'revenue': 0}

    for product in products:
        sheet = existing_sheets.get(product.id)
        prev_sheet = prev_sheets.get(product.id)
        open_val = sheet.open_stock if sheet else (prev_sheet.remaining_stock if prev_sheet else 0)
        add_val = sheet.add_stock if sheet else transfer_map.get(product.id, 0)
        saved_price = float(sheet.selling_price) if sheet else float(product.selling_price)
        pos_sold = pos_sales_map.get(product.id, 0) if is_cashier else 0
        saved_sold = sheet.sold_stock if sheet else 0
        sold_val = pos_sold if is_cashier else saved_sold
        total = open_val + add_val
        remain = total - sold_val
        amt = sold_val * saved_price

        row_data = {
            'id': sheet.id if sheet else None,
            'item': product,
            'category': product.category,
            'open_stock': open_val,
            'add_stock': add_val,
            'total_stock': total,
            'selling_price': saved_price,
            'sold_stock': sold_val,
            'remaining_stock': remain,
            'amount': amt,
            'date': parsed_date,
        }
        rows.append(row_data)

        totals['open'] += open_val
        totals['add'] += add_val
        totals['total'] += total
        totals['sold'] += sold_val
        totals['remain'] += remain
        totals['revenue'] += amt

    import json as json_lib
    cats_json = json_lib.dumps([{'name': c.name} for c in categories])

    return render(request, 'inventory/sales_sheet.html', {
        'rows': rows,
        'categories': categories,
        'categories_json': cats_json,
        'selected_date': selected_date,
        'selected_category': cat_filter,
        'search_q': search_q,
        'totals': totals,
        'current_branch': current_branch,
        'is_cashier': is_cashier,
    })


@login_required
@role_required('super_admin', 'manager', 'store_keeper')
@require_POST
def sales_sheet_save(request):
    try:
        current_branch = getattr(request, 'current_branch', None)
        if not current_branch:
            return JsonResponse({'success': False, 'error': 'No branch selected'}, status=400)

        data = json.loads(request.body)
        item_id = data.get('item_id')
        open_stock = int(data.get('open_stock', 0))
        add_stock = int(data.get('add_stock', 0))
        remain_stock = int(data.get('remain_stock', 0))
        selling_price = float(data.get('selling_price', 0))
        sheet_date = data.get('date', datetime.date.today().isoformat())

        total_stock = open_stock + add_stock
        sold_stock = total_stock - remain_stock
        if sold_stock < 0:
            sold_stock = 0

        if remain_stock > total_stock:
            return JsonResponse({'success': False, 'error': 'REMAIN cannot exceed TOTAL'}, status=400)
        if open_stock < 0 or add_stock < 0 or remain_stock < 0 or selling_price < 0:
            return JsonResponse({'success': False, 'error': 'Negative values not allowed'}, status=400)

        item = get_object_or_404(Product, pk=item_id) if item_id else None
        if not item:
            return JsonResponse({'success': False, 'error': 'Item required'}, status=400)

        sheet, created = SalesSheet.objects.get_or_create(
            item=item,
            date=sheet_date,
            branch=current_branch,
            defaults={
                'category': item.category,
                'open_stock': open_stock,
                'add_stock': add_stock,
                'selling_price': selling_price,
                'sold_stock': sold_stock,
                'created_by': request.user,
            }
        )

        if not created:
            sheet.open_stock = open_stock
            sheet.add_stock = add_stock
            sheet.selling_price = selling_price
            sheet.sold_stock = sold_stock
            sheet.save()

        return JsonResponse({
            'success': True,
            'id': sheet.id,
            'total_stock': sheet.total_stock,
            'remaining_stock': sheet.remaining_stock,
            'sold_stock': sheet.sold_stock,
            'amount': float(sheet.amount),
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@role_required('super_admin', 'manager', 'store_keeper', 'cashier')
@require_GET
def sales_sheet_data(request):
    from sales.models import SaleItem, Sale

    profile = request.user.profile
    current_branch = getattr(request, 'current_branch', None)
    if not current_branch:
        return JsonResponse({'error': 'No branch selected'}, status=400)
    date_str = request.GET.get('date', datetime.date.today().isoformat())
    cat_filter = request.GET.get('category', '')
    sheets = SalesSheet.objects.filter(date=date_str, branch=current_branch).select_related('item', 'category')
    sheets = profile.filter_products(sheets)
    if cat_filter:
        sheets = sheets.filter(category__name=cat_filter)

    is_cashier = profile.role == 'cashier'
    parsed_date = datetime.date.fromisoformat(date_str) if isinstance(date_str, str) else date_str

    pos_sales_map = {}
    if is_cashier:
        pos_items = SaleItem.objects.filter(
            sale__branch=current_branch,
            sale__created_at__date=parsed_date,
            sale__status='completed',
        ).values('product_id').annotate(total_qty=Sum('quantity'))
        for item in pos_items:
            pos_sales_map[item['product_id']] = item['total_qty']

    data = []
    for s in sheets:
        sold_val = pos_sales_map.get(s.item_id, s.sold_stock) if is_cashier else s.sold_stock
        data.append({
            'id': s.id,
            'item_id': s.item.id if s.item else None,
            'item_name': s.item.name if s.item else '',
            'category': s.category.name if s.category else '',
            'open_stock': s.open_stock,
            'add_stock': s.add_stock,
            'total_stock': s.total_stock,
            'selling_price': float(s.selling_price),
            'sold_stock': sold_val,
            'remaining_stock': s.total_stock - sold_val,
            'amount': float(sold_val * float(s.selling_price)),
        })

    return JsonResponse({'data': data})


@login_required
@role_required('super_admin', 'manager', 'store_keeper')
@require_GET
def api_products_by_category(request):
    cat_name = request.GET.get('category', '')
    products = Product.objects.filter(is_active=True, category__name=cat_name).values('id', 'name', 'selling_price')
    return JsonResponse(list(products), safe=False)
