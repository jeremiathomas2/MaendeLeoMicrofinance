from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from apps.accounts.services import filter_by_scope
from apps.audit.models import AuditLog
from apps.customers.models import Customer
from apps.loans.models import Loan
from apps.notifications.models import Notification
from apps.organization.models import Branch
from apps.repayments.models import Repayment
from apps.reports import services as report_services


@login_required
def dashboard(request):
    org_branches = request.user.accessible_branches()
    loans = filter_by_scope(request.user, Loan.objects.all(), 'branch')

    portfolio = report_services.portfolio_summary()
    kpis = report_services.dashboard_kpis()
    par = report_services.par_tiers()
    months = report_services.monthly_activity()

    today = timezone.now().date()
    collections_today = filter_by_scope(request.user, Repayment.objects.filter(payment_date=today), 'branch')
    recent_activity = AuditLog.objects.filter(branch__in=org_branches) if not request.user.is_superuser \
        else AuditLog.objects.all()

    context = {
        'portfolio': portfolio,
        'kpis': kpis,
        'par': par,
        'months': months,
        'par30_pct': portfolio['par_pct'],
        'active_customers': Customer.objects.filter(status='ACTIVE', branch__in=org_branches).count(),
        'branches': report_services.branch_performance(),
        'recent_repayments': collections_today[:8],
        'activity': recent_activity[:8],
        'today': today,
    }
    return render(request, 'pages/dashboard.html', context)


@login_required
def reports_page(request):
    from apps.reports.report_defs import REPORT_CATEGORIES
    return render(request, 'pages/reports.html', {'categories': REPORT_CATEGORIES})
