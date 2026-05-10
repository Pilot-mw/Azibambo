import json, datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, F, Count
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from .models import Product, Category, StockSheet
from .forms import ProductForm, CategoryForm, StockSheetForm
from accounts.models import ActivityLog

@login_required
def product_list(request):
    query = request.GET.get('q', '')
    category_id = request.GET.get('category', '')
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
    }
    return render(request, 'inventory/product_list.html', context)

@login_required
def product_add(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            ActivityLog.objects.create(
                user=request.user,
                action=f'Added product {product.name}',
                model_name='Product',
                object_id=product.id,
                ip_address=request.META.get('REMOTE_ADDR')
            )
            messages.success(request, f'Product "{product.name}" added successfully!')
            return redirect('inventory:product_list')
    else:
        form = ProductForm()
    return render(request, 'inventory/product_form.html', {'form': form, 'title': 'Add Product'})

@login_required
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
                ip_address=request.META.get('REMOTE_ADDR')
            )
            messages.success(request, f'Product "{product.name}" updated successfully!')
            return redirect('inventory:product_list')
    else:
        form = ProductForm(instance=product)
    return render(request, 'inventory/product_form.html', {'form': form, 'title': 'Edit Product'})

@login_required
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
            ip_address=request.META.get('REMOTE_ADDR')
        )
        messages.success(request, f'Product "{name}" deleted successfully!')
        return redirect('inventory:product_list')
    return render(request, 'inventory/product_confirm_delete.html', {'product': product})

@login_required
def category_list(request):
    categories = Category.objects.all().annotate(product_count=Count('products'))
    return render(request, 'inventory/category_list.html', {'categories': categories})

@login_required
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
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        category.delete()
        messages.success(request, 'Category deleted!')
        return redirect('inventory:category_list')
    return render(request, 'inventory/category_confirm_delete.html', {'category': category})


@login_required
def stock_sheet(request):
    today = datetime.date.today()
    categories = Category.objects.filter(name__in=['Beers & Softs', 'Ciders & Wines', 'Spirits & Others'])
    selected_date = request.GET.get('date', today.isoformat())
    cat_filter = request.GET.get('category', '')
    parsed_date = datetime.date.fromisoformat(selected_date) if isinstance(selected_date, str) else selected_date
    prev_date = parsed_date - datetime.timedelta(days=1)

    cat_ids = categories.values_list('id', flat=True)
    products = Product.objects.filter(is_active=True, category_id__in=cat_ids).select_related('category')
    if cat_filter:
        products = products.filter(category__name=cat_filter)

    existing_sheets = {
        s.item_id: s
        for s in StockSheet.objects.filter(date=selected_date, item_id__in=products.values('id'))
    }

    prev_sheets = {
        s.item_id: s
        for s in StockSheet.objects.filter(date=prev_date.isoformat(), item_id__in=products.values('id'))
    }

    rows = []
    total_sold = 0
    total_remaining = 0
    total_revenue = 0

    for product in products:
        sheet = existing_sheets.get(product.id)
        if sheet:
            rows.append(sheet)
            total_sold += sheet.sold_stock
            total_remaining += sheet.remaining_stock
            total_revenue += float(sheet.total_amount)
        else:
            prev_sheet = prev_sheets.get(product.id)
            open_stock = prev_sheet.remaining_stock if prev_sheet else product.quantity
            rows.append({
                'id': None,
                'item': product,
                'category': product.category,
                'open_stock': open_stock,
                'order_stock': 0,
                'total_stock': open_stock,
                'selling_price': product.selling_price,
                'sold_stock': 0,
                'remaining_stock': open_stock,
                'total_amount': 0,
                'date': parsed_date,
            })
            total_remaining += open_stock

    import json as json_lib
    cats_json = json_lib.dumps([{'name': c.name} for c in categories])

    return render(request, 'inventory/stock_sheet.html', {
        'rows': rows,
        'categories': categories,
        'categories_json': cats_json,
        'selected_date': selected_date,
        'selected_category': cat_filter,
        'total_sold': total_sold,
        'total_remaining': total_remaining,
        'total_revenue': total_revenue,
    })


@login_required
@require_POST
def stock_sheet_save(request):
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        order_stock = int(data.get('order_stock', 0))
        sold_stock = int(data.get('sold_stock', 0))
        sheet_date = data.get('date', datetime.date.today().isoformat())

        item = get_object_or_404(Product, pk=item_id) if item_id else None
        if not item:
            return JsonResponse({'success': False, 'error': 'Item required'}, status=400)

        sheet, created = StockSheet.objects.get_or_create(
            item=item,
            date=sheet_date,
            defaults={
                'category': item.category,
                'open_stock': item.quantity,
                'selling_price': item.selling_price,
                'created_by': request.user,
            }
        )

        sheet.order_stock = order_stock
        sheet.sold_stock = sold_stock
        sheet.selling_price = item.selling_price
        sheet.save()

        return JsonResponse({
            'success': True,
            'id': sheet.id,
            'total_stock': sheet.total_stock,
            'remaining_stock': sheet.remaining_stock,
            'total_amount': float(sheet.total_amount),
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
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
def stock_sheet_data(request):
    date_str = request.GET.get('date', datetime.date.today().isoformat())
    cat_filter = request.GET.get('category', '')
    sheets = StockSheet.objects.filter(date=date_str).select_related('item', 'category')
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
            'selling_price': float(s.selling_price),
            'sold_stock': s.sold_stock,
            'remaining_stock': s.remaining_stock,
            'total_amount': float(s.total_amount),
        })

    return JsonResponse({'data': data})


@login_required
@require_GET
def api_products_by_category(request):
    cat_name = request.GET.get('category', '')
    products = Product.objects.filter(is_active=True, category__name=cat_name).values('id', 'name', 'selling_price')
    return JsonResponse(list(products), safe=False)
