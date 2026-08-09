"""Double-entry accounting engine (SRS sections 41-44, 109)."""

from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from apps.accounting.models import Account, JournalEntry, JournalEntryLine

ZERO = Decimal('0.00')


def get_or_create_account(code, name, account_type, parent=None):
    return Account.objects.get_or_create(
        code=code,
        defaults={'name': name, 'account_type': account_type, 'parent': parent},
    )[0]


def coa():
    """Standard chart of accounts seeded from the SRS."""
    a = {
        'cash': get_or_create_account('1100', 'Cash', Account.TYPE_ASSET),
        'bank': get_or_create_account('1200', 'Bank', Account.TYPE_ASSET),
        'loan_portfolio': get_or_create_account('1300', 'Loan Portfolio', Account.TYPE_ASSET),
        'savings_deposits': get_or_create_account('2100', 'Customer Deposits', Account.TYPE_LIABILITY),
        'interest_income': get_or_create_account('4100', 'Interest Income', Account.TYPE_INCOME),
        'fee_income': get_or_create_account('4200', 'Fee Income', Account.TYPE_INCOME),
        'penalty_income': get_or_create_account('4300', 'Penalty Income', Account.TYPE_INCOME),
        'other_income': get_or_create_account('4400', 'Other Income', Account.TYPE_INCOME),
        'salaries': get_or_create_account('5100', 'Salaries', Account.TYPE_EXPENSE),
        'rent': get_or_create_account('5200', 'Rent', Account.TYPE_EXPENSE),
        'utilities': get_or_create_account('5300', 'Utilities', Account.TYPE_EXPENSE),
        'admin_expense': get_or_create_account('5900', 'Administrative Expense', Account.TYPE_EXPENSE),
        'equity': get_or_create_account('3000', 'Retained Earnings', Account.TYPE_EQUITY),
    }
    return a


@transaction.atomic
def post_journal(description, lines, branch=None, user=None, entry_date=None,
                 source_type='', source_reference='', approve=True):
    """
    Create and post a balanced journal entry.

    ``lines`` is a list of dicts: {"account": Account, "debit": Decimal, "credit": Decimal}.
    Raises ``ValueError`` when debits != credits.
    """
    from apps.common.numbering import next_number

    if not lines:
        raise ValueError('Journal entry requires at least one line')

    total_debit = sum((l.get('debit') or ZERO) for l in lines)
    total_credit = sum((l.get('credit') or ZERO) for l in lines)
    if total_debit != total_credit:
        raise ValueError(f'Journal entry not balanced: debits {total_debit} != credits {total_credit}')

    for l in lines:
        account = l.get('account')
        if account is None:
            raise ValueError('Every journal line needs an account')

    reference = next_number('JRN', include_year=True)
    entry = JournalEntry.objects.create(
        reference=reference,
        entry_date=entry_date or timezone.now().date(),
        description=description,
        branch=branch,
        source_type=source_type,
        source_reference=source_reference,
        status=JournalEntry.STATUS_POSTED,
        posted_by=user,
        posted_at=timezone.now(),
        created_by=user,
    )
    for l in lines:
        JournalEntryLine.objects.create(
            entry=entry,
            account=l['account'],
            debit=l.get('debit') or ZERO,
            credit=l.get('credit') or ZERO,
            memo=l.get('memo', ''),
        )
    return entry


def post_repayment_entries(repayment):
    """Post accounting for a loan repayment (SRS section 41 example)."""
    from apps.accounting.services import coa
    from apps.accounting.models import Account

    accounts = coa()
    lines = [
        {'account': accounts['cash'], 'debit': repayment.amount, 'credit': ZERO},
    ]
    if repayment.principal_allocated:
        lines.append({'account': accounts['loan_portfolio'], 'credit': repayment.principal_allocated, 'debit': ZERO})
    if repayment.interest_allocated:
        lines.append({'account': accounts['interest_income'], 'credit': repayment.interest_allocated, 'debit': ZERO})
    if repayment.fees_allocated:
        lines.append({'account': accounts['fee_income'], 'credit': repayment.fees_allocated, 'debit': ZERO})
    if repayment.penalty_allocated:
        lines.append({'account': accounts['penalty_income'], 'credit': repayment.penalty_allocated, 'debit': ZERO})

    return post_journal(
        description=f'Loan repayment {repayment.receipt_number}',
        lines=lines,
        branch=repayment.branch,
        user=repayment.teller or repayment.created_by,
        source_type='Repayment',
        source_reference=repayment.receipt_number,
    )


def post_disbursement_entries(loan, method):
    """Post accounting for a loan disbursement.

    Debit Loan Portfolio, credit Cash/Bank. Also books processing & insurance
    fee income when applicable.
    """
    accounts = coa()
    lines = [
        {'account': accounts['loan_portfolio'], 'debit': loan.principal, 'credit': ZERO},
    ]
    credit_account = accounts['cash'] if method == 'CASH' else accounts['bank']
    lines.append({'account': credit_account, 'credit': loan.principal, 'debit': ZERO})
    if loan.processing_fee:
        lines.append({'account': accounts['fee_income'], 'credit': loan.processing_fee, 'debit': ZERO})
        lines.append({'account': credit_account, 'debit': loan.processing_fee, 'credit': ZERO})
    if loan.insurance_fee:
        lines.append({'account': accounts['admin_expense'], 'debit': loan.insurance_fee, 'credit': ZERO})
        lines.append({'account': credit_account, 'credit': loan.insurance_fee, 'debit': ZERO})

    return post_journal(
        description=f'Loan disbursement {loan.loan_number}',
        lines=lines,
        branch=loan.branch,
        user=loan.disbursed_by,
        source_type='Disbursement',
        source_reference=loan.loan_number,
    )


def post_deposit_entries(transaction):
    from apps.accounting.services import coa
    accounts = coa()
    return post_journal(
        description=f'Savings deposit {transaction.reference}',
        lines=[
            {'account': accounts['cash'], 'debit': transaction.amount, 'credit': ZERO},
            {'account': accounts['savings_deposits'], 'credit': transaction.amount, 'debit': ZERO},
        ],
        branch=transaction.branch,
        user=transaction.created_by,
        source_type='Savings Deposit',
        source_reference=transaction.reference,
    )


def post_withdrawal_entries(transaction):
    from apps.accounting.services import coa
    accounts = coa()
    return post_journal(
        description=f'Savings withdrawal {transaction.reference}',
        lines=[
            {'account': accounts['cash'], 'credit': transaction.amount, 'debit': ZERO},
            {'account': accounts['savings_deposits'], 'debit': transaction.amount, 'credit': ZERO},
        ],
        branch=transaction.branch,
        user=transaction.created_by,
        source_type='Savings Withdrawal',
        source_reference=transaction.reference,
    )


def post_expense_entries(expense):
    from apps.accounting.services import coa
    accounts = coa()
    return post_journal(
        description=f'Expense {expense.reference} - {expense.category}',
        lines=[
            {'account': accounts['admin_expense'], 'debit': expense.amount, 'credit': ZERO},
            {'account': accounts['cash'], 'credit': expense.amount, 'debit': ZERO},
        ],
        branch=expense.branch,
        user=expense.requested_by,
        source_type='Expense',
        source_reference=expense.reference,
    )


def trial_balance():
    """Return list of {account, debit_total, credit_total, balance}."""
    from django.db.models import Sum
    lines = JournalEntryLine.objects.filter(entry__status=JournalEntry.STATUS_POSTED)
    rows = []
    for account in Account.objects.filter(is_active=True):
        agg = lines.filter(account=account).aggregate(d=Sum('debit'), c=Sum('credit'))
        debit = agg['d'] or ZERO
        credit = agg['c'] or ZERO
        rows.append({
            'account': account,
            'debit': debit,
            'credit': credit,
            'balance': debit - credit,
        })
    return rows


def account_balance(account, as_of=None):
    from django.db.models import Sum
    lines = account.lines.filter(entry__status=JournalEntry.STATUS_POSTED)
    if as_of:
        lines = lines.filter(entry__entry_date__lte=as_of)
    debit = lines.aggregate(d=Sum('debit'))['d'] or ZERO
    credit = lines.aggregate(c=Sum('credit'))['c'] or ZERO
    if account.account_type in (Account.TYPE_ASSET, Account.TYPE_EXPENSE):
        return debit - credit
    return credit - debit


def income_statement(start_date, end_date):
    """Return income and expense line totals for a period."""
    from django.db.models import Sum
    lines = JournalEntryLine.objects.filter(
        entry__status=JournalEntry.STATUS_POSTED,
        entry__entry_date__gte=start_date,
        entry__entry_date__lte=end_date,
    )
    income = []
    expense = []
    for account in Account.objects.filter(account_type__in=[Account.TYPE_INCOME, Account.TYPE_EXPENSE], is_active=True):
        agg = lines.filter(account=account).aggregate(d=Sum('debit'), c=Sum('credit'))
        debit = agg['d'] or ZERO
        credit = agg['c'] or ZERO
        net = credit - debit
        if account.account_type == Account.TYPE_INCOME:
            income.append({'account': account, 'amount': net})
        else:
            expense.append({'account': account, 'amount': -net})
    total_income = sum(i['amount'] for i in income)
    total_expense = sum(e['amount'] for e in expense)
    return {
        'income': income,
        'expense': expense,
        'total_income': total_income,
        'total_expense': total_expense,
        'net_income': total_income - total_expense,
    }


def cash_flow(start_date, end_date):
    """Simple cash-flow statement: cash in/out by category for a period."""
    from django.db.models import Sum
    from apps.accounting.models import JournalEntryLine

    lines = JournalEntryLine.objects.filter(
        entry__status=JournalEntry.STATUS_POSTED,
        entry__entry_date__gte=start_date,
        entry__entry_date__lte=end_date,
    )
    cash = Account.objects.filter(code='1100').first()
    inflow = lines.filter(account=cash).aggregate(s=Sum('debit'))['s'] or ZERO
    outflow = lines.filter(account=cash).aggregate(s=Sum('credit'))['s'] or ZERO
    return {
        'inflow': inflow,
        'outflow': outflow,
        'net': inflow - outflow,
    }


def balance_sheet(as_of=None):
    """Return assets, liabilities, equity totals."""
    assets, liabilities, equity = ZERO, ZERO, ZERO
    rows = {'assets': [], 'liabilities': [], 'equity': []}
    for account in Account.objects.filter(is_active=True).order_by('code'):
        balance = account_balance(account, as_of)
        if balance == 0:
            continue
        if account.account_type == Account.TYPE_ASSET:
            assets += balance
            rows['assets'].append((account, balance))
        elif account.account_type == Account.TYPE_LIABILITY:
            liabilities += balance
            rows['liabilities'].append((account, balance))
        elif account.account_type == Account.TYPE_EQUITY:
            equity += balance
            rows['equity'].append((account, balance))
    return {
        'assets': assets,
        'liabilities': liabilities,
        'equity': equity,
        'rows': rows,
        'balanced': assets == liabilities + equity,
    }
