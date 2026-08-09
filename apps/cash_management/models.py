from django.db import models
from decimal import Decimal

from apps.common.models import TimeStampedModel


class TellerSession(TimeStampedModel):
    STATUS_OPEN = 'OPEN'
    STATUS_RECONCILING = 'RECONCILING'
    STATUS_CLOSED = 'CLOSED'
    STATUS_CHOICES = [
        (STATUS_OPEN, 'Open'),
        (STATUS_RECONCILING, 'Reconciling'),
        (STATUS_CLOSED, 'Closed'),
    ]

    teller = models.ForeignKey('accounts.User', on_delete=models.PROTECT, related_name='teller_sessions')
    branch = models.ForeignKey('organization.Branch', on_delete=models.PROTECT, related_name='teller_sessions')
    opening_balance = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    opening_time = models.DateTimeField(auto_now_add=True)
    closing_time = models.DateTimeField(null=True, blank=True)
    expected_closing = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    actual_closing = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    variance = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    variance_reason = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_OPEN)
    closed_by = models.ForeignKey(
        'accounts.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='closed_sessions',
    )

    class Meta:
        ordering = ['-opening_time']

    def __str__(self):
        return f'{self.teller.get_full_name()} @ {self.branch} [{self.status}]'

    @property
    def cash_in(self):
        from apps.cash_management.models import CashTransaction
        from django.db.models import Sum
        return self.transactions.filter(transaction_type__in=['DEPOSIT', 'REPAYMENT']).aggregate(s=Sum('amount'))['s'] or Decimal('0')

    @property
    def cash_out(self):
        from apps.cash_management.models import CashTransaction
        from django.db.models import Sum
        return self.transactions.filter(transaction_type__in=['WITHDRAWAL', 'DISBURSEMENT', 'EXPENSE']).aggregate(s=Sum('amount'))['s'] or Decimal('0')

    def recompute_expected(self):
        self.expected_closing = self.opening_balance + self.cash_in - self.cash_out
        return self.expected_closing


class CashTransaction(TimeStampedModel):
    TYPE_DEPOSIT = 'DEPOSIT'
    TYPE_WITHDRAWAL = 'WITHDRAWAL'
    TYPE_REPAYMENT = 'REPAYMENT'
    TYPE_DISBURSEMENT = 'DISBURSEMENT'
    TYPE_TRANSFER = 'CASH_TRANSFER'
    TYPE_ADJUSTMENT = 'ADJUSTMENT'
    TYPE_EXPENSE = 'EXPENSE'
    TYPE_CHOICES = [
        (TYPE_DEPOSIT, 'Deposit'),
        (TYPE_WITHDRAWAL, 'Withdrawal'),
        (TYPE_REPAYMENT, 'Repayment'),
        (TYPE_DISBURSEMENT, 'Disbursement'),
        (TYPE_TRANSFER, 'Cash transfer'),
        (TYPE_ADJUSTMENT, 'Cash adjustment'),
        (TYPE_EXPENSE, 'Cash expense'),
    ]

    reference = models.CharField(max_length=30, unique=True)
    transaction_type = models.CharField(max_length=15, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    branch = models.ForeignKey('organization.Branch', on_delete=models.PROTECT, related_name='cash_transactions')
    teller = models.ForeignKey(
        'accounts.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='cash_transactions',
    )
    session = models.ForeignKey(TellerSession, null=True, blank=True, on_delete=models.SET_NULL, related_name='transactions')
    customer = models.ForeignKey(
        'customers.Customer', null=True, blank=True, on_delete=models.SET_NULL, related_name='cash_transactions',
    )
    loan = models.ForeignKey(
        'loans.Loan', null=True, blank=True, on_delete=models.SET_NULL, related_name='cash_transactions',
    )
    repayment = models.ForeignKey(
        'repayments.Repayment', null=True, blank=True, on_delete=models.SET_NULL, related_name='cash_transactions',
    )
    savings_account = models.ForeignKey(
        'savings.SavingsAccount', null=True, blank=True, on_delete=models.SET_NULL, related_name='cash_transactions',
    )
    transaction_date = models.DateField()
    description = models.CharField(max_length=255, blank=True)
    approval_status = models.CharField(max_length=12, default='APPROVED')
    created_by = models.ForeignKey(
        'accounts.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='created_cash_txn',
    )

    class Meta:
        ordering = ['-transaction_date', '-id']

    def __str__(self):
        return f'{self.reference} {self.transaction_type} {self.amount}'

    def is_inflow(self):
        return self.transaction_type in (self.TYPE_DEPOSIT, self.TYPE_REPAYMENT)


class BankAccount(TimeStampedModel, ):
    ACCOUNT_OPERATING = 'OPERATING'
    ACCOUNT_DISBURSEMENT = 'DISBURSEMENT'
    ACCOUNT_RESERVE = 'RESERVE'
    ACCOUNT_SAVINGS = 'SAVINGS'
    ACCOUNT_CHOICES = [
        (ACCOUNT_OPERATING, 'Operating account'),
        (ACCOUNT_DISBURSEMENT, 'Disbursement account'),
        (ACCOUNT_RESERVE, 'Reserve account'),
        (ACCOUNT_SAVINGS, 'Savings account'),
    ]

    bank_name = models.CharField(max_length=120)
    account_name = models.CharField(max_length=200)
    account_number = models.CharField(max_length=60)
    branch = models.ForeignKey(
        'organization.Branch', null=True, blank=True, on_delete=models.SET_NULL, related_name='bank_accounts',
    )
    account_type = models.CharField(max_length=20, choices=ACCOUNT_CHOICES, default=ACCOUNT_OPERATING)
    balance = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    opened_on = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['bank_name', 'account_name']
        unique_together = ('bank_name', 'account_number')

    def __str__(self):
        return f'{self.bank_name} - {self.account_name}'


class BankTransaction(TimeStampedModel):
    TYPE_DEPOSIT = 'DEPOSIT'
    TYPE_WITHDRAWAL = 'WITHDRAWAL'
    TYPE_TRANSFER = 'TRANSFER'
    TYPE_CHARGE = 'BANK_CHARGE'
    TYPE_CHOICES = [
        (TYPE_DEPOSIT, 'Deposit'),
        (TYPE_WITHDRAWAL, 'Withdrawal'),
        (TYPE_TRANSFER, 'Transfer'),
        (TYPE_CHARGE, 'Bank charge'),
    ]

    reference = models.CharField(max_length=30, unique=True)
    bank_account = models.ForeignKey(BankAccount, on_delete=models.PROTECT, related_name='transactions')
    transaction_type = models.CharField(max_length=15, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    transaction_date = models.DateField(auto_now_add=True)
    description = models.CharField(max_length=255, blank=True)
    reconciled = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        'accounts.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='bank_txn',
    )

    class Meta:
        ordering = ['-transaction_date', '-id']

    def __str__(self):
        return f'{self.reference} {self.transaction_type} {self.amount}'
