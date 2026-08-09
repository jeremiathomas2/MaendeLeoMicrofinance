from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.audit.models import AuditLog, ALL_ACTIONS
from apps.accounts.roles import is_org_wide
from apps.reports.utils import csv_response


@login_required
def audit_page(request):
    action = request.GET.get('action', '')
    user_q = request.GET.get('user', '')
    date_from = request.GET.get('date', '')

    logs = AuditLog.objects.select_related('user', 'branch')
    if not (request.user.is_superuser or is_org_wide(request.user)):
        logs = logs.filter(user=request.user)
    if action:
        logs = logs.filter(action=action)
    if user_q:
        logs = logs.filter(user__username__icontains=user_q)
    if date_from:
        logs = logs.filter(timestamp__date=date_from)

    context = {
        'logs': logs[:100],
        'actions': [a for a in ALL_ACTIONS],
        'branches': request.user.accessible_branches(),
    }
    return render(request, 'pages/audit.html', context)


@login_required
def audit_export(request):
    logs = AuditLog.objects.select_related('user', 'branch')
    if not (request.user.is_superuser or is_org_wide(request.user)):
        logs = logs.filter(user=request.user)
    rows = [[log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
             log.user.get_full_name() if log.user else 'System',
             log.action, log.object_repr,
             log.branch.name if log.branch else '—',
             log.ip_address or '—', log.reason] for log in logs[:2000]]
    return csv_response('audit_log', ['Timestamp', 'User', 'Action', 'Object', 'Branch', 'IP', 'Reason'], rows)
