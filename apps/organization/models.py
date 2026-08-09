from django.db import models

from apps.common.models import TimeStampedModel


class Organization(TimeStampedModel):
    name = models.CharField(max_length=200)
    registration_number = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    logo = models.ImageField(upload_to='logos/', blank=True, null=True)
    currency = models.CharField(max_length=8, default='TZS')
    timezone = models.CharField(max_length=64, default='Africa/Dar_es_Salaam')
    financial_year_start = models.IntegerField(default=1, help_text='Month (1-12) the financial year starts')
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = 'Organizations'

    def __str__(self):
        return self.name

    @classmethod
    def get(cls):
        return cls.objects.filter(is_active=True).first()


class Branch(TimeStampedModel):
    STATUS_ACTIVE = 'ACTIVE'
    STATUS_INACTIVE = 'INACTIVE'
    STATUS_CLOSED = 'CLOSED'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_INACTIVE, 'Inactive'),
        (STATUS_CLOSED, 'Closed'),
    ]

    code = models.CharField(max_length=12, unique=True)
    name = models.CharField(max_length=120)
    region = models.CharField(max_length=120, blank=True, help_text='Geographic region e.g. Northern Region')
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    manager = models.ForeignKey(
        'accounts.User', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='managed_branches', help_text='Branch manager',
    )
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    opening_date = models.DateField(null=True, blank=True)
    operating_hours = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.code})'


class Department(TimeStampedModel):
    name = models.CharField(max_length=120)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='departments', null=True, blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class SystemSetting(TimeStampedModel):
    """Key/value store for configurable business rules."""

    CATEGORY_INSTITUTION = 'INSTITUTION'
    CATEGORY_LOANS = 'LOANS'
    CATEGORY_SAVINGS = 'SAVINGS'
    CATEGORY_PENALTIES = 'PENALTIES'
    CATEGORY_APPROVAL = 'APPROVAL'
    CATEGORY_ACCOUNTING = 'ACCOUNTING'
    CATEGORY_NOTIFICATIONS = 'NOTIFICATIONS'
    CATEGORY_SECURITY = 'SECURITY'
    CATEGORY_CHOICES = [
        (CATEGORY_INSTITUTION, 'Institution'),
        (CATEGORY_LOANS, 'Loans'),
        (CATEGORY_SAVINGS, 'Savings'),
        (CATEGORY_PENALTIES, 'Penalties'),
        (CATEGORY_APPROVAL, 'Approval'),
        (CATEGORY_ACCOUNTING, 'Accounting'),
        (CATEGORY_NOTIFICATIONS, 'Notifications'),
        (CATEGORY_SECURITY, 'Security'),
    ]

    key = models.CharField(max_length=120, unique=True)
    label = models.CharField(max_length=200, blank=True)
    value = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default=CATEGORY_INSTITUTION)
    is_public = models.BooleanField(default=False)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['category', 'key']

    def __str__(self):
        return f'{self.key} = {self.value}'

    @classmethod
    def get(cls, key, default=None):
        obj = cls.objects.filter(key=key).first()
        if obj is None:
            return default
        return obj.value if obj.value != '' else default
