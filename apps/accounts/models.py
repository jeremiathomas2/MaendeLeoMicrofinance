from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.common.models import TimeStampedModel


class User(AbstractUser):
    """System user with staff profile fields."""

    STATUS_ACTIVE = 'ACTIVE'
    STATUS_LOCKED = 'LOCKED'
    STATUS_DISABLED = 'DISABLED'
    STATUS_PENDING = 'PENDING'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_LOCKED, 'Locked'),
        (STATUS_DISABLED, 'Disabled'),
        (STATUS_PENDING, 'Pending'),
    ]

    phone = models.CharField(max_length=30, blank=True)
    employee_number = models.CharField(max_length=30, blank=True, unique=True)
    profile_photo = models.ImageField(upload_to='profiles/', blank=True, null=True)
    account_status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    mfa_enabled = models.BooleanField(default=False)
    must_change_password = models.BooleanField(default=False)
    last_password_change = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['first_name', 'last_name']

    def __str__(self):
        return self.get_full_name() or self.username

    @property
    def role_name(self):
        groups = self.groups.all()
        return groups[0].name if groups else 'Staff'

    @property
    def is_staff_account(self):
        return hasattr(self, 'staff_profile')

    def accessible_branches(self):
        """Return the set of Branch objects the user may access.

        * System administrators see all branches.
        * Users with ``organization.see_all_branches`` permission see all branches.
        * Otherwise the union of their primary branch and extra assignments.
        """
        from apps.organization.models import Branch

        if self.is_superuser or self.has_perm('organization.see_all_branches'):
            return Branch.objects.filter(status=Branch.STATUS_ACTIVE)

        profile = getattr(self, 'staff_profile', None)
        branch_ids = set()
        if profile and profile.primary_branch_id:
            branch_ids.add(profile.primary_branch_id)
        branch_ids |= set(
            self.branch_assignments.values_list('branch_id', flat=True)
        )
        return Branch.objects.filter(id__in=branch_ids, status=Branch.STATUS_ACTIVE)

    def can_see_branch(self, branch):
        return branch in self.accessible_branches()

    def has_role(self, name):
        return self.groups.filter(name__iexact=name).exists()


class StaffProfile(TimeStampedModel):
    EMPLOYMENT_ACTIVE = 'ACTIVE'
    EMPLOYMENT_ON_LEAVE = 'ON_LEAVE'
    EMPLOYMENT_TERMINATED = 'TERMINATED'
    EMPLOYMENT_CHOICES = [
        (EMPLOYMENT_ACTIVE, 'Active'),
        (EMPLOYMENT_ON_LEAVE, 'On leave'),
        (EMPLOYMENT_TERMINATED, 'Terminated'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='staff_profile')
    employee_number = models.CharField(max_length=30, blank=True)
    department = models.ForeignKey(
        'organization.Department', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='staff',
    )
    job_title = models.CharField(max_length=120, blank=True)
    employment_status = models.CharField(max_length=20, choices=EMPLOYMENT_CHOICES, default=EMPLOYMENT_ACTIVE)
    primary_branch = models.ForeignKey(
        'organization.Branch', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='primary_staff',
    )
    date_of_employment = models.DateField(null=True, blank=True)
    supervisor = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL, related_name='subordinates',
    )
    signature = models.ImageField(upload_to='signatures/', blank=True, null=True)
    identification_number = models.CharField(max_length=60, blank=True)

    class Meta:
        ordering = ['user__first_name', 'user__last_name']

    def __str__(self):
        return f'{self.user.get_full_name()} @ {self.primary_branch or "-"}'

    @property
    def branch_label(self):
        return self.primary_branch.name if self.primary_branch else '—'


class StaffBranchAssignment(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='branch_assignments')
    branch = models.ForeignKey('organization.Branch', on_delete=models.CASCADE, related_name='assigned_staff')
    is_primary = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'branch')

    def __str__(self):
        return f'{self.user} -> {self.branch}'
