from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal

from apps.common.models import TimeStampedModel, SoftDeleteMixin


class Customer(TimeStampedModel, SoftDeleteMixin):
    GENDER_MALE = 'MALE'
    GENDER_FEMALE = 'FEMALE'
    GENDER_OTHER = 'OTHER'
    GENDER_CHOICES = [
        (GENDER_MALE, 'Male'),
        (GENDER_FEMALE, 'Female'),
        (GENDER_OTHER, 'Other'),
    ]

    MARITAL_SINGLE = 'SINGLE'
    MARITAL_MARRIED = 'MARRIED'
    MARITAL_DIVORCED = 'DIVORCED'
    MARITAL_WIDOWED = 'WIDOWED'
    MARITAL_CHOICES = [
        (MARITAL_SINGLE, 'Single'),
        (MARITAL_MARRIED, 'Married'),
        (MARITAL_DIVORCED, 'Divorced'),
        (MARITAL_WIDOWED, 'Widowed'),
    ]

    STATUS_ACTIVE = 'ACTIVE'
    STATUS_INACTIVE = 'INACTIVE'
    STATUS_DORMANT = 'DORMANT'
    STATUS_BLACKLISTED = 'BLACKLISTED'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_INACTIVE, 'Inactive'),
        (STATUS_DORMANT, 'Dormant'),
        (STATUS_BLACKLISTED, 'Blacklisted'),
    ]

    RISK_LOW = 'LOW'
    RISK_MEDIUM = 'MEDIUM'
    RISK_HIGH = 'HIGH'
    RISK_CRITICAL = 'CRITICAL'
    RISK_CHOICES = [
        (RISK_LOW, 'Low'),
        (RISK_MEDIUM, 'Medium'),
        (RISK_HIGH, 'High'),
        (RISK_CRITICAL, 'Critical'),
    ]

    customer_number = models.CharField(max_length=30, unique=True)
    full_name = models.CharField(max_length=200)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    date_of_birth = models.DateField(null=True, blank=True)
    national_id = models.CharField(max_length=60, blank=True, unique=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    marital_status = models.CharField(max_length=12, choices=MARITAL_CHOICES, default=MARITAL_SINGLE)
    address = models.TextField(blank=True)
    occupation = models.CharField(max_length=120, blank=True)
    employer = models.CharField(max_length=200, blank=True, help_text='Employer or business name')
    photo = models.ImageField(upload_to='customers/', blank=True, null=True)

    monthly_income = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    other_income = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    monthly_expenses = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    existing_debts = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    bank_name = models.CharField(max_length=120, blank=True)
    bank_account_number = models.CharField(max_length=60, blank=True)

    branch = models.ForeignKey('organization.Branch', on_delete=models.PROTECT, related_name='customers')
    registered_by = models.ForeignKey(
        'accounts.User', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='registered_customers',
    )
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    risk_rating = models.CharField(max_length=10, choices=RISK_CHOICES, default=RISK_LOW)
    credit_score = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0)])
    kyc_complete = models.BooleanField(default=False)
    kyc_verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['full_name']
        permissions = [
            ('register_customer', 'Can register customers'),
            ('verify_customer_kyc', 'Can verify customer KYC'),
        ]

    def __str__(self):
        return f'{self.customer_number} - {self.full_name}'

    @property
    def disposable_income(self):
        return self.monthly_income + self.other_income - self.monthly_expenses

    @property
    def outstanding_balance(self):
        from apps.loans.models import Loan
        return sum(Loan.objects.filter(customer=self, status__in=['ACTIVE', 'OVERDUE', 'PAR', 'DEFAULT'])
                   .values_list('outstanding_principal', flat=True)) or 0

    @property
    def initials(self):
        parts = [p for p in self.full_name.split() if p]
        if not parts:
            return '?'
        if len(parts) == 1:
            return parts[0][:2].upper()
        return (parts[0][0] + parts[-1][0]).upper()


class CustomerGroup(TimeStampedModel, SoftDeleteMixin):
    STATUS_ACTIVE = 'ACTIVE'
    STATUS_INACTIVE = 'INACTIVE'
    STATUS_DORMANT = 'DORMANT'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_INACTIVE, 'Inactive'),
        (STATUS_DORMANT, 'Dormant'),
    ]

    MEETING_WEEKLY = 'WEEKLY'
    MEETING_BIWEEKLY = 'BIWEEKLY'
    MEETING_MONTHLY = 'MONTHLY'
    MEETING_CHOICES = [
        (MEETING_WEEKLY, 'Weekly'),
        (MEETING_BIWEEKLY, 'Bi-weekly'),
        (MEETING_MONTHLY, 'Monthly'),
    ]

    group_number = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=200)
    branch = models.ForeignKey('organization.Branch', on_delete=models.PROTECT, related_name='customer_groups')
    formation_date = models.DateField(null=True, blank=True)
    leader = models.ForeignKey(
        Customer, null=True, blank=True, on_delete=models.SET_NULL, related_name='led_groups',
    )
    meeting_location = models.CharField(max_length=255, blank=True)
    meeting_frequency = models.CharField(max_length=12, choices=MEETING_CHOICES, default=MEETING_WEEKLY)
    meeting_day = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    created_by = models.ForeignKey(
        'accounts.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='created_groups',
    )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def member_count(self):
        return self.members.count()


class GroupMember(TimeStampedModel):
    ROLE_LEADER = 'LEADER'
    ROLE_SECRETARY = 'SECRETARY'
    ROLE_MEMBER = 'MEMBER'
    ROLE_CHOICES = [
        (ROLE_LEADER, 'Leader'),
        (ROLE_SECRETARY, 'Secretary'),
        (ROLE_MEMBER, 'Member'),
    ]

    group = models.ForeignKey(CustomerGroup, on_delete=models.CASCADE, related_name='members')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='group_memberships')
    role = models.CharField(max_length=12, choices=ROLE_CHOICES, default=ROLE_MEMBER)
    joined_on = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('group', 'customer')

    def __str__(self):
        return f'{self.customer} in {self.group}'


class CustomerDocument(TimeStampedModel):
    TYPE_NATIONAL_ID = 'NATIONAL_ID'
    TYPE_PASSPORT = 'PASSPORT'
    TYPE_PHOTO = 'PHOTO'
    TYPE_BUSINESS_LICENSE = 'BUSINESS_LICENSE'
    TYPE_BANK_STATEMENT = 'BANK_STATEMENT'
    TYPE_SALARY_SLIP = 'SALARY_SLIP'
    TYPE_COLLATERAL = 'COLLATERAL'
    TYPE_GUARANTOR = 'GUARANTOR'
    TYPE_AGREEMENT = 'AGREEMENT'
    TYPE_OTHER = 'OTHER'
    TYPE_CHOICES = [
        (TYPE_NATIONAL_ID, 'National ID'),
        (TYPE_PASSPORT, 'Passport'),
        (TYPE_PHOTO, 'Passport photograph'),
        (TYPE_BUSINESS_LICENSE, 'Business license'),
        (TYPE_BANK_STATEMENT, 'Bank statement'),
        (TYPE_SALARY_SLIP, 'Salary slip'),
        (TYPE_COLLATERAL, 'Collateral document'),
        (TYPE_GUARANTOR, 'Guarantor document'),
        (TYPE_AGREEMENT, 'Signed agreement'),
        (TYPE_OTHER, 'Other'),
    ]

    STATUS_PENDING = 'PENDING'
    STATUS_VERIFIED = 'VERIFIED'
    STATUS_REJECTED = 'REJECTED'
    STATUS_UNDER_REVIEW = 'UNDER_REVIEW'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_VERIFIED, 'Verified'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_UNDER_REVIEW, 'Under review'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    file = models.FileField(upload_to='documents/')
    uploaded_by = models.ForeignKey(
        'accounts.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='uploaded_documents',
    )
    upload_date = models.DateTimeField(auto_now_add=True)
    verification_status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=STATUS_PENDING)
    verification_date = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        'accounts.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='verified_documents',
    )
    notes = models.TextField(blank=True)
    version = models.IntegerField(default=1)

    class Meta:
        ordering = ['-upload_date']

    def __str__(self):
        return f'{self.customer} - {self.get_document_type_display()}'
