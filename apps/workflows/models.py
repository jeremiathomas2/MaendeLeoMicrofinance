from django.db import models
from decimal import Decimal

from apps.common.models import TimeStampedModel


class ApprovalConfig(TimeStampedModel):
    """Approval authority limits (SRS sections 23, 48).

    A request is routed to the *highest* tier whose ``max_amount`` is >= the
    requested amount. Example::

        ≤  5,000,000  -> Branch Manager
        ≤ 20,000,000  -> Head of Operations
        otherwise     -> General Manager
    """

    ROLE_BRANCH_MANAGER = 'Branch Manager'
    ROLE_HEAD_OPERATIONS = 'Head of Operations'
    ROLE_GENERAL_MANAGER = 'General Manager'
    ROLE_CHOICES = [
        (ROLE_BRANCH_MANAGER, 'Branch Manager'),
        (ROLE_HEAD_OPERATIONS, 'Head of Operations'),
        (ROLE_GENERAL_MANAGER, 'General Manager'),
    ]

    role = models.CharField(max_length=60, choices=ROLE_CHOICES, unique=True)
    min_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0'))
    max_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('99999999999.00'))
    priority = models.IntegerField(default=0, help_text='Higher number = more senior')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['priority']
        verbose_name_plural = 'Approval configurations'

    def __str__(self):
        return f'{self.role}: {self.min_amount} - {self.max_amount}'


def required_approval_role(amount):
    """Return the role name required to approve a loan of ``amount``."""
    from apps.organization.models import SystemSetting
    amount = Decimal(amount)

    configs = list(ApprovalConfig.objects.filter(is_active=True).order_by('max_amount'))
    if not configs:
        return ApprovalConfig.ROLE_BRANCH_MANAGER

    chosen = None
    for cfg in configs:
        if amount <= cfg.max_amount:
            chosen = cfg.role
            break
    if chosen is None:
        chosen = configs[-1].role if configs else ApprovalConfig.ROLE_GENERAL_MANAGER
    return chosen
