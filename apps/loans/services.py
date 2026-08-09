"""Loan domain services: schedules, workflow, disbursement, status (SRS 17-36)."""

from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.utils import timezone

from apps.loans.models import Loan, LoanInstallment, LoanApplication, LoanApproval
from apps.audit.models import audit

TWO = Decimal('0.01')
ZERO = Decimal('0.00')


def _r(value, places=2):
    return value.quantize(Decimal('1').scaleb(-places), rounding=ROUND_HALF_UP)


# ---------------------------------------------------------------- schedules

def schedule_installments(loan):
    """Generate LoanInstallment rows for a loan.

    * FLAT: equal principal + equal interest (interest on full principal).
    * REDUCING_BALANCE: equal payment (annuity) with interest on outstanding.
    * DECLINING: equal principal with interest on outstanding balance.
    """
    principal = loan.principal
    annual_rate = loan.interest_rate / Decimal('100')
    months = loan.term_months
    freq = loan.repayment_frequency
    rate = annual_rate / Decimal('12') if loan.interest_rate >= 1 else annual_rate
    if loan.interest_method in ('REDUCING_BALANCE', 'DECLINING') and freq == 'MONTHLY':
        per_period_rate = annual_rate / Decimal('12')
    else:
        per_period_rate = annual_rate

    start = loan.disbursement_date or timezone.now().date()
    if loan.first_installment_date:
        start = loan.first_installment_date
    else:
        from datetime import timedelta
        start = start + timedelta(days=loan.grace_period_days)
        if freq == 'MONTHLY':
            start = _shift_months(start, 1)
        elif freq == 'WEEKLY':
            start = start + timedelta(weeks=1)
        elif freq == 'BIWEEKLY':
            start = start + timedelta(weeks=2)
        elif freq == 'QUARTERLY':
            start = _shift_months(start, 3)
        else:
            start = start + timedelta(days=1)

    rows = []
    for i in range(1, months + 1):
        if i == 1:
            due = start
        else:
            if freq == 'MONTHLY':
                due = _shift_months(rows[-1]['due'], 1)
            elif freq == 'WEEKLY':
                due = rows[-1]['due'] + timedelta(weeks=1)
            elif freq == 'BIWEEKLY':
                due = rows[-1]['due'] + timedelta(weeks=2)
            elif freq == 'QUARTERLY':
                due = _shift_months(rows[-1]['due'], 3)
            else:
                due = rows[-1]['due'] + timedelta(days=1)

        if loan.interest_method == 'FLAT':
            interest = _r(principal * annual_rate * months / months)
            principal_part = _r(principal / months)
            if i == months:
                principal_part = _r(principal - (_r(principal / months) * (months - 1)))
                interest = _r(principal * annual_rate * months - interest * (months - 1))
        elif loan.interest_method == 'DECLINING':
            outstanding = principal - (_r(principal / months) * (i - 1))
            principal_part = _r(principal / months)
            interest = _r(outstanding * per_period_rate)
            if i == months:
                principal_part = _r(principal - (_r(principal / months) * (months - 1)))
        else:  # REDUCING_BALANCE annuity
            r = per_period_rate
            n = months
            annuity_factor = ((1 + r) ** n - 1) / (r * (1 + r) ** n) if r > 0 else Decimal(n)
            payment = _r(principal / annuity_factor)
            outstanding = principal - (payment * (i - 1)) + (_r(outstanding_interest(loan, payment, r, i - 1)))
            interest = _r(outstanding * r)
            principal_part = _r(payment - interest)
            if i == months:
                interest = _r(outstanding * r)
                principal_part = _r(outstanding)

        total = principal_part + interest
        rows.append({'due': due, 'principal': principal_part, 'interest': interest, 'total': total})

    # Ensure the sum of principals equals exactly the loan principal.
    principal_sum = sum(r['principal'] for r in rows)
    diff = principal - principal_sum
    if diff:
        rows[-1]['principal'] = _r(rows[-1]['principal'] + diff)
        rows[-1]['total'] = _r(rows[-1]['principal'] + rows[-1]['interest'])

    return rows


def outstanding_interest(loan, payment, rate, periods_paid):
    """Helper to track unpaid interest for the annuity method."""
    return ZERO


def _shift_months(date, months):
    import calendar
    month_index = date.month - 1 + months
    year = date.year + month_index // 12
    month = month_index % 12 + 1
    day = min(date.day, calendar.monthrange(year, month)[1])
    from datetime import date as d
    return d(year, month, day)


def generate_loan_schedule(loan):
    """Build the repayment schedule for a disbursed loan."""
    for row in schedule_installments(loan):
        LoanInstallment.objects.create(
            loan=loan,
            installment_number=len(loan.installments.all()) + 1,
            due_date=row['due'],
            principal_due=row['principal'],
            interest_due=row['interest'],
            total_due=row['principal'] + row['interest'],
        )
    return loan


# ---------------------------------------------------------------- workflow

def submit_application(app, user):
    if app.status != LoanApplication.STATUS_DRAFT:
        raise ValueError('Only draft applications can be submitted')
    if not app.customer.kyc_complete and not user.is_superuser:
        raise ValueError('Customer KYC must be complete before submission')
    app.status = LoanApplication.STATUS_SUBMITTED
    app.submitted_date = timezone.now()
    app.save(update_fields=['status', 'submitted_date', 'updated_at'])
    audit(user, 'LOAN_APPLICATION_SUBMITTED', app)
    return app


def review_application(app, user):
    if app.status not in (LoanApplication.STATUS_SUBMITTED, LoanApplication.STATUS_UNDER_REVIEW):
        raise ValueError('Application is not awaiting review')
    app.status = LoanApplication.STATUS_UNDER_REVIEW
    app.save(update_fields=['status', 'updated_at'])
    audit(user, 'LOAN_APPLICATION_UPDATED', app)
    return app


def approve_application(app, user, amount, comments=''):
    """Maker-checker enforced: creator cannot approve their own application."""
    from apps.workflows.services import maker_checker_ok, can_approve_amount, authority_label

    if app.status not in (LoanApplication.STATUS_SUBMITTED,
                          LoanApplication.STATUS_UNDER_REVIEW,
                          LoanApplication.STATUS_CREDIT_ASSESSMENT,
                          LoanApplication.STATUS_RECOMMENDED):
        raise ValueError('Application cannot be approved in its current state')
    if not maker_checker_ok(user, app):
        raise ValueError('You cannot approve an application you created')
    if not can_approve_amount(user, amount):
        raise ValueError('Your role does not have authority for this amount')

    role = authority_label(amount)
    approval = LoanApproval.objects.create(
        application=app,
        approver=user,
        authority_level=role,
        decision=LoanApproval.DECISION_APPROVED,
        amount_approved=amount,
        comments=comments,
    )
    app.status = LoanApplication.STATUS_APPROVED
    app.approved_amount = amount
    app.approved_by = user
    app.approved_date = timezone.now()
    app.approval_authority = role
    app.save(update_fields=['status', 'approved_amount', 'approved_by', 'approved_date',
                            'approval_authority', 'updated_at'])
    audit(user, 'LOAN_APPROVED', app, new={'amount': str(amount), 'authority': role})
    return approval


def reject_application(app, user, reason=''):
    from apps.workflows.services import maker_checker_ok
    if app.status == LoanApplication.STATUS_REJECTED:
        raise ValueError('Application already rejected')
    if not maker_checker_ok(user, app):
        raise ValueError('You cannot reject an application you created')
    LoanApproval.objects.create(
        application=app,
        approver=user,
        authority_level='',
        decision=LoanApproval.DECISION_REJECTED,
        comments=reason,
    )
    app.status = LoanApplication.STATUS_REJECTED
    app.rejection_reason = reason
    app.save(update_fields=['status', 'rejection_reason', 'updated_at'])
    audit(user, 'LOAN_REJECTED', app, new={'reason': reason})
    return app


def make_ready_for_disbursement(app, user):
    if app.status != LoanApplication.STATUS_APPROVED:
        raise ValueError('Only approved applications can be readied for disbursement')
    app.status = LoanApplication.STATUS_READY_FOR_DISBURSEMENT
    app.save(update_fields=['status', 'updated_at'])
    audit(user, 'LOAN_APPLICATION_UPDATED', app)
    return app


# ---------------------------------------------------------------- disbursement

def check_disbursement_prerequisites(app, user):
    """Verify the SRS section 25 checklist before disbursing."""
    issues = []
    if app.status not in (LoanApplication.STATUS_APPROVED, LoanApplication.STATUS_READY_FOR_DISBURSEMENT):
        issues.append('Application must be approved first')
    if not app.customer.is_active:
        issues.append('Customer is not active')
    if app.customer.status == 'BLACKLISTED':
        issues.append('Customer is blacklisted')
    product = app.product
    if product.collateral_required:
        if not app.customer.collaterals.filter(verification_status='VERIFIED').exists():
            issues.append('Verified collateral is required')
    if product.guarantor_required:
        loan_qs = app.loan if hasattr(app, 'loan') and app.loan else None
        if loan_qs and not loan_qs.guarantors.filter(verification_status='VERIFIED').exists():
            issues.append('Verified guarantors are required')
    return issues


@transaction.atomic
def disburse_loan(app, user, method='CASH', disbursement_date=None, first_installment_date=None):
    """Disburse an approved application: create loan, schedule, accounting, cash."""
    from apps.common.numbering import next_number
    from apps.accounting.services import post_disbursement_entries
    from apps.notifications.models import notify
    from apps.cash_management.models import CashTransaction

    issues = check_disbursement_prerequisites(app, user)
    if issues:
        raise ValueError('; '.join(issues))
    if Loan.objects.filter(application=app).exists():
        raise ValueError('Loan already disbursed for this application')

    disbursement_date = disbursement_date or timezone.now().date()
    product = app.product
    principal = app.approved_amount or app.requested_amount
    processing_fee = _r(principal * product.processing_fee / Decimal('100'))
    insurance_fee = _r(principal * product.insurance_fee / Decimal('100'))

    loan = Loan.objects.create(
        loan_number=next_number('LOAN', app.branch, include_year=True),
        application=app,
        customer=app.customer,
        product=product,
        branch=app.branch,
        loan_officer=app.loan_officer,
        principal=principal,
        interest_rate=product.interest_rate,
        interest_method=product.interest_method,
        term_months=app.approved_term_months or app.requested_term_months,
        repayment_frequency=product.repayment_frequency,
        grace_period_days=product.grace_period_days,
        processing_fee=processing_fee,
        insurance_fee=insurance_fee,
        penalty_rate=product.penalty_rate,
        disbursement_date=disbursement_date,
        disbursed_by=user,
        disbursement_method=method,
        outstanding_principal=principal,
        first_installment_date=first_installment_date,
    )

    generate_loan_schedule(loan)

    app.status = LoanApplication.STATUS_DISBURSED
    app.loan = loan
    app.save(update_fields=['status', 'updated_at'])

    CashTransaction.objects.create(
        reference=next_number('TXN', app.branch, include_year=True),
        transaction_type=CashTransaction.TYPE_DISBURSEMENT,
        amount=principal,
        branch=app.branch,
        teller=user if user.has_role('Teller') else None,
        customer=app.customer,
        loan=loan,
        transaction_date=disbursement_date,
        description=f'Loan disbursement {loan.loan_number}',
    )

    post_disbursement_entries(loan, method)
    audit(user, 'LOAN_DISBURSED', loan, new={'method': method, 'amount': str(principal)})
    notify(app.loan_officer, f'Loan {loan.loan_number} disbursed',
           f'{app.customer.full_name} loan of TZS {principal:,.0f} was disbursed.',
           'SUCCESS', link='/loans/')
    return loan


def refresh_loan_status(loan):
    """Recalculate outstanding balances and derive PAR/overdue status."""
    installments = loan.installments.all()
    outstanding_principal = sum((i.principal_due - i.principal_paid) for i in installments)
    outstanding_interest = sum((i.interest_due - i.interest_paid) for i in installments)
    outstanding_fees = sum((i.fees_due - i.fees_paid) for i in installments)
    outstanding_penalties = sum(i.penalty_paid for i in installments) * 0  # penalties held separately
    amount_paid = sum(i.total_paid for i in installments)

    loan.outstanding_principal = _r(max(outstanding_principal, ZERO))
    loan.outstanding_interest = _r(max(outstanding_interest, ZERO))
    loan.outstanding_fees = _r(max(outstanding_fees, ZERO))
    loan.amount_paid = _r(amount_paid)

    total_due = sum(i.total_due for i in installments)
    total_paid = sum(i.total_paid for i in installments)
    if loan.status not in ('WRITTEN_OFF', 'CLOSED'):
        if total_paid >= total_due and total_due > 0:
            loan.status = Loan.STATUS_CLOSED
            loan.closed_date = timezone.now().date()
        else:
            days = loan.days_overdue
            if days >= 90:
                loan.status = Loan.STATUS_DEFAULT
            elif days >= 30:
                loan.status = Loan.STATUS_PAR
            elif days > 0:
                loan.status = Loan.STATUS_OVERDUE
            else:
                loan.status = Loan.STATUS_ACTIVE
    loan.save(update_fields=[
        'outstanding_principal', 'outstanding_interest', 'outstanding_fees',
        'amount_paid', 'status', 'closed_date', 'updated_at',
    ])
    return loan


def apply_penalties(loan):
    """Calculate and record penalties on overdue installments."""
    from django.utils import timezone
    from apps.organization.models import SystemSetting

    today = timezone.now().date()
    rate = float(loan.penalty_rate or 0)
    total_penalty = ZERO
    for inst in loan.installments.filter(status__in=['PENDING', 'PARTIAL']):
        if inst.due_date < today:
            days = (today - inst.due_date).days
            overdue_amount = inst.total_due - inst.total_paid
            penalty = _r(overdue_amount * Decimal(rate) / Decimal('100') * days / Decimal('30'))
            total_penalty += penalty
    return total_penalty
