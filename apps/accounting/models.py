from django.db import models
from decimal import Decimal

from apps.common.models import TimeStampedModel


class Account(TimeStampedModel):
    TYPE_ASSET = 'ASSET'
    TYPE_LIABILITY = 'LIABILITY'
    TYPE_EQUITY = 'EQUITY'
    TYPE_INCOME = 'INCOME'
    TYPE_EXPENSE = 'EXPENSE'
    TYPE_CHOICES = [
        (TYPE_ASSET, 'Asset'),
        (TYPE_LIABILITY, 'Liability'),
        (TYPE_EQUITY, 'Equity'),
        (TYPE_INCOME, 'Income'),
        (TYPE_EXPENSE, 'Expense'),
    ]

    code = models.CharField(max_length=12, unique=True)
    name = models.CharField(max_length=200)
    account_type = models.CharField(max_length=12, choices=TYPE_CHOICES)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='children')
    branch = models.ForeignKey(
        'organization.Branch', null=True, blank=True, on_delete=models.SET_NULL, related_name='accounts',
    )
    is_active = models.BooleanField(default=True)
    is_control = models.BooleanField(default=False)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f'{self.code} - {self.name}'

    @property
    def balance(self):
        """Net balance from all posted journal lines (debits - credits for assets/expenses)."""
        from django.db.models import Sum
        lines = self.lines.filter(entry__status=JournalEntry.STATUS_POSTED)
        debit = lines.aggregate(s=Sum('debit'))['s'] or Decimal('0')
        credit = lines.aggregate(s=Sum('credit'))['s'] or Decimal('0')
        if self.account_type in (self.TYPE_ASSET, self.TYPE_EXPENSE):
            return debit - credit
        return credit - debit


class JournalEntry(TimeStampedModel):
    STATUS_DRAFT = 'DRAFT'
    STATUS_PENDING = 'PENDING_APPROVAL'
    STATUS_POSTED = 'POSTED'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_PENDING, 'Pending approval'),
        (STATUS_POSTED, 'Posted'),
    ]

    reference = models.CharField(max_length=40, unique=True)
    entry_date = models.DateField()
    description = models.TextField(blank=True)
    branch = models.ForeignKey(
        'organization.Branch', null=True, blank=True, on_delete=models.SET_NULL, related_name='journal_entries',
    )
    source_type = models.CharField(max_length=80, blank=True, help_text='e.g. Repayment, Disbursement')
    source_reference = models.CharField(max_length=40, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    posted_by = models.ForeignKey(
        'accounts.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='posted_journals',
    )
    posted_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        'accounts.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='approved_journals',
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        'accounts.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='created_journals',
    )

    class Meta:
        ordering = ['-entry_date', '-id']

    def __str__(self):
        return self.reference

    @property
    def total_debit(self):
        from django.db.models import Sum
        return self.lines.aggregate(s=Sum('debit'))['s'] or Decimal('0')

    @property
    def total_credit(self):
        from django.db.models import Sum
        return self.lines.aggregate(s=Sum('credit'))['s'] or Decimal('0')

    @property
    def is_balanced(self):
        return self.total_debit == self.total_credit


class JournalEntryLine(models.Model):
    entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name='lines')
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='lines')
    debit = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    memo = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f'{self.account} D{self.debit} C{self.credit}'


class AccountingPeriod(TimeStampedModel):
    STATUS_OPEN = 'OPEN'
    STATUS_CLOSED = 'CLOSED'
    STATUS_CHOICES = [(STATUS_OPEN, 'Open'), (STATUS_CLOSED, 'Closed')]

    name = models.CharField(max_length=80, unique=True)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_OPEN)

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        return self.name


class Expense(TimeStampedModel):
    STATUS_DRAFT = 'DRAFT'
    STATUS_PENDING = 'PENDING'
    STATUS_APPROVED = 'APPROVED'
    STATUS_PAID = 'PAID'
    STATUS_REJECTED = 'REJECTED'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_PENDING, 'Pending approval'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_PAID, 'Paid'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    reference = models.CharField(max_length=30, unique=True)
    category = models.CharField(max_length=120, blank=True)
    vendor = models.CharField(max_length=200, blank=True)
    branch = models.ForeignKey(
        'organization.Branch', on_delete=models.PROTECT, related_name='expenses',
    )
    amount = models.DecimalField(max_digits=16, decimal_places=2, validators=[])
    expense_date = models.DateField(auto_now_add=True)
    description = models.TextField(blank=True)
    requested_by = models.ForeignKey(
        'accounts.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='requested_expenses',
    )
    approval_status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    approved_by = models.ForeignKey(
        'accounts.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='approved_expenses',
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    receipt = models.FileField(upload_to='expense_receipts/', blank=True, null=True)
    paid = models.BooleanField(default=False)

    class Meta:
        ordering = ['-expense_date']

    def __str__(self):
        return f'{self.reference} - {self.category}'
