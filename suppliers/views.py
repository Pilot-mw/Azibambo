import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum
from django.core.paginator import Paginator
from .models import Supplier, Purchase
from .forms import SupplierForm, PurchaseForm
from inventory.models import Product
from expenses.models import Expense, ExpenseCategory
from accounts.decorators import role_required
from accounts.models import ActivityLog


def _get_branch_filter(request):
    branch = getattr(request, 'current_branch', None)
    if branch:
        return {'branch': branch}, branch
    return {}, None


@login_required
@role_required('super_admin', 'manager', 'store_keeper')
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
@role_required('super_admin', 'manager', 'store_keeper')
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
@role_required('super_admin', 'manager', 'store_keeper')
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
@role_required('super_admin', 'manager', 'store_keeper')
def supplier_detail(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    purchases = Purchase.objects.filter(supplier=supplier).select_related('product')
    return render(request, 'suppliers/supplier_detail.html', {
        'supplier': supplier, 'purchases': purchases
    })


@login_required
@role_required('super_admin', 'manager', 'store_keeper')
def purchase_list(request):
    branch_filter, _ = _get_branch_filter(request)
    purchases = Purchase.objects.select_related('supplier', 'product', 'purchased_by').filter(**branch_filter)
    paginator = Paginator(purchases, 20)
    page = request.GET.get('page')
    purchases = paginator.get_page(page)
    return render(request, 'suppliers/purchase_list.html', {'purchases': purchases})


@login_required
@role_required('super_admin', 'manager', 'store_keeper')
def purchase_add(request):
    if request.method == 'POST':
        form = PurchaseForm(request.POST)
        if form.is_valid():
            purchase = form.save(commit=False)
            purchase.purchased_by = request.user
            purchase.branch = getattr(request, 'current_branch', None)

            # Auto-calculate finance fields
            product = purchase.product
            purchase.total_amount = purchase.unit_price * purchase.quantity
            purchase.remaining_amount = purchase.total_amount - purchase.paid_amount

            if purchase.remaining_amount <= 0:
                purchase.payment_status = 'paid'
            elif purchase.paid_amount == 0:
                purchase.payment_status = 'unpaid'
            else:
                purchase.payment_status = 'partial'

            # Convert warehouse qty to base stock
            purchase.converted_quantity = product.convert_purchase_to_base(purchase.quantity)
            purchase.save()

            # Update product stock & buying price
            product.bottle_quantity += purchase.converted_quantity
            product.buying_price = purchase.unit_price
            product.save()

            # Sync to warehouse StockSheet
            today = purchase.date
            from inventory.models import StockSheet
            from branches.models import Branch
            warehouse = Branch.objects.filter(branch_type='Warehouse', is_active=True).first()
            if warehouse:
                prev = StockSheet.objects.filter(
                    item=product, date=today - datetime.timedelta(days=1), branch=warehouse
                ).first()
                prev_remain = prev.remaining_stock if prev else product.bottle_quantity - purchase.converted_quantity
                StockSheet.objects.update_or_create(
                    item=product,
                    date=today,
                    branch=warehouse,
                    defaults={
                        'category': product.category,
                        'open_stock': prev_remain if prev_remain >= 0 else 0,
                        'order_stock': purchase.converted_quantity,
                        'buying_price': purchase.unit_price,
                        'selling_price': product.selling_price,
                        'created_by': request.user,
                    }
                )

            # Create Expense/Loan record if remaining > 0
            if purchase.remaining_amount > 0:
                loan_cat, _ = ExpenseCategory.objects.get_or_create(name='Supplier Loan')
                expense = Expense.objects.create(
                    category=loan_cat,
                    title=f'Supplier Loan — {purchase.supplier.name} ({purchase.product.name})',
                    description=f'Auto-generated loan from purchase #{purchase.id} — {purchase.warehouse_display} = {purchase.selling_display}',
                    amount=purchase.remaining_amount,
                    paid_by=request.user,
                    branch=warehouse or purchase.branch,
                    purchase=purchase,
                    is_paid=False,
                    payment_status='unpaid',
                    date=today,
                )
                purchase.linked_expense = expense
                purchase.save(update_fields=['linked_expense'])

            # Update supplier outstanding balance
            supplier = purchase.supplier
            if supplier:
                supplier.outstanding_balance += purchase.remaining_amount
                supplier.save()

            messages.success(
                request,
                f'Purchase recorded! {purchase.warehouse_display} → {purchase.selling_display} | '
                f'Status: {purchase.get_payment_status_display()} | '
                f'Remaining: MK {purchase.remaining_amount:,.0f}'
            )
            return redirect('suppliers:purchase_list')
    else:
        form = PurchaseForm()
    products = Product.objects.filter(is_active=True).select_related('category')
    return render(request, 'suppliers/purchase_form.html', {
        'form': form,
        'title': 'Record Purchase',
        'products': products,
    })
