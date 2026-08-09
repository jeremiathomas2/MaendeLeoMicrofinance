"""Portfolio analytics and report data services (SRS sections 34, 51, 52)."""

from decimal import Decimal
from django.db.models import Sum, Count
from django.utils import timezone

from apps.loans.models import Loan, LoanApplication
from apps.customers.models import Customer
from apps.repayments.models import Repayment

ZERO = Decimal('0.00')


def par_tiers():
    """Return PAR buckets and counts for the whole portfolio."""
    today = timezone.now().date()
    tiers = {'current': {'amount': ZERO, 'count': 0},
             'par_1_29': {'amount': ZERO, 'count': 0},
             'par_30_89': {'amount': ZERO, 'count': 0},
             'par_90': {'amount': ZERO, 'count': 0}}

    for loan in Loan.objects.filter(status__in=['ACTIVE', 'OVERDUE', 'PAR', 'DEFAULT']).select_related('customer'):
        days = loan.days_overdue
        amount = loan.outstanding_principal
        if days <= 0:
            tiers['current']['amount'] += amount
            tiers['current']['count'] += 1
        elif days < 30:
            tiers['par_1_29']['amount'] += amount
            tiers['par_1_29']['count'] += 1
        elif days < 90:
            tiers['par_30_89']['amount'] += amount
            tiers['par_30_89']['count'] += 1
        else:
            tiers['par_90']['amount'] += amount
            tiers['par_90']['count'] += 1
    return tiers


def par_value(days):
    """Outstanding principal on loans overdue by at least ``days``."""
    from apps.loans.models import Loan
    total = ZERO
    for loan in Loan.objects.filter(status__in=['ACTIVE', 'OVERDUE', 'PAR', 'DEFAULT']):
        if loan.days_overdue >= days:
            total += loan.outstanding_principal
    return total


def portfolio_summary():
    total_portfolio = Loan.objects.filter(
        status__in=['ACTIVE', 'OVERDUE', 'PAR', 'DEFAULT'],
    ).aggregate(s=Sum('outstanding_principal'))['s'] or ZERO
    gross = Loan.objects.filter(
        status__in=['ACTIVE', 'OVERDUE', 'PAR', 'DEFAULT'],
    ).aggregate(s=Sum('principal'))['s'] or ZERO
    par30 = par_value(30)
    par_pct = (par30 / gross * 100) if gross else ZERO
    active_loans = Loan.objects.filter(
        status__in=['ACTIVE', 'OVERDUE', 'PAR', 'DEFAULT'],
    ).count()
    return {
        'total_portfolio': total_portfolio,
        'gross_portfolio': gross,
        'par30': par30,
        'par_pct': par_pct,
        'active_loans': active_loans,
    }


def dashboard_kpis():
    today = timezone.now().date()
    active_customers = Customer.objects.filter(status='ACTIVE').count()
    new_customers = Customer.objects.filter(created_at__date=today).count()
    total_customers = Customer.objects.count()
    applications = LoanApplication.objects.count()
    pending_apps = LoanApplication.objects.filter(
        status__in=['SUBMITTED', 'UNDER_REVIEW', 'CREDIT_ASSESSMENT', 'RECOMMENDED', 'READY_FOR_DISBURSEMENT'],
    ).count()
    disbursed = Loan.objects.filter(disbursement_date__isnull=False).count()
    collections_today = Repayment.objects.filter(payment_date=today).aggregate(s=Sum('amount'))['s'] or ZERO
    overdue_loans = Loan.objects.filter(status__in=['OVERDUE', 'PAR', 'DEFAULT']).count()
    return {
        'active_customers': active_customers,
        'new_customers': new_customers,
        'total_customers': total_customers,
        'applications': applications,
        'pending_apps': pending_apps,
        'disbursed': disbursed,
        'collections_today': collections_today,
        'overdue_loans': overdue_loans,
    }


def monthly_activity(months=6):
    """Return disbursements and collections per month for the bar chart.

    Each row carries raw values plus percentages scaled against the peak
    value so the bars render proportionally inside the chart height.
    """
    import calendar
    today = timezone.now().date()
    result = []
    for offset in range(months - 1, -1, -1):
        year = today.year
        month = today.month - offset
        while month <= 0:
            month += 12
            year -= 1
        disb = Loan.objects.filter(disbursement_date__year=year, disbursement_date__month=month).count()
        coll = Repayment.objects.filter(payment_date__year=year, payment_date__month=month).aggregate(s=Sum('amount'))['s'] or ZERO
        result.append({
            'label': calendar.month_abbr[month],
            'disbursements': disb,
            'collections': float(coll),
        })
    peak = max([max(r['disbursements'], r['collections']) for r in result] + [1])
    for r in result:
        r['disb_pct'] = round(r['disbursements'] / peak * 100)
        r['coll_pct'] = round(r['collections'] / peak * 100)
    return result


def branch_performance():
    """Per-branch aggregates for the dashboard table."""
    rows = []
    from apps.organization.models import Branch
    for branch in Branch.objects.filter(status=Branch.STATUS_ACTIVE):
        active_loans = Loan.objects.filter(
            branch=branch, status__in=['ACTIVE', 'OVERDUE', 'PAR', 'DEFAULT'],
        ).count()
        disbursed = Loan.objects.filter(branch=branch).count()
        gross = Loan.objects.filter(branch=branch, status__in=['ACTIVE', 'OVERDUE', 'PAR', 'DEFAULT']).aggregate(s=Sum('principal'))['s'] or ZERO
        par30 = ZERO
        for loan in Loan.objects.filter(branch=branch, status__in=['ACTIVE', 'OVERDUE', 'PAR', 'DEFAULT']):
            if loan.days_overdue >= 30:
                par30 += loan.outstanding_principal
        par_pct = (par30 / gross * 100) if gross else ZERO
        customers = Customer.objects.filter(branch=branch, status='ACTIVE').count()
        due = Repayment.objects.filter(branch=branch).aggregate(s=Sum('amount'))['s'] or ZERO
        rows.append({
            'branch': branch,
            'active_loans': active_loans,
            'disbursed': disbursed,
            'gross': gross,
            'par30_pct': par_pct,
            'customers': customers,
            'collections': due,
        })
    return rows
