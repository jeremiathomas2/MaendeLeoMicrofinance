from rest_framework import serializers

from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.customers.models import Customer, CustomerGroup
from apps.loans.models import Loan, LoanApplication, LoanInstallment, LoanProduct
from apps.organization.models import Branch
from apps.repayments.models import Repayment
from apps.savings.models import SavingsAccount, SavingsTransaction


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = ['id', 'code', 'name', 'region', 'status']


class UserSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source='role_name', read_only=True)
    branches = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'phone',
                  'employee_number', 'role', 'branches', 'is_active']

    def get_branches(self, obj):
        return [b.name for b in obj.accessible_branches()]


class CustomerSerializer(serializers.ModelSerializer):
    branch = BranchSerializer(read_only=True)

    class Meta:
        model = Customer
        fields = ['id', 'customer_number', 'full_name', 'gender', 'phone', 'email',
                  'branch', 'status', 'risk_rating', 'credit_score', 'monthly_income',
                  'monthly_expenses', 'kyc_complete']


class GroupSerializer(serializers.ModelSerializer):
    branch = BranchSerializer(read_only=True)
    member_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = CustomerGroup
        fields = ['id', 'group_number', 'name', 'branch', 'status', 'member_count']


class LoanProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanProduct
        fields = ['id', 'code', 'name', 'min_amount', 'max_amount', 'interest_rate',
                  'interest_method', 'repayment_frequency', 'status']


class LoanApplicationSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer(read_only=True)
    product = LoanProductSerializer(read_only=True)
    branch = BranchSerializer(read_only=True)
    required_authority = serializers.CharField(read_only=True)

    class Meta:
        model = LoanApplication
        fields = ['id', 'application_number', 'customer', 'product', 'branch',
                  'requested_amount', 'requested_term_months', 'status',
                  'required_authority', 'created_at']


class LoanSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer(read_only=True)
    product = LoanProductSerializer(read_only=True)
    branch = BranchSerializer(read_only=True)

    class Meta:
        model = Loan
        fields = ['id', 'loan_number', 'customer', 'product', 'branch', 'principal',
                  'outstanding_principal', 'disbursement_date', 'status']


class LoanInstallmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanInstallment
        fields = ['installment_number', 'due_date', 'principal_due', 'interest_due',
                  'total_due', 'total_paid', 'outstanding', 'status']


class RepaymentSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer(read_only=True)

    class Meta:
        model = Repayment
        fields = ['id', 'receipt_number', 'loan', 'customer', 'amount',
                  'principal_allocated', 'interest_allocated', 'payment_date', 'status']


class SavingsAccountSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer(read_only=True)

    class Meta:
        model = SavingsAccount
        fields = ['id', 'account_number', 'customer', 'balance', 'status']


class SavingsTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavingsTransaction
        fields = ['id', 'reference', 'account', 'transaction_type', 'amount', 'transaction_date']


class AuditLogSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = AuditLog
        fields = ['id', 'timestamp', 'user', 'action', 'object_repr', 'branch', 'ip_address', 'reason']
