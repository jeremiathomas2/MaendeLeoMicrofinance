from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.roles import is_org_wide
from apps.audit.models import audit
from apps.organization.forms import BranchForm
from apps.organization.models import Branch, Organization, SystemSetting

ZERO = Decimal('0.00')


def _can(user, perm):
    return user.is_superuser or user.has_perm(perm)


def _branch_stats(branch):
    """Aggregates for one branch (works for any status)."""
    from apps.customers.models import Customer
    from apps.loans.models import Loan
    from apps.savings.models import SavingsAccount

    active_statuses = ['ACTIVE', 'OVERDUE', 'PAR', 'DEFAULT']
    active = Loan.objects.filter(branch=branch, status__in=active_statuses)
    gross = active.aggregate(s=Sum('principal'))['s'] or ZERO
    par30 = ZERO
    for loan in active:
        if loan.days_overdue >= 30:
            par30 += loan.outstanding_principal
    par_pct = (par30 / gross * 100) if gross else ZERO
    return {
        'active_loans': active.count(),
        'gross': float(gross),
        'par30': float(par30),
        'par30_pct': float(par_pct),
        'customers': Customer.objects.filter(branch=branch, status='ACTIVE').count(),
        'savings': SavingsAccount.objects.filter(branch=branch).count(),
    }


def _branch_payload(branch, stats):
    """Serializable dict used to populate the detail modal."""
    staff = []
    seen = set()
    for a in branch.assigned_staff.select_related('user', 'user__staff_profile'):
        u = a.user
        if u.id in seen:
            continue
        seen.add(u.id)
        profile = getattr(u, 'staff_profile', None)
        staff.append({
            'name': u.get_full_name() or u.username,
            'job_title': profile.job_title if profile else '',
            'primary': a.is_primary,
        })
    for p in branch.primary_staff.select_related('user'):
        u = p.user
        if u.id in seen:
            continue
        seen.add(u.id)
        staff.append({
            'name': u.get_full_name() or u.username,
            'job_title': p.job_title,
            'primary': True,
        })
    return {
        'pk': branch.pk,
        'code': branch.code,
        'name': branch.name,
        'region': branch.region or '',
        'address': branch.address or '',
        'phone': branch.phone or '',
        'email': branch.email or '',
        'manager_id': branch.manager_id or '',
        'manager': branch.manager.get_full_name() if branch.manager else '',
        'status': branch.get_status_display(),
        'status_code': branch.status,
        'opening_date': branch.opening_date.isoformat() if branch.opening_date else '',
        'operating_hours': branch.operating_hours or '',
        'created_at': branch.created_at.strftime('%d %b %Y') if branch.created_at else '',
        'updated_at': branch.updated_at.strftime('%d %b %Y') if branch.updated_at else '',
        'stats': stats,
        'staff': staff,
        'departments': [d.name for d in branch.departments.all()],
    }


def _delete_blockers(branch):
    """Human-readable list of dependent records preventing deletion."""
    from apps.accounting.models import Expense, JournalEntry
    from apps.cash_management.models import CashTransaction, TellerSession
    from apps.customers.models import Customer
    from apps.loans.models import Loan, LoanApplication
    from apps.repayments.models import Repayment
    from apps.savings.models import SavingsAccount

    checks = [
        ('customers', Customer.objects.filter(branch=branch)),
        ('loans', Loan.objects.filter(branch=branch)),
        ('loan applications', LoanApplication.objects.filter(branch=branch)),
        ('savings accounts', SavingsAccount.objects.filter(branch=branch)),
        ('repayments', Repayment.objects.filter(branch=branch)),
        ('journal entries', JournalEntry.objects.filter(branch=branch)),
        ('expenses', Expense.objects.filter(branch=branch)),
        ('teller sessions', TellerSession.objects.filter(branch=branch)),
        ('cash transactions', CashTransaction.objects.filter(branch=branch)),
        ('departments', branch.departments.all()),
        ('staff assignments', branch.assigned_staff.all()),
    ]
    blockers = [label for label, qs in checks if qs.exists()]
    if branch.primary_staff.exists():
        blockers.append('staff with this as their primary branch')
    return blockers


@login_required
def branches_page(request):
    q = request.GET.get('q', '')
    status = request.GET.get('status', '')
    region = request.GET.get('region', '')

    if request.user.is_superuser or is_org_wide(request.user):
        branches = Branch.objects.all()
    else:
        branches = request.user.accessible_branches()

    if q:
        branches = branches.filter(
            Q(name__icontains=q) | Q(code__icontains=q) | Q(region__icontains=q)
            | Q(phone__icontains=q) | Q(email__icontains=q)
        )
    if status:
        branches = branches.filter(status=status)
    if region:
        branches = branches.filter(region=region)

    branches = branches.prefetch_related('assigned_staff', 'primary_staff', 'departments').order_by('name')
    stats = {b.id: _branch_stats(b) for b in branches}
    payload = [_branch_payload(b, stats[b.id]) for b in branches]
    regions = list(Branch.objects.exclude(region='').values_list('region', flat=True).distinct().order_by('region'))

    context = {
        'branches': branches,
        'stats': stats,
        'branch_payload': payload,
        'regions': regions,
        'q': q,
        'status': status,
        'region': region,
        'can_add': _can(request.user, 'organization.add_branch'),
        'can_edit': _can(request.user, 'organization.change_branch'),
        'can_delete': _can(request.user, 'organization.delete_branch'),
        'form': BranchForm(),
    }
    return render(request, 'pages/branches.html', context)


@login_required
def branch_create(request):
    if not _can(request.user, 'organization.add_branch'):
        messages.error(request, 'You do not have permission to add branches.')
        return redirect('branches_page')
    if request.method == 'POST':
        form = BranchForm(request.POST)
        if form.is_valid():
            branch = form.save()
            audit(request.user, 'SYSTEM_EVENT', branch, branch=branch, request=request,
                  new={'created': True})
            messages.success(request, f'Branch {branch.name} added.')
        else:
            messages.error(request, 'Please correct the form.')
    return redirect('branches_page')


@login_required
def branch_edit(request, pk):
    if not _can(request.user, 'organization.change_branch'):
        messages.error(request, 'You do not have permission to edit branches.')
        return redirect('branches_page')
    branch = get_object_or_404(Branch, pk=pk)
    if request.method == 'POST':
        form = BranchForm(request.POST, instance=branch)
        if form.is_valid():
            previous = {f: _serialize(branch, f) for f in form.cleaned_data}
            branch = form.save()
            audit(request.user, 'SYSTEM_EVENT', branch, branch=branch, request=request,
                  previous=previous, new={f: _serialize(branch, f) for f in form.cleaned_data})
            messages.success(request, f'Branch {branch.name} updated.')
        else:
            messages.error(request, 'Please correct the form.')
    return redirect('branches_page')


@login_required
def branch_delete(request, pk):
    if not _can(request.user, 'organization.delete_branch'):
        messages.error(request, 'You do not have permission to delete branches.')
        return redirect('branches_page')
    branch = get_object_or_404(Branch, pk=pk)
    if request.method == 'POST':
        blockers = _delete_blockers(branch)
        if blockers:
            messages.error(request, (
                f'Cannot delete {branch.name}: it still has {", ".join(blockers)}. '
                'Set the branch status to INACTIVE or CLOSED instead.'
            ))
            return redirect('branches_page')
        try:
            audit(request.user, 'SYSTEM_EVENT', branch, branch=branch, request=request,
                  previous={'deleted': True}, reason='Branch deleted')
            branch.delete()
            messages.success(request, f'Branch {branch.name} deleted.')
        except ProtectedError:
            messages.error(request, (
                f'Cannot delete {branch.name}: linked records exist. '
                'Set the branch status to INACTIVE or CLOSED instead.'
            ))
    return redirect('branches_page')


def _serialize(branch, field):
    value = getattr(branch, field)
    if field == 'manager':
        return str(value) if value else ''
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    return value


@login_required
def settings_page(request):
    organization = Organization.get()
    settings = SystemSetting.objects.all()
    categories = [c[0] for c in SystemSetting.CATEGORY_CHOICES]
    context = {
        'organization': organization,
        'settings': settings,
        'categories': categories,
    }
    return render(request, 'pages/settings.html', context)


@login_required
def settings_save(request):
    if not (request.user.is_superuser or request.user.has_perm('organization.change_systemsetting')):
        messages.error(request, 'You do not have permission to change settings.')
        return redirect('settings_page')
    if request.method == 'POST':
        changed = 0
        for key, value in request.POST.items():
            if key.startswith('setting_'):
                real_key = key[len('setting_'):]
                obj, created = SystemSetting.objects.get_or_create(key=real_key)
                if obj.value != value:
                    audit(request.user, 'SETTING_CHANGED', obj, new={real_key: value},
                          previous={real_key: obj.value}, request=request)
                    obj.value = value
                    obj.save()
                    changed += 1
        if changed:
            messages.success(request, f'{changed} setting(s) updated.')
        else:
            messages.info(request, 'No changes detected.')
    return redirect('settings_page')
