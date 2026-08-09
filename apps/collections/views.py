from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404

from apps.accounts.services import filter_by_scope
from apps.audit.models import audit
from apps.collections.forms import CollectionActionForm
from apps.collections.models import CollectionAction
from apps.loans.models import Loan


@login_required
def collections_page(request):
    loans = filter_by_scope(request.user, Loan.objects.filter(
        status__in=['OVERDUE', 'PAR', 'DEFAULT']).select_related('customer', 'branch', 'loan_officer'), 'branch')
    cards = []
    for loan in loans:
        inst = loan.installments.filter(status__in=['PENDING', 'PARTIAL']).order_by('due_date').first()
        cards.append({
            'loan': loan,
            'due_date': inst.due_date if inst else None,
            'days_overdue': loan.days_overdue,
            'last_action': loan.collection_actions.first(),
        })
    actions = filter_by_scope(request.user, CollectionAction.objects.select_related(
        'customer', 'loan', 'officer'), 'branch')
    context = {
        'cards': cards,
        'actions': actions[:50],
        'form': CollectionActionForm(),
    }
    return render(request, 'pages/collections.html', context)


@login_required
def collection_action_create(request):
    if request.method == 'POST':
        form = CollectionActionForm(request.POST)
        if form.is_valid():
            action = form.save(commit=False)
            action.officer = request.user
            action.save()
            audit(request.user, 'CUSTOMER_UPDATED', action,
                  branch=action.customer.branch, request=request)
            messages.success(request, 'Collection action recorded.')
    return redirect('collections_page')


@login_required
def collection_action_resolve(request, pk):
    action = get_object_or_404(CollectionAction, pk=pk)
    action.status = CollectionAction.STATUS_RESOLVED
    action.save(update_fields=['status'])
    messages.success(request, 'Follow-up marked as resolved.')
    return redirect('collections_page')
