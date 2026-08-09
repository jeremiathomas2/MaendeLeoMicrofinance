from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q

from apps.accounts.services import filter_by_scope
from apps.audit.models import audit
from apps.common.numbering import next_number
from apps.customers.forms import CustomerDocumentForm, CustomerRegistrationForm, GroupForm
from apps.customers.models import Customer, CustomerDocument, CustomerGroup, GroupMember
from apps.customers.services import build_customer_search

PERM_REGISTER = 'customers.register_customer'
PERM_VERIFY = 'customers.verify_customer_kyc'


def _has(request, perm):
    return request.user.is_superuser or request.user.has_perm(perm)


@login_required
def customers_page(request):
    q = request.GET.get('q', '')
    branch_id = request.GET.get('branch', '')
    status = request.GET.get('status', '')

    customers = filter_by_scope(request.user, Customer.objects.select_related('branch'), 'branch')
    if q:
        customers = customers.filter(
            Q(full_name__icontains=q) | Q(phone__icontains=q) | Q(customer_number__icontains=q)
            | Q(national_id__icontains=q) | Q(email__icontains=q)
        )
    if branch_id:
        customers = customers.filter(branch_id=branch_id)
    if status:
        customers = customers.filter(status=status)

    groups = filter_by_scope(request.user, CustomerGroup.objects.prefetch_related('members'), 'branch')
    documents = CustomerDocument.objects.select_related('customer', 'uploaded_by', 'verified_by').order_by('-upload_date')

    context = {
        'customers': customers[:100],
        'groups': groups[:30],
        'documents': documents[:50],
        'branches': request.user.accessible_branches(),
        'q': q,
        'can_register': _has(request, PERM_REGISTER),
        'can_verify': _has(request, PERM_VERIFY),
        'register_form': CustomerRegistrationForm(user=request.user),
        'group_form': GroupForm(),
        'doc_form': CustomerDocumentForm(),
    }
    return render(request, 'pages/customers.html', context)


@login_required
def customer_register(request):
    if not _has(request, PERM_REGISTER):
        messages.error(request, 'You do not have permission to register customers.')
        return redirect('customers_page')
    if request.method == 'POST':
        form = CustomerRegistrationForm(request.POST, user=request.user)
        if form.is_valid():
            customer = form.save(commit=False)
            branch = form.cleaned_data.get('branch') or (
                request.user.accessible_branches().first()
            )
            customer.branch = branch
            customer.registered_by = request.user
            customer.customer_number = next_number('CUS', branch, include_year=False)
            customer.save()
            group = form.cleaned_data.get('group')
            if group:
                GroupMember.objects.get_or_create(group=group, customer=customer)
                if group.leader_id is None:
                    group.leader = customer
                    group.save(update_fields=['leader'])
            audit(request.user, 'CUSTOMER_CREATED', customer, branch=branch, request=request)
            messages.success(request, f'Customer {customer.customer_number} registered successfully.')
            return redirect('customer_detail', pk=customer.pk)
        messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomerRegistrationForm(user=request.user)
    return render(request, 'pages/customer_form.html', {'form': form, 'title': 'Register Customer'})


@login_required
def customer_detail(request, pk):
    customer = get_object_or_404(
        filter_by_scope(request.user, Customer.objects.select_related('branch'), 'branch'), pk=pk,
    )
    from apps.loans.models import Loan, LoanApplication
    from apps.savings.models import SavingsAccount
    loans = Loan.objects.filter(customer=customer)
    applications = LoanApplication.objects.filter(customer=customer)
    accounts = SavingsAccount.objects.filter(customer=customer)
    context = {
        'customer': customer,
        'loans': loans,
        'applications': applications,
        'accounts': accounts,
        'doc_form': CustomerDocumentForm(),
    }
    return render(request, 'pages/customer_detail.html', context)


@login_required
def customer_document_upload(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == 'POST':
        form = CustomerDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.customer = customer
            doc.uploaded_by = request.user
            doc.save()
            audit(request.user, 'CUSTOMER_UPDATED', doc, branch=customer.branch, request=request)
            messages.success(request, 'Document uploaded.')
    return redirect('customer_detail', pk=customer.pk)


@login_required
def customer_document_verify(request, pk):
    if not _has(request, PERM_VERIFY):
        messages.error(request, 'You do not have permission to verify documents.')
        return redirect('customers_page')
    doc = get_object_or_404(CustomerDocument, pk=pk)
    action = request.POST.get('action', 'verify')
    from django.utils import timezone
    if action == 'verify':
        doc.verification_status = CustomerDocument.STATUS_VERIFIED
    else:
        doc.verification_status = CustomerDocument.STATUS_REJECTED
    doc.verified_by = request.user
    doc.verification_date = timezone.now()
    doc.save()
    customer = doc.customer
    if customer.documents.exclude(verification_status=CustomerDocument.STATUS_VERIFIED).count() == 0:
        customer.kyc_complete = True
        customer.kyc_verified_at = timezone.now()
        customer.save(update_fields=['kyc_complete', 'kyc_verified_at'])
    audit(request.user, 'CUSTOMER_DOCUMENT_VERIFIED', doc, branch=customer.branch,
          new={'status': doc.verification_status}, request=request)
    messages.success(request, 'Document verified.')
    return redirect('customers_page')


@login_required
def group_create(request):
    if request.method == 'POST':
        form = GroupForm(request.POST)
        if form.is_valid():
            group = form.save(commit=False)
            group.group_number = next_number('GRP', group.branch, include_year=False)
            group.created_by = request.user
            group.save()
            if group.leader:
                GroupMember.objects.get_or_create(group=group, customer=group.leader,
                                                 defaults={'role': GroupMember.ROLE_LEADER})
            audit(request.user, 'GROUP_CREATED', group, branch=group.branch, request=request)
            messages.success(request, f'Group {group.name} created.')
            return redirect('customers_page')
        messages.error(request, 'Please correct the errors below.')
    return redirect('customers_page')


@login_required
def group_add_member(request, pk):
    group = get_object_or_404(CustomerGroup, pk=pk)
    customer = get_object_or_404(Customer, pk=request.POST.get('customer'))
    role = request.POST.get('role', GroupMember.ROLE_MEMBER)
    GroupMember.objects.get_or_create(group=group, customer=customer, defaults={'role': role})
    if role == GroupMember.ROLE_LEADER and group.leader_id is None:
        group.leader = customer
        group.save(update_fields=['leader'])
    messages.success(request, 'Member added to group.')
    return redirect('customers_page')
