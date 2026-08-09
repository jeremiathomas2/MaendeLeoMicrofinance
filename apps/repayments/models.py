from django.db import models
from decimal import Decimal

from apps.common.models import TimeStampedModel


class Repayment(TimeStampedModel):
    METHOD_CASH = 'CASH'
    METHOD_BANK = 'BANK'
    METHOD_MOBILE = 'MOBILE'
    METHOD_CHOICES = [
        (METHOD_CASH, 'Cash'),
        (METHOD_BANK, 'Bank transfer'),
        (METHOD_MOBILE, 'Mobile money'),
    ]

    STATUS_POSTED = 'POSTED'
    STATUS_REVERSED = 'REVERSED'
    STATUS_CHOICES = [
        (STATUS_POSTED, 'Posted'),
        (STATUS_REVERSED, 'Reversed'),
    ]

    receipt_number = models.CharField(max_length=30, unique=True)
    loan = models.ForeignKey('loans.Loan', on_delete=models.PROTECT, related_name='repayments')
    customer = models.ForeignKey('customers.Customer', on_delete=models.PROTECT, related_name='repayments')
    branch = models.ForeignKey('organization.Branch', on_delete=models.PROTECT, related_name='repayments')
    teller = models.ForeignKey(
        'accounts.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='teller_repayments',
    )
    created_by = models.ForeignKey(
        'accounts.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='created_repayments',
    )
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    penalty_allocated = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    fees_allocated = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    interest_allocated = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    principal_allocated = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    excess_amount = models.DecimalField(max_digits=16, decimal_places=2, default=0,
                                        help_text='Overpayment held as customer credit')
    payment_method = models.CharField(max_length=10, choices=METHOD_CHOICES, default=METHOD_CASH)
    payment_date = models.DateField()
    external_reference = models.CharField(max_length=60, blank=True)
    notes = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_POSTED)
    reversed = models.BooleanField(default=False)
    reversal_of = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='reversal_records')
    reversed_by = models.ForeignKey(
        'accounts.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='reversed_repayments',
    )
    reversed_at = models.DateTimeField(null=True, blank=True)
    reversal_reason = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ['-payment_date', '-id']

    def __str__(self):
        return self.receipt_number

    @property
    def allocation_label(self):
        parts = []
        if self.penalty_allocated:
            parts.append('Penalty')
        if self.fees_allocated:
            parts.append('Fees')
        if self.interest_allocated:
            parts.append('Interest')
        if self.principal_allocated:
            parts.append('Principal')
        return ' → '.join(parts) if parts else '—'

    @property
    def allocation_summary(self):
        order = []
        if self.penalty_allocated:
            order.append(f'Penalty {self.penalty_allocated:,.0f}')
        if self.fees_allocated:
            order.append(f'Fees {self.fees_allocated:,.0f}')
        if self.interest_allocated:
            order.append(f'Interest {self.interest_allocated:,.0f}')
        if self.principal_allocated:
            order.append(f'Principal {self.principal_allocated:,.0f}')
        return ' → '.join(order) if order else '—'


class PaymentAllocationConfig(TimeStampedModel):
    """Configurable allocation order (SRS section 28)."""

    ORDER_DEFAULT = 'penalty,fees,interest,principal'
    order = models.CharField(max_length=200, default=ORDER_DEFAULT)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = 'Payment allocation configurations'

    def __str__(self):
        return f'Allocation order: {self.order}'

    @property
    def steps(self):
        return [s.strip() for s in self.order.split(',') if s.strip()]
