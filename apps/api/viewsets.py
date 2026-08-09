from rest_framework import viewsets

from apps.accounts.models import User
from apps.accounts.services import filter_by_scope
from apps.api.serializers import (
    AuditLogSerializer, BranchSerializer, CustomerSerializer, GroupSerializer,
    LoanApplicationSerializer, LoanInstallmentSerializer, LoanProductSerializer,
    LoanSerializer, RepaymentSerializer, SavingsAccountSerializer,
    SavingsTransactionSerializer, UserSerializer,
)
from apps.audit.models import AuditLog
from apps.customers.models import Customer, CustomerGroup
from apps.loans.models import Loan, LoanApplication, LoanInstallment, LoanProduct
from apps.organization.models import Branch
from apps.repayments.models import Repayment
from apps.savings.models import SavingsAccount, SavingsTransaction


class BranchViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Branch.objects.filter(status='ACTIVE')
    serializer_class = BranchSerializer


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.filter(is_active=True)
    serializer_class = UserSerializer


class CustomerViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CustomerSerializer

    def get_queryset(self):
        return filter_by_scope(self.request.user, Customer.objects.select_related('branch'), 'branch')


class GroupViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = GroupSerializer

    def get_queryset(self):
        return filter_by_scope(self.request.user, CustomerGroup.objects.select_related('branch'), 'branch')


class LoanProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LoanProduct.objects.filter(status='ACTIVE')
    serializer_class = LoanProductSerializer


class LoanApplicationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LoanApplicationSerializer

    def get_queryset(self):
        return filter_by_scope(
            self.request.user,
            LoanApplication.objects.select_related('customer', 'product', 'branch'),
            'branch',
        ).order_by('-created_at')


class LoanViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LoanSerializer

    def get_queryset(self):
        return filter_by_scope(
            self.request.user,
            Loan.objects.select_related('customer', 'product', 'branch'),
            'branch',
        )


class LoanInstallmentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LoanInstallmentSerializer
    queryset = LoanInstallment.objects.all()


class RepaymentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = RepaymentSerializer

    def get_queryset(self):
        return filter_by_scope(
            self.request.user,
            Repayment.objects.select_related('customer', 'loan'),
            'branch',
        ).order_by('-payment_date')


class SavingsAccountViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SavingsAccountSerializer

    def get_queryset(self):
        return filter_by_scope(
            self.request.user,
            SavingsAccount.objects.select_related('customer'),
            'branch',
        )


class SavingsTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SavingsTransactionSerializer

    def get_queryset(self):
        return filter_by_scope(
            self.request.user,
            SavingsTransaction.objects.select_related('account'),
            'branch',
        ).order_by('-transaction_date')


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditLogSerializer

    def get_queryset(self):
        qs = AuditLog.objects.select_related('user', 'branch')
        if not (self.request.user.is_superuser or
                self.request.user.has_perm('organization.see_all_branches')):
            qs = qs.filter(user=self.request.user)
        return qs.order_by('-timestamp')
