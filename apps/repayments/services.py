"""Repayment service — the core financial transaction (SRS sections 27-31, 94)."""

from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from apps.repayments.models import Repayment, PaymentAllocationConfig
from apps.loans.models import Loan
from apps.audit.models import audit

ZERO = Decimal('0.00')
TWO = Decimal('0.01')


def _r(v):
    return v.quantize(TWO)


@transaction.atomic
def receive_repayment(loan, user, amount, payment_date=None, method='CASH',
                      teller=None, external_reference='', notes='', branch=None):
    """
    Receive a loan repayment in one atomic financial transaction.

    Steps: validate -> allocate -> update installments -> update loan ->
    post accounting -> update teller cash -> receipt -> audit -> notify.
    """
    from apps.common.numbering import next_number
    from apps.accounting.services import post_repayment_entries
    from apps.cash_management.models import CashTransaction
    from apps.loans.services import refresh_loan_status
    from apps.notifications.models import notify

    amount = Decimal(amount)
    if amount <= 0:
        raise ValueError('Payment amount must be positive')
    if loan.status in (Loan.STATUS_CLOSED, Loan.STATUS_WRITTEN_OFF):
        raise ValueError('Loan is closed or written off - cannot receive payment')

    loan = Loan.objects.select_for_update().get(pk=loan.pk)
    branch = branch or loan.branch
    payment_date = payment_date or timezone.now().date()

    # ---- compute penalties on overdue installments
    penalty_due = _penalty_due(loan)
    total_outstanding = loan.total_outstanding

    if amount > total_outstanding + penalty_due:
        excess = _r(amount - (total_outstanding + penalty_due))
    else:
        excess = ZERO

    alloc = {
        'penalty': ZERO, 'fees': ZERO, 'interest': ZERO, 'principal': ZERO,
    }
    remaining = amount - excess

    steps = PaymentAllocationConfig.objects.filter(is_active=True).first()
    order = steps.steps if steps else ['penalty', 'fees', 'interest', 'principal']

    # penalties are charged against the overdue penalty bucket on the loan
    if 'penalty' in order and penalty_due > 0:
        take = min(remaining, penalty_due)
        alloc['penalty'] = _r(take)
        remaining = _r(remaining - take)

    # allocate across installments, earliest first
    installments = list(loan.installments.filter(status__in=['PENDING', 'PARTIAL']).order_by('due_date'))

    for step in order:
        if step == 'penalty':
            continue
        if remaining <= 0:
            break
        for inst in installments:
            if remaining <= 0:
                break
            if step == 'fees':
                bucket_due = inst.fees_due - inst.fees_paid
            elif step == 'interest':
                bucket_due = inst.interest_due - inst.interest_paid
            else:  # principal
                bucket_due = inst.principal_due - inst.principal_paid
            if bucket_due <= 0:
                continue
            take = min(remaining, bucket_due)
            if step == 'fees':
                inst.fees_paid = _r(inst.fees_paid + take)
            elif step == 'interest':
                inst.interest_paid = _r(inst.interest_paid + take)
            else:
                inst.principal_paid = _r(inst.principal_paid + take)
            alloc[step] = _r(alloc[step] + take)
            remaining = _r(remaining - take)

    if remaining > 0 and amount - excess == remaining:
        # not enough buckets — anything left over is a genuine overpayment
        excess = _r(excess + remaining)
        remaining = ZERO

    # persist installment updates
    for inst in installments:
        inst.total_paid = _r(inst.principal_paid + inst.interest_paid + inst.fees_paid)
        inst.outstanding = _r(inst.total_due - inst.total_paid)
        if inst.total_paid >= inst.total_due:
            inst.status = 'PAID'
        elif inst.total_paid > 0:
            inst.status = 'PARTIAL'
        else:
            inst.status = 'PENDING'
        inst.save(update_fields=[
            'principal_paid', 'interest_paid', 'fees_paid', 'total_paid',
            'outstanding', 'status', 'updated_at',
        ])

    # ---- create the repayment record
    paid = amount - excess
    repayment = Repayment.objects.create(
        receipt_number=next_number('RCT', branch, include_year=True),
        loan=loan,
        customer=loan.customer,
        branch=branch,
        teller=teller or user,
        created_by=user,
        amount=paid,
        penalty_allocated=alloc['penalty'],
        fees_allocated=alloc['fees'],
        interest_allocated=alloc['interest'],
        principal_allocated=alloc['principal'],
        excess_amount=excess,
        payment_method=method,
        payment_date=payment_date,
        external_reference=external_reference,
        notes=notes,
    )

    # ---- update loan
    refresh_loan_status(loan)

    # ---- accounting
    if paid > 0:
        post_repayment_entries(repayment)

    # ---- cash / teller
    CashTransaction.objects.create(
        reference=next_number('TXN', branch, include_year=True),
        transaction_type=CashTransaction.TYPE_REPAYMENT,
        amount=paid,
        branch=branch,
        teller=teller,
        customer=loan.customer,
        loan=loan,
        repayment=repayment,
        transaction_date=payment_date,
        description=f'Repayment {repayment.receipt_number}',
    )

    audit(user, 'REPAYMENT_CREATED', repayment,
          new={'amount': str(paid), 'allocation': alloc, 'excess': str(excess)})
    notify(loan.loan_officer, f'Repayment received: {repayment.receipt_number}',
           f'{loan.customer.full_name} paid TZS {paid:,.0f} on {loan.loan_number}.',
           'SUCCESS', link='/loans/')
    return repayment


def _penalty_due(loan):
    """Compute outstanding penalty on overdue installments per configured rate."""
    from django.utils import timezone
    today = timezone.now().date()
    rate = Decimal(str(loan.penalty_rate or '0'))
    total = ZERO
    for inst in loan.installments.filter(status__in=['PENDING', 'PARTIAL']):
        if inst.due_date < today:
            days = (today - inst.due_date).days
            overdue = inst.total_due - inst.total_paid
            total += overdue * rate / Decimal('100') * days / Decimal('30')
    return _r(total)


@transaction.atomic
def reverse_repayment(repayment, user, reason=''):
    """Reverse a posted repayment: restore installment and loan balances.

    The original record is preserved (SRS section 57) — a reversal record is
    created and accounting entries restored.
    """
    from apps.accounting.models import JournalEntry
    from apps.accounting.services import coa
    from apps.loans.services import refresh_loan_status

    if repayment.reversed:
        raise ValueError('Repayment already reversed')
    if repayment.status == Repayment.STATUS_REVERSED:
        raise ValueError('Repayment already reversed')

    loan = Loan.objects.select_for_update().get(pk=repayment.loan_id)

    # restore installments
    remaining = repayment.amount
    buckets = {
        'principal_paid': repayment.principal_allocated,
        'interest_paid': repayment.interest_allocated,
        'fees_paid': repayment.fees_allocated,
    }
    installments = list(loan.installments.filter(status__in=['PENDING', 'PARTIAL', 'PAID']).order_by('-due_date'))
    for inst in installments:
        for field in ('principal_paid', 'interest_paid', 'fees_paid'):
            take = min(getattr(inst, field), buckets[field])
            setattr(inst, field, getattr(inst, field) - take)
            buckets[field] -= take
            remaining -= take
        inst.total_paid = _r(inst.principal_paid + inst.interest_paid + inst.fees_paid)
        inst.outstanding = _r(inst.total_due - inst.total_paid)
        if inst.outstanding > 0:
            inst.status = 'PARTIAL' if inst.total_paid > 0 else 'PENDING'
        inst.save()

    repayment.reversed = True
    repayment.status = Repayment.STATUS_REVERSED
    repayment.reversed_by = user
    repayment.reversed_at = timezone.now()
    repayment.reversal_reason = reason
    repayment.save(update_fields=['reversed', 'status', 'reversed_by', 'reversed_at', 'reversal_reason'])

    refresh_loan_status(loan)

    # reversing accounting entry
    accounts = coa()
    from apps.accounting.services import post_journal
    lines = [
        {'account': accounts['loan_portfolio'], 'debit': repayment.principal_allocated, 'credit': ZERO},
        {'account': accounts['interest_income'], 'debit': repayment.interest_allocated, 'credit': ZERO},
        {'account': accounts['fee_income'], 'debit': repayment.fees_allocated, 'credit': ZERO},
        {'account': accounts['penalty_income'], 'debit': repayment.penalty_allocated, 'credit': ZERO},
        {'account': accounts['cash'], 'credit': repayment.amount, 'debit': ZERO},
    ]
    post_journal(
        description=f'Reversal of {repayment.receipt_number}',
        lines=lines,
        branch=repayment.branch,
        user=user,
        source_type='Repayment Reversal',
        source_reference=repayment.receipt_number,
    )

    audit(user, 'REPAYMENT_REVERSED', repayment, reason=reason)
    return repayment
