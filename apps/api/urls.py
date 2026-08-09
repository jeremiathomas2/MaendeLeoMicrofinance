from rest_framework.routers import DefaultRouter

from apps.api.viewsets import (
    AuditLogViewSet, BranchViewSet, CustomerViewSet, GroupViewSet,
    LoanApplicationViewSet, LoanInstallmentViewSet, LoanProductViewSet,
    LoanViewSet, RepaymentViewSet, SavingsAccountViewSet,
    SavingsTransactionViewSet, UserViewSet,
)

router = DefaultRouter()
router.register('branches', BranchViewSet, basename='branch')
router.register('users', UserViewSet, basename='user')
router.register('customers', CustomerViewSet, basename='customer')
router.register('groups', GroupViewSet, basename='group')
router.register('loan-products', LoanProductViewSet, basename='loan-product')
router.register('loan-applications', LoanApplicationViewSet, basename='loan-application')
router.register('loans', LoanViewSet, basename='loan')
router.register('loan-installments', LoanInstallmentViewSet, basename='loan-installment')
router.register('repayments', RepaymentViewSet, basename='repayment')
router.register('savings-accounts', SavingsAccountViewSet, basename='savings-account')
router.register('savings-transactions', SavingsTransactionViewSet, basename='savings-transaction')
router.register('audit', AuditLogViewSet, basename='audit')

urlpatterns = router.urls
