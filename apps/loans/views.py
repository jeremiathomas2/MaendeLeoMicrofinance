from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q

from apps.accounts.roles import can_approve, can_disburse, role_names_for
from apps.accounts.services import filter_by_scope
from apps.audit.models import audit
from apps.common.numbering import next_number
from apps.credit.models import CreditAssessment, CreditScoreComponent
from apps.credit.views_helpers import compute_and_store
from apps.customers.models import Customer
from apps.loans.forms import CreditAssessmentForm, LoanApplicationForm
from apps.loans.models import Loan, LoanApplication, LoanApproval
from apps.loans import services as loan_services
from apps.repayments.models import Repayment
from apps.repayments import services as repayment_services
from apps.workflows.services import can_approve_amount, authority_label

PERM_APPROVE = 'loans.approve_loan'
PERM_DISBURSE = 'loans.disburse_loan'
PERM_ASSESS = 'credit.perform_assessment'


def _has(request, perm):
    return request.user.is_superuser or request.user.has_perm(perm)


@login_required
def loans_page(request):
    apps = filter_by_scope(request.user, LoanApplication.objects.select_related(
        'customer', 'product', 'branch', 'loan_officer'), 'branch')
    if request.GET.get('status'):
        apps = apps.filter(status=request.GET['status'])
    if request.GET.get('product'):
        apps = apps.filter(product_id=request.GET['product'])

    loans = filter_by_scope(request.user, Loan.objects.select_related(
        'customer', 'product', 'branch'), 'branch')
    repayments = filter_by_scope(request.user, Repayment.objects.select_related(
        'customer', 'loan', 'branch', 'teller'), 'branch')
    assessments = CreditAssessment.objects.select_related('application', 'credit_officer').filter(
        application__in=apps)
    approvals = LoanApproval.objects.select_related('application', 'approver').filter(application__in=apps)

    context = {
        'applications': apps[:100],
        'loans': loans[:100],
        'repayments': repayments[:100],
        'assessments': assessments,
        'approvals': approvals,
        'weights': CreditScoreComponent.objects.filter(is_active=True).order_by('key'),
        'can_approve': _has(request, PERM_APPROVE) or can_approve(request.user),
        'can_disburse': _has(request, PERM_DISBURSE) or can_disburse(request.user),
        'can_assess': _has(request, PERM_ASSESS),
        'app_form': LoanApplicationForm(user=request.user),
        'now': __import__('django.utils.timezone', fromlist=['now']).now().date(),
    }
    return render(request, 'pages/loans.html', context)


@login_required
def loan_application_create(request):
    initial = {}
    customer_pk = request.GET.get('customer')
    if customer_pk:
        customer = filter_by_scope(request.user, Customer.objects.filter(status='ACTIVE'), 'branch') \
            .filter(pk=customer_pk).first()
        if customer:
            initial['customer'] = customer
    if request.method == 'POST':
        form = LoanApplicationForm(request.POST, user=request.user)
        if form.is_valid():
            app = form.save(commit=False)
            branch = request.user.accessible_branches().filter(id=app.customer.branch_id).first()
            if branch is None:
                branch = app.customer.branch
            app.branch = branch
            app.loan_officer = request.user
            app.application_number = next_number('APP', branch, include_year=True)
            app.status = LoanApplication.STATUS_DRAFT
            app.save()
            audit(request.user, 'LOAN_APPLICATION_CREATED', app, branch=branch, request=request)
            messages.success(request, f'Application {app.application_number} created.')
            return redirect('loans_page')
        messages.error(request, 'Please correct the errors below.')
        context = {'form': form, 'title': 'New Loan Application'}
        return render(request, 'pages/loan_form.html', context)
    form = LoanApplicationForm(user=request.user, initial=initial)
    return render(request, 'pages/loan_form.html', {'form': form, 'title': 'New Loan Application'})


@login_required
def loan_application_submit(request, pk):
    app = get_object_or_404(LoanApplication, pk=pk)
    try:
        loan_services.submit_application(app, request.user)
        messages.success(request, 'Application submitted for review.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('loans_page')


@login_required
def loan_application_detail(request, pk):
    app = get_object_or_404(LoanApplication.objects.select_related(
        'customer', 'product', 'branch', 'loan_officer'), pk=pk)
    assessment = getattr(app, 'credit_assessment', None)
    context = {
        'app': app,
        'assessment': assessment,
        'assess_form': CreditAssessmentForm(instance=assessment),
        'required_authority': authority_label(app.requested_amount),
        'can_assess': _has(request, PERM_ASSESS),
        'can_approve': _has(request, PERM_APPROVE) or can_approve(request.user),
        'is_maker': app.loan_officer_id == request.user.id,
    }
    return render(request, 'pages/loan_detail.html', context)


@login_required
def loan_assess(request, pk):
    app = get_object_or_404(LoanApplication, pk=pk)
    if not _has(request, PERM_ASSESS):
        messages.error(request, 'You do not have permission to perform credit assessment.')
        return redirect('loans_page')
    if request.method == 'POST':
        form = CreditAssessmentForm(request.POST)
        if form.is_valid():
            assessment = form.save(commit=False)
            assessment.application = app
            assessment.credit_officer = request.user
            assessment.disposable_income = (assessment.verified_income - assessment.verified_expenses
                                            - assessment.existing_obligations)
            compute_and_store(assessment)
            assessment.save()
            if assessment.recommendation == CreditAssessment.RECOMMEND_REJECT:
                app.status = LoanApplication.STATUS_REJECTED
                app.rejection_reason = assessment.overall_notes or 'Rejected by credit assessment'
            elif assessment.recommendation in (CreditAssessment.RECOMMEND_APPROVE,
                                               CreditAssessment.RECOMMEND_CONDITIONAL):
                app.status = LoanApplication.STATUS_RECOMMENDED
            app.save(update_fields=['status', 'rejection_reason', 'updated_at'])
            audit(request.user, 'CREDIT_ASSESSED', assessment, branch=app.branch,
                  new={'score': assessment.credit_score, 'recommendation': assessment.recommendation},
                  request=request)
            messages.success(request, f'Credit assessment saved (score {assessment.credit_score}).')
            return redirect('loans_page')
        messages.error(request, 'Please correct the errors below.')
    return redirect('loan_application_detail', pk=app.pk)


@login_required
def loan_approve(request, pk):
    app = get_object_or_404(LoanApplication, pk=pk)
    amount = request.POST.get('amount') or app.requested_amount
    comments = request.POST.get('comments', '')
    try:
        loan_services.approve_application(app, request.user, amount, comments)
        messages.success(request, f'Application {app.application_number} approved.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('loans_page')


@login_required
def loan_reject(request, pk):
    app = get_object_or_404(LoanApplication, pk=pk)
    reason = request.POST.get('reason', '')
    try:
        loan_services.reject_application(app, request.user, reason)
        messages.success(request, f'Application {app.application_number} rejected.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('loans_page')


@login_required
def loan_disburse(request, pk):
    app = get_object_or_404(LoanApplication, pk=pk)
    method = request.POST.get('method', 'CASH')
    try:
        loan_services.disburse_loan(app, request.user, method=method)
        messages.success(request, f'Loan disbursed for {app.customer.full_name}.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('loans_page')


@login_required
def loan_repay(request, pk):
    loan = get_object_or_404(Loan, pk=pk)
    amount = request.POST.get('amount')
    method = request.POST.get('method', 'CASH')
    reference = request.POST.get('external_reference', '')
    if not amount:
        messages.error(request, 'Payment amount is required.')
        return redirect('loans_page')
    try:
        repayment_services.receive_repayment(
            loan, request.user, amount, method=method, external_reference=reference,
            teller=request.user if 'Teller' in role_names_for(request.user) else None,
        )
        messages.success(request, 'Repayment recorded.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('loans_page')


@login_required
def repayment_reverse(request, pk):
    repayment = get_object_or_404(Repayment, pk=pk)
    reason = request.POST.get('reason', '')
    if not request.user.is_superuser and not request.user.has_perm('repayments.reverse_repayment'):
        messages.error(request, 'You do not have permission to reverse repayments.')
        return redirect('loans_page')
    try:
        repayment_services.reverse_repayment(repayment, request.user, reason)
        messages.success(request, 'Repayment reversed.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('loans_page')
