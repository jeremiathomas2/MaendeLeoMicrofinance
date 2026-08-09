from django.db import models
from decimal import Decimal

from apps.common.models import TimeStampedModel, SoftDeleteMixin


class SavingsProduct(TimeStampedModel, SoftDeleteMixin):
    INTEREST_SIMPLE = 'SIMPLE'
    INTEREST_COMPOUND = 'COMPOUND'
    INTEREST_CHOICES = [
        (INTEREST_SIMPLE, 'Simple'),
        (INTEREST_COMPOUND, 'Compound'),
    ]

    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=120)
    minimum_balance = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    opening_fee = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    withdrawal_fee = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    interest_rate = models.DecimalField(max_digits=6, decimal_places=2, default=0, help_text='% per annum')
    interest_method = models.CharField(max_length=10, choices=INTEREST_CHOICES, default=INTEREST_SIMPLE)
    minimum_opening_deposit = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    maximum_balance = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('9999999999.99'))
    withdrawal_restrictions = models.CharField(max_length=255, blank=True, help_text='e.g. 12-month lock-in')
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class SavingsAccount(TimeStampedModel, SoftDeleteMixin):
    STATUS_ACTIVE = 'ACTIVE'
    STATUS_DORMANT = 'DORMANT'
    STATUS_CLOSED = 'CLOSED'
    STATUS_FROZEN = 'FROZEN'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_DORMANT, 'Dormant'),
        (STATUS_CLOSED, 'Closed'),
        (STATUS_FROZEN, 'Frozen'),
    ]

    account_number = models.CharField(max_length=30, unique=True)
    customer = models.ForeignKey('customers.Customer', on_delete=models.PROTECT, related_name='savings_accounts')
    product = models.ForeignKey(SavingsProduct, on_delete=models.PROTECT, related_name='accounts')
    branch = models.ForeignKey('organization.Branch', on_delete=models.PROTECT, related_name='savings_accounts')
    opening_date = models.DateField(auto_now_add=True)
    balance = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    available_balance = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    opened_by = models.ForeignKey(
        'accounts.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='opened_savings',
    )

    class Meta:
        ordering = ['account_number']

    def __str__(self):
        return f'{self.account_number} - {self.customer}'


class SavingsTransaction(TimeStampedModel):
    TYPE_DEPOSIT = 'DEPOSIT'
    TYPE_WITHDRAWAL = 'WITHDRAWAL'
    TYPE_TRANSFER = 'TRANSFER'
    TYPE_INTEREST = 'INTEREST_POSTING'
    TYPE_FEE = 'FEE'
    TYPE_ADJUSTMENT = 'ADJUSTMENT'
    TYPE_CHOICES = [
        (TYPE_DEPOSIT, 'Deposit'),
        (TYPE_WITHDRAWAL, 'Withdrawal'),
        (TYPE_TRANSFER, 'Transfer'),
        (TYPE_INTEREST, 'Interest posting'),
        (TYPE_FEE, 'Fee'),
        (TYPE_ADJUSTMENT, 'Adjustment'),
    ]

    reference = models.CharField(max_length=30, unique=True)
    account = models.ForeignKey(SavingsAccount, on_delete=models.PROTECT, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    branch = models.ForeignKey('organization.Branch', on_delete=models.PROTECT, related_name='savings_transactions')
    teller = models.ForeignKey(
        'accounts.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='savings_teller_txn',
    )
    created_by = models.ForeignKey(
        'accounts.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='savings_created_txn',
    )
    transaction_date = models.DateField(auto_now_add=True)
    description = models.CharField(max_length=255, blank=True)
    reversed = models.BooleanField(default=False)
    reversal_of = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='reversal_records')

    class Meta:
        ordering = ['-transaction_date', '-id']

    def __str__(self):
        return f'{self.reference} {self.transaction_type} {self.amount}'

    def is_inflow(self):
        return self.transaction_type in (self.TYPE_DEPOSIT, self.TYPE_INTEREST)
