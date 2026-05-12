from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import timedelta
from .models import Expense, ExpenseCategory
from .forms import ExpenseForm, ExpenseCategoryForm
from accounts.decorators import role_required
from accounts.models import ActivityLog


def _get_branch_filter(request):
    branch = getattr(request, 'current_branch', None)
    if branch:
        return {'branch': branch}, branch
    return {}, None


@login_required
@role_required('super_admin', 'manager')
def expense_list(request):
    query = request.GET.get('q', '')
    category_id = request.GET.get('category', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    branch_filter, current_branch = _get_branch_filter(request)

    expenses = Expense.objects.select_related('category', 'paid_by').filter(**branch_filter)

    if query:
        expenses = expenses.filter(Q(title__icontains=query) | Q(description__icontains=query))
    if category_id:
        expenses = expenses.filter(category_id=category_id)
    if date_from:
        expenses = expenses.filter(date__gte=date_from)
    if date_to:
        expenses = expenses.filter(date__lte=date_to)

    paginator = Paginator(expenses, 20)
    page = request.GET.get('page')
    expenses = paginator.get_page(page)

    total_amount = expenses.object_list.aggregate(total=Sum('amount'))['total'] or 0
    categories = ExpenseCategory.objects.all()

    context = {
        'expenses': expenses,
        'categories': categories,
        'total_amount': total_amount,
        'query': query,
        'selected_category': category_id,
        'current_branch': current_branch,
    }
    return render(request, 'expenses/expense_list.html', context)


@login_required
@role_required('super_admin', 'manager')
def expense_add(request):
    if request.method == 'POST':
        form = ExpenseForm(request.POST, request.FILES)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.paid_by = request.user
            expense.branch = getattr(request, 'current_branch', None)
            expense.save()
            ActivityLog.objects.create(
                user=request.user,
                action=f'Added expense: {expense.title}',
                model_name='Expense',
                object_id=expense.id,
                branch=getattr(request, 'current_branch', None),
                ip_address=request.META.get('REMOTE_ADDR')
            )
            messages.success(request, 'Expense added successfully!')
            return redirect('expenses:expense_list')
    else:
        form = ExpenseForm()
    return render(request, 'expenses/expense_form.html', {'form': form, 'title': 'Add Expense'})


@login_required
@role_required('super_admin', 'manager')
def expense_edit(request, pk):
    expense = get_object_or_404(Expense, pk=pk)
    if request.method == 'POST':
        form = ExpenseForm(request.POST, request.FILES, instance=expense)
        if form.is_valid():
            form.save()
            messages.success(request, 'Expense updated!')
            return redirect('expenses:expense_list')
    else:
        form = ExpenseForm(instance=expense)
    return render(request, 'expenses/expense_form.html', {'form': form, 'title': 'Edit Expense'})


@login_required
@role_required('super_admin', 'manager')
def expense_delete(request, pk):
    expense = get_object_or_404(Expense, pk=pk)
    if request.method == 'POST':
        expense.delete()
        messages.success(request, 'Expense deleted!')
        return redirect('expenses:expense_list')
    return render(request, 'expenses/expense_confirm_delete.html', {'expense': expense})


@login_required
@role_required('super_admin', 'manager')
def category_list(request):
    categories = ExpenseCategory.objects.all()
    return render(request, 'expenses/category_list.html', {'categories': categories})


@login_required
@role_required('super_admin', 'manager')
def category_add(request):
    if request.method == 'POST':
        form = ExpenseCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Expense category added!')
            return redirect('expenses:category_list')
    else:
        form = ExpenseCategoryForm()
    return render(request, 'expenses/category_form.html', {'form': form, 'title': 'Add Category'})


@login_required
@role_required('super_admin', 'manager')
def category_edit(request, pk):
    category = get_object_or_404(ExpenseCategory, pk=pk)
    if request.method == 'POST':
        form = ExpenseCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, 'Expense category updated!')
            return redirect('expenses:category_list')
    else:
        form = ExpenseCategoryForm(instance=category)
    return render(request, 'expenses/category_form.html', {'form': form, 'title': 'Edit Category'})


@login_required
@role_required('super_admin', 'manager')
def category_delete(request, pk):
    category = get_object_or_404(ExpenseCategory, pk=pk)
    if request.method == 'POST':
        category.delete()
        messages.success(request, 'Expense category deleted!')
        return redirect('expenses:category_list')
    return render(request, 'expenses/category_confirm_delete.html', {'category': category})
