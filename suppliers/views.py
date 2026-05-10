from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum
from django.core.paginator import Paginator
from .models import Supplier, Purchase
from .forms import SupplierForm, PurchaseForm
from accounts.models import ActivityLog

@login_required
def supplier_list(request):
    query = request.GET.get('q', '')
    suppliers = Supplier.objects.filter(is_active=True)

    if query:
        suppliers = suppliers.filter(
            Q(name__icontains=query) | Q(phone__icontains=query) | Q(email__icontains=query)
        )

    paginator = Paginator(suppliers, 20)
    page = request.GET.get('page')
    suppliers = paginator.get_page(page)
    return render(request, 'suppliers/supplier_list.html', {'suppliers': suppliers})

@login_required
def supplier_add(request):
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            supplier = form.save()
            ActivityLog.objects.create(
                user=request.user, action=f'Added supplier {supplier.name}',
                model_name='Supplier', object_id=supplier.id,
                ip_address=request.META.get('REMOTE_ADDR')
            )
            messages.success(request, f'Supplier "{supplier.name}" added!')
            return redirect('suppliers:supplier_list')
    else:
        form = SupplierForm()
    return render(request, 'suppliers/supplier_form.html', {'form': form, 'title': 'Add Supplier'})

@login_required
def supplier_edit(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            form.save()
            messages.success(request, 'Supplier updated!')
            return redirect('suppliers:supplier_list')
    else:
        form = SupplierForm(instance=supplier)
    return render(request, 'suppliers/supplier_form.html', {'form': form, 'title': 'Edit Supplier'})

@login_required
def supplier_detail(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    purchases = Purchase.objects.filter(supplier=supplier).select_related('product')
    return render(request, 'suppliers/supplier_detail.html', {
        'supplier': supplier, 'purchases': purchases
    })

@login_required
def purchase_list(request):
    purchases = Purchase.objects.select_related('supplier', 'product', 'purchased_by')
    paginator = Paginator(purchases, 20)
    page = request.GET.get('page')
    purchases = paginator.get_page(page)
    return render(request, 'suppliers/purchase_list.html', {'purchases': purchases})

@login_required
def purchase_add(request):
    if request.method == 'POST':
        form = PurchaseForm(request.POST)
        if form.is_valid():
            purchase = form.save(commit=False)
            purchase.purchased_by = request.user
            purchase.save()

            product = purchase.product
            product.quantity += purchase.quantity
            product.buying_price = purchase.unit_price
            product.save()

            supplier = purchase.supplier
            if supplier:
                supplier.outstanding_balance += purchase.balance
                supplier.save()

            messages.success(request, 'Purchase recorded!')
            return redirect('suppliers:purchase_list')
    else:
        form = PurchaseForm()
    return render(request, 'suppliers/purchase_form.html', {'form': form, 'title': 'Record Purchase'})
