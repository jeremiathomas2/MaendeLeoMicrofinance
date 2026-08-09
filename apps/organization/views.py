from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from apps.accounts.roles import is_org_wide
from apps.audit.models import audit
from apps.organization.forms import BranchForm
from apps.organization.models import Branch, Organization, SystemSetting
from apps.reports.services import branch_performance


@login_required
def branches_page(request):
    branches = request.user.accessible_branches().prefetch_related('customers', 'loans')
    if request.user.is_superuser or is_org_wide(request.user):
        branches = Branch.objects.all()
    performance = {row['branch'].id: row for row in branch_performance()}
    context = {
        'branches': branches,
        'performance': performance,
        'form': BranchForm(),
    }
    return render(request, 'pages/branches.html', context)


@login_required
def branch_create(request):
    if not request.user.is_superuser and not request.user.has_perm('organization.add_branch'):
        messages.error(request, 'You do not have permission to add branches.')
        return redirect('branches_page')
    if request.method == 'POST':
        form = BranchForm(request.POST)
        if form.is_valid():
            branch = form.save()
            audit(request.user, 'SYSTEM_EVENT', branch, branch=branch, request=request)
            messages.success(request, f'Branch {branch.name} added.')
        else:
            messages.error(request, 'Please correct the form.')
    return redirect('branches_page')


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
