from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal

from apps.common.models import TimeStampedModel, SoftDeleteMixin


class LoanProduct(TimeStampedModel, SoftDeleteMixin):
    INTEREST_FLAT = 'FLAT'
    INTEREST_REDUCING = 'REDUCING_BALANCE'
    INTEREST_DECLINING = 'DECLINING'
    INTEREST_CHOICES = [
        (INTEREST_FLAT, 'Flat rate'),
        (INTEREST_REDUCING, 'Reducing balance'),
        (INTEREST_DECLINING, 'Declining balance'),
    ]

    FREQUENCY_DAILY = 'DAILY'
    FREQUENCY_WEEKLY = 'WEEKLY'
    FREQUENCY_BIWEEKLY = 'BIWEEKLY'
    FREQUENCY_MONTHLY = 'MONTHLY'
    FREQUENCY_QUARTERLY = 'QUARTERLY'
    FREQUENCY_CHOICES = [
        (FREQUENCY_DAILY, 'Daily'),
        (FREQUENCY_WEEKLY, 'Weekly'),
        (FREQUENCY_BIWEEKLY, 'Bi-weekly'),
        (FREQUENCY_MONTHLY, 'Monthly'),
        (FREQUENCY_QUARTERLY, 'Quarterly'),
    ]

    STATUS_ACTIVE = 'ACTIVE'
    STATUS_INACTIVE = 'INACTIVE'
    STATUS_CHOICES = [(STATUS_ACTIVE, 'Active'), (STATUS_INACTIVE, 'Inactive')]

    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=120)
    min_amount = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    max_amount = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal('9999999999.99'))
    interest_rate = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('10.00'),
                                        help_text='% per period')
    interest_method = models.CharField(max_length=20, choices=INTEREST_CHOICES, default=INTEREST_FLAT)
    repayment_frequency = models.CharField(max_length=12, choices=FREQUENCY_CHOICES, default=FREQUENCY_MONTHLY)
    max_term_months = models.IntegerField(default=12)
    grace_period_days = models.IntegerField(default=0)
    processing_fee = models.DecimalField(max_digits=6, decimal_places=2, default=0, help_text='% of principal')
    insurance_fee = models.DecimalField(max_digits=6, decimal_places=2, default=0, help_text='% of principal')
    penalty_rate = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('1.00'),
                                       help_text='% of overdue amount per day')
    collateral_required = models.BooleanField(default=False)
    guarantor_required = models.BooleanField(default=False)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class LoanApplication(TimeStampedModel):
    STATUS_DRAFT = 'DRAFT'
    STATUS_SUBMITTED = 'SUBMITTED'
    STATUS_UNDER_REVIEW = 'UNDER_REVIEW'
    STATUS_CREDIT_ASSESSMENT = 'CREDIT_ASSESSMENT'
    STATUS_RECOMMENDED = 'RECOMMENDED'
    STATUS_APPROVED = 'APPROVED'
    STATUS_REJECTED = 'REJECTED'
    STATUS_READY_FOR_DISBURSEMENT = 'READY_FOR_DISBURSEMENT'
    STATUS_DISBURSED = 'DISBURSED'
    STATUS_CANCELLED = 'CANCELLED'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_SUBMITTED, 'Submitted'),
        (STATUS_UNDER_REVIEW, 'Under review'),
        (STATUS_CREDIT_ASSESSMENT, 'Credit assessment'),
        (STATUS_RECOMMENDED, 'Recommended'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_READY_FOR_DISBURSEMENT, 'Ready for disbursement'),
        (STATUS_DISBURSED, 'Disbursed'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    application_number = models.CharField(max_length=30, unique=True)
    customer = models.ForeignKey('customers.Customer', on_delete=models.PROTECT, related_name='loan_applications')
    branch = models.ForeignKey('organization.Branch', on_delete=models.PROTECT, related_name='loan_applications')
    loan_officer = models.ForeignKey(
        'accounts.User', on_delete=models.PROTECT, related_name='loan_applications',
    )
    product = models.ForeignKey(LoanProduct, on_delete=models.PROTECT, related_name='applications')
    requested_amount = models.DecimalField(max_digits=16, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    requested_term_months = models.IntegerField(default=12)
    purpose = models.CharField(max_length=255, blank=True)
    proposed_installment = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True)
    submitted_date = models.DateTimeField(null=True, blank=True)
    approved_amount = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    approved_term_months = models.IntegerField(null=True, blank=True)
    approval_authority = models.CharField(max_length=60, blank=True, help_text='Role that approved')
    approved_by = models.ForeignKey(
        'accounts.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='approved_applications',
    )
    approved_date = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.application_number} ({self.customer.full_name})'

    @property
    def required_authority(self):
        from apps.workflows.services import required_approval_role
        return required_approval_role(self.requested_amount)


class LoanApproval(TimeStampedModel):
    DECISION_APPROVED = 'APPROVED'
    DECISION_REJECTED = 'REJECTED'
    DECISION_CHOICES = [
        (DECISION_APPROVED, 'Approved'),
        (DECISION_REJECTED, 'Rejected'),
    ]

    application = models.ForeignKey(LoanApplication, on_delete=models.CASCADE, related_name='approvals')
    approver = models.ForeignKey(
        'accounts.User', on_delete=models.PROTECT, related_name='loan_approvals',
    )
    authority_level = models.CharField(max_length=60, blank=True)
    decision = models.CharField(max_length=12, choices=DECISION_CHOICES)
    amount_approved = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    comments = models.TextField(blank=True)
    decided_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-decided_at']

    def __str__(self):
        return f'{self.application} - {self.decision}'


class Loan(TimeStampedModel):
    STATUS_DISBURSED = 'DISBURSED'
    STATUS_ACTIVE = 'ACTIVE'
    STATUS_OVERDUE = 'OVERDUE'
    STATUS_PAR = 'PAR'
    STATUS_DEFAULT = 'DEFAULT'
    STATUS_RESTRUCTURED = 'RESTRUCTURED'
    STATUS_WRITTEN_OFF = 'WRITTEN_OFF'
    STATUS_CLOSED = 'CLOSED'
    STATUS_CANCELLED = 'CANCELLED'
    STATUS_CHOICES = [
        (STATUS_DISBURSED, 'Disbursed'),
        (STATUS_ACTIVE, 'Active'),
        (STATUS_OVERDUE, 'Overdue'),
        (STATUS_PAR, 'PAR'),
        (STATUS_DEFAULT, 'Default'),
        (STATUS_RESTRUCTURED, 'Restructured'),
        (STATUS_WRITTEN_OFF, 'Written off'),
        (STATUS_CLOSED, 'Closed'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    DISBURSEMENT_CASH = 'CASH'
    DISBURSEMENT_BANK = 'BANK_TRANSFER'
    DISBURSEMENT_MOBILE = 'MOBILE_MONEY'
    DISBURSEMENT_ACCOUNT = 'CUSTOMER_ACCOUNT'
    DISBURSEMENT_CHOICES = [
        (DISBURSEMENT_CASH, 'Cash'),
        (DISBURSEMENT_BANK, 'Bank transfer'),
        (DISBURSEMENT_MOBILE, 'Mobile money'),
        (DISBURSEMENT_ACCOUNT, 'Customer account'),
    ]

    loan_number = models.CharField(max_length=30, unique=True)
    application = models.OneToOneField(
        LoanApplication, null=True, blank=True, on_delete=models.SET_NULL, related_name='loan',
    )
    customer = models.ForeignKey('customers.Customer', on_delete=models.PROTECT, related_name='loans')
    product = models.ForeignKey(LoanProduct, on_delete=models.PROTECT, related_name='loans')
    branch = models.ForeignKey('organization.Branch', on_delete=models.PROTECT, related_name='loans')
    loan_officer = models.ForeignKey(
        'accounts.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='managed_loans',
    )
    principal = models.DecimalField(max_digits=16, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=6, decimal_places=2)
    interest_method = models.CharField(max_length=20, choices=LoanProduct.INTEREST_CHOICES)
    term_months = models.IntegerField(default=12)
    repayment_frequency = models.CharField(max_length=12, choices=LoanProduct.FREQUENCY_CHOICES, default='MONTHLY')
    grace_period_days = models.IntegerField(default=0)
    processing_fee = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    insurance_fee = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    penalty_rate = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    disbursement_date = models.DateField(null=True, blank=True)
    disbursed_by = models.ForeignKey(
        'accounts.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='disbursed_loans',
    )
    disbursement_method = models.CharField(max_length=20, choices=DISBURSEMENT_CHOICES, default=DISBURSEMENT_CASH)
    outstanding_principal = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    outstanding_interest = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    outstanding_fees = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    outstanding_penalties = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=STATUS_DISBURSED, db_index=True)
    write_off_date = models.DateField(null=True, blank=True)
    write_off_reason = models.TextField(blank=True)
    written_off_by = models.ForeignKey(
        'accounts.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='written_off_loans',
    )
    closed_date = models.DateField(null=True, blank=True)
    first_installment_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.loan_number

    @property
    def total_outstanding(self):
        return (self.outstanding_principal + self.outstanding_interest +
                self.outstanding_fees + self.outstanding_penalties)

    @property
    def next_due_date(self):
        inst = self.installments.filter(status__in=['PENDING', 'PARTIAL']).order_by('due_date').first()
        return inst.due_date if inst else None

    @property
    def days_overdue(self):
        inst = self.installments.filter(status__in=['PENDING', 'PARTIAL']).order_by('due_date').first()
        if not inst:
            return 0
        from apps.common.utils import days_overdue as _d
        return _d(inst.due_date)

    @property
    def installment_count(self):
        return self.installments.count()

    @property
    def paid_installments(self):
        return self.installments.filter(status='PAID').count()


class LoanInstallment(TimeStampedModel):
    STATUS_PENDING = 'PENDING'
    STATUS_PARTIAL = 'PARTIAL'
    STATUS_PAID = 'PAID'
    STATUS_OVERDUE = 'OVERDUE'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_PARTIAL, 'Partial'),
        (STATUS_PAID, 'Paid'),
        (STATUS_OVERDUE, 'Overdue'),
    ]

    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='installments')
    installment_number = models.IntegerField()
    due_date = models.DateField(db_index=True)
    principal_due = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    interest_due = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    fees_due = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    total_due = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    principal_paid = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    interest_paid = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    fees_paid = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    penalty_paid = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    total_paid = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    outstanding = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)

    class Meta:
        ordering = ['due_date', 'installment_number']
        unique_together = ('loan', 'installment_number')

    def __str__(self):
        return f'{self.loan} - Installment {self.installment_number}'

    @property
    def is_past_due(self):
        from django.utils import timezone
        return self.due_date < timezone.now().date() and self.status in ('PENDING', 'PARTIAL')


class Collateral(TimeStampedModel):
    STATUS_REGISTERED = 'REGISTERED'
    STATUS_VERIFIED = 'VERIFIED'
    STATUS_RELEASED = 'RELEASED'
    STATUS_CHOICES = [
        (STATUS_REGISTERED, 'Registered'),
        (STATUS_VERIFIED, 'Verified'),
        (STATUS_RELEASED, 'Released'),
    ]

    TYPE_LAND = 'LAND'
    TYPE_VEHICLE = 'VEHICLE'
    TYPE_GOODS = 'GOODS'
    TYPE_EQUIPMENT = 'EQUIPMENT'
    TYPE_SAVINGS = 'SAVINGS'
    TYPE_OTHER = 'OTHER'
    TYPE_CHOICES = [
        (TYPE_LAND, 'Land/title'),
        (TYPE_VEHICLE, 'Vehicle'),
        (TYPE_GOODS, 'Business goods'),
        (TYPE_EQUIPMENT, 'Equipment'),
        (TYPE_SAVINGS, 'Savings lien'),
        (TYPE_OTHER, 'Other'),
    ]

    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='collaterals', null=True, blank=True)
    customer = models.ForeignKey('customers.Customer', on_delete=models.PROTECT, related_name='collaterals')
    collateral_type = models.CharField(max_length=15, choices=TYPE_CHOICES)
    description = models.TextField(blank=True)
    owner_name = models.CharField(max_length=200, blank=True)
    location = models.CharField(max_length=255, blank=True)
    estimated_value = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    verified_value = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    valuation_date = models.DateField(null=True, blank=True)
    verification_status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=STATUS_REGISTERED)
    verified_by = models.ForeignKey(
        'accounts.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='verified_collaterals',
    )
    document = models.ForeignKey(
        'customers.CustomerDocument', null=True, blank=True, on_delete=models.SET_NULL, related_name='collaterals',
    )

    def __str__(self):
        return f'{self.get_collateral_type_display()} - {self.customer}'


class Guarantor(TimeStampedModel):
    STATUS_REGISTERED = 'REGISTERED'
    STATUS_VERIFIED = 'VERIFIED'
    STATUS_RELEASED = 'RELEASED'
    STATUS_CHOICES = [
        (STATUS_REGISTERED, 'Registered'),
        (STATUS_VERIFIED, 'Verified'),
        (STATUS_RELEASED, 'Released'),
    ]

    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='guarantors', null=True, blank=True)
    customer = models.ForeignKey('customers.Customer', on_delete=models.PROTECT, related_name='guarantees', null=True, blank=True)
    name = models.CharField(max_length=200)
    relationship = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    national_id = models.CharField(max_length=60, blank=True)
    guarantee_amount = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    consent_received = models.BooleanField(default=False)
    consent_document = models.ForeignKey(
        'customers.CustomerDocument', null=True, blank=True, on_delete=models.SET_NULL, related_name='guarantor_consents',
    )
    verification_status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=STATUS_REGISTERED)
    verified_by = models.ForeignKey(
        'accounts.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='verified_guarantors',
    )

    def __str__(self):
        return self.name
