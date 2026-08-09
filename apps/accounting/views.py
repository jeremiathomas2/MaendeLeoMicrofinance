from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils import timezone

from apps.accounts.services import filter_by_scope, get_primary_branch
from apps.accounting.models import Account, Expense, JournalEntry
from apps.accounting import services as accounting_services
from apps.accounting.forms import ExpenseForm, JournalForm
from apps.audit.models import audit
from apps.common.numbering import next_number


@login_required
def accounting_page(request):
    accounts = Account.objects.filter(is_active=True).order_by('code')
    journals = filter_by_scope(request.user, JournalEntry.objects.select_related('branch'), 'branch')
    expenses = filter_by_scope(request.user, Expense.objects.select_related('branch'), 'branch')
    tb = accounting_services.trial_balance()
    total_debit = sum(r['debit'] for r in tb)
    total_credit = sum(r['credit'] for r in tb)
    context = {
        'accounts': accounts,
        'journals': journals[:100],
        'expenses': expenses[:100],
        'trial_balance': tb,
        'total_debit': total_debit,
        'total_credit': total_credit,
        'balanced': total_debit == total_credit,
        'journal_form': JournalForm(),
        'expense_form': ExpenseForm(),
        'can_account': request.user.is_superuser or request.user.groups.filter(name__in=[
            'General Manager', 'Head of Operations', 'Accountant']).exists(),
    }
    return render(request, 'pages/accounting.html', context)


@login_required
def journal_create(request):
    if request.method == 'POST':
        form = JournalForm(request.POST)
        if form.is_valid():
            debit = form.cleaned_data['debit']
            credit = form.cleaned_data['credit']
            account = form.cleaned_data['account']
            description = form.cleaned_data['description']
            if debit == credit == 0:
                messages.error(request, 'Debit and credit cannot both be zero.')
                return redirect('accounting_page')
            if debit != credit:
                messages.error(request, 'Debit must equal credit (double-entry balance).')
                return redirect('accounting_page')
            branch = form.cleaned_data.get('branch') or get_primary_branch(request.user)
            try:
                entry = accounting_services.post_journal(
                    description, [
                        {'account': account, 'debit': debit, 'credit': 0},
                        {'account': form.cleaned_data['counter_account'], 'debit': 0, 'credit': credit},
                    ],
                    branch=branch, user=request.user,
                    source_type='Manual Journal',
                )
                audit(request.user, 'JOURNAL_POSTED', entry, branch=branch, request=request)
                messages.success(request, f'Journal {entry.reference} posted.')
            except ValueError as e:
                messages.error(request, str(e))
        else:
            messages.error(request, 'Please correct the journal form.')
    return redirect('accounting_page')


@login_required
def expense_create(request):
    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        if form.is_valid():
            branch = form.cleaned_data.get('branch') or get_primary_branch(request.user)
            expense = form.save(commit=False)
            expense.reference = next_number('EXP', branch, include_year=True)
            expense.branch = branch
            expense.requested_by = request.user
            expense.approval_status = Expense.STATUS_PENDING
            expense.save()
            audit(request.user, 'EXPENSE_CREATED', expense, branch=branch, request=request)
            messages.success(request, 'Expense submitted for approval.')
        else:
            messages.error(request, 'Please correct the expense form.')
    return redirect('accounting_page')


@login_required
def expense_approve(request, pk):
    from django.shortcuts import get_object_or_404
    expense = get_object_or_404(Expense, pk=pk)
    action = request.POST.get('action')
    if action == 'approve':
        expense.approval_status = Expense.STATUS_APPROVED
        expense.approved_by = request.user
        expense.approved_at = timezone.now()
        expense.save()
        accounting_services.post_expense_entries(expense)
        audit(request.user, 'EXPENSE_CREATED', expense, branch=expense.branch,
              new={'status': 'APPROVED'}, request=request)
        messages.success(request, 'Expense approved and posted to ledger.')
    elif action == 'pay':
        expense.approval_status = Expense.STATUS_PAID
        expense.paid = True
        expense.save()
        messages.success(request, 'Expense marked as paid.')
    elif action == 'reject':
        expense.approval_status = Expense.STATUS_REJECTED
        expense.save()
        messages.success(request, 'Expense rejected.')
    return redirect('accounting_page')


@login_required
def statements(request, statement):
    from django.utils.dateparse import parse_date
    start = request.GET.get('start') or f'{timezone.now().year}-01-01'
    end = request.GET.get('end') or timezone.now().date().isoformat()
    start_date = parse_date(start)
    end_date = parse_date(end)

    if statement == 'income':
        data = accounting_services.income_statement(start_date, end_date)
        template = 'pages/statement_income.html'
    elif statement == 'balance':
        data = accounting_services.balance_sheet(as_of=end_date)
        template = 'pages/statement_balance.html'
    elif statement == 'cashflow':
        data = accounting_services.cash_flow(start_date, end_date)
        template = 'pages/statement_cashflow.html'
    else:
        return redirect('accounting_page')
    return render(request, template, {'data': data, 'start': start_date, 'end': end_date})
