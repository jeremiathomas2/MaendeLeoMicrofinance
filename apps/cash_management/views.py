from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404

from apps.accounts.services import filter_by_scope, get_primary_branch
from apps.cash_management.models import BankAccount, CashTransaction, TellerSession
from apps.cash_management import services as cash_services
from apps.cash_management.forms import CloseSessionForm, OpenSessionForm


@login_required
def cash_page(request):
    sessions = filter_by_scope(request.user, TellerSession.objects.select_related('teller', 'branch'), 'branch')
    transactions = filter_by_scope(request.user, CashTransaction.objects.select_related('branch', 'teller'), 'branch')
    banks = filter_by_scope(request.user, BankAccount.objects.all(), 'branch')

    for s in sessions:
        s.recompute_expected()

    context = {
        'sessions': sessions[:50],
        'transactions': transactions[:100],
        'banks': banks,
        'open_form': OpenSessionForm(),
        'close_form': CloseSessionForm(),
        'my_session': sessions.filter(teller=request.user, status__in=['OPEN', 'RECONCILING']).first(),
        'primary_branch': get_primary_branch(request.user),
    }
    return render(request, 'pages/cash.html', context)


@login_required
def session_open(request):
    if request.method == 'POST':
        form = OpenSessionForm(request.POST)
        if form.is_valid():
            branch = form.cleaned_data.get('branch') or get_primary_branch(request.user)
            try:
                cash_services.open_session(request.user, branch, form.cleaned_data['opening_balance'])
                messages.success(request, 'Teller session opened.')
            except ValueError as e:
                messages.error(request, str(e))
        else:
            messages.error(request, 'Opening balance is required.')
    return redirect('cash_page')


@login_required
def session_reconcile(request, pk):
    session = get_object_or_404(TellerSession, pk=pk)
    actual = request.POST.get('actual_closing')
    reason = request.POST.get('variance_reason', '')
    if not actual:
        messages.error(request, 'Actual closing cash is required.')
        return redirect('cash_page')
    try:
        cash_services.reconcile_session(session, request.user, actual, reason)
        messages.success(request, 'Session reconciled and submitted for closure.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('cash_page')


@login_required
def session_close(request, pk):
    session = get_object_or_404(TellerSession, pk=pk)
    actual = request.POST.get('actual_closing')
    reason = request.POST.get('variance_reason', '')
    try:
        cash_services.close_session(session, request.user, actual, reason)
        messages.success(request, 'Teller session closed.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('cash_page')
