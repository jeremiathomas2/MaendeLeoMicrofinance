from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages

from apps.accounts.services import filter_by_scope
from apps.customers.models import Customer
from apps.savings.forms import DepositForm, SavingsOpenForm, WithdrawalForm
from apps.savings.models import SavingsAccount, SavingsProduct, SavingsTransaction
from apps.savings import services as savings_services


@login_required
def savings_page(request):
    products = SavingsProduct.objects.filter(is_active=True)
    accounts = filter_by_scope(request.user, SavingsAccount.objects.select_related(
        'customer', 'product', 'branch'), 'branch')
    transactions = filter_by_scope(request.user, SavingsTransaction.objects.select_related(
        'account', 'branch'), 'branch').order_by('-transaction_date', '-id')[:100]

    open_form = SavingsOpenForm()
    preselected_customer = None
    customer_pk = request.GET.get('customer')
    if customer_pk:
        preselected_customer = filter_by_scope(
            request.user,
            Customer.objects.filter(status='ACTIVE', pk=customer_pk),
            'branch',
        ).first()
        if preselected_customer:
            open_form = SavingsOpenForm(initial={'customer': preselected_customer})

    context = {
        'products': products,
        'accounts': accounts[:100],
        'transactions': transactions,
        'open_form': open_form,
        'deposit_form': DepositForm(),
        'withdrawal_form': WithdrawalForm(),
        'preselected_customer': preselected_customer,
        'can_operate': request.user.is_superuser or request.user.groups.filter(name__in=['Teller', 'Branch Manager', 'General Manager', 'Head of Operations']).exists(),
    }
    return render(request, 'pages/savings.html', context)


@login_required
def savings_open(request):
    if request.method == 'POST':
        form = SavingsOpenForm(request.POST)
        if form.is_valid():
            customer = form.cleaned_data['customer']
            product = form.cleaned_data['product']
            opening_deposit = form.cleaned_data.get('opening_deposit')
            try:
                savings_services.open_account(customer, product, request.user,
                                              branch=customer.branch,
                                              opening_deposit=opening_deposit)
                messages.success(request, 'Savings account opened.')
            except ValueError as e:
                messages.error(request, str(e))
            except Exception:
                messages.error(request, 'Could not open account. Check branch scope.')
        else:
            messages.error(request, 'Please correct the form errors.')
    return redirect('savings_page')


@login_required
def savings_deposit(request):
    if request.method == 'POST':
        form = DepositForm(request.POST)
        if form.is_valid():
            account = form.cleaned_data['account']
            try:
                savings_services.deposit(account, request.user, form.cleaned_data['amount'],
                                         description=form.cleaned_data.get('description', ''))
                messages.success(request, 'Deposit recorded.')
            except ValueError as e:
                messages.error(request, str(e))
    return redirect('savings_page')


@login_required
def savings_withdraw(request):
    if request.method == 'POST':
        form = WithdrawalForm(request.POST)
        if form.is_valid():
            account = form.cleaned_data['account']
            try:
                savings_services.withdraw(account, request.user, form.cleaned_data['amount'],
                                          description=form.cleaned_data.get('description', ''))
                messages.success(request, 'Withdrawal recorded.')
            except ValueError as e:
                messages.error(request, str(e))
    return redirect('savings_page')
