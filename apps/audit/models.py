from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models

from apps.common.models import TimeStampedModel

ACTION_CHOICES = [
    ('LOGIN', 'Login'),
    ('LOGOUT', 'Logout'),
    ('USER_CREATED', 'User created'),
    ('USER_UPDATED', 'User updated'),
    ('PERMISSION_CHANGED', 'Permission changed'),
    ('CUSTOMER_CREATED', 'Customer created'),
    ('CUSTOMER_UPDATED', 'Customer updated'),
    ('CUSTOMER_DOCUMENT_VERIFIED', 'Customer document verified'),
    ('GROUP_CREATED', 'Group created'),
    ('LOAN_APPLICATION_CREATED', 'Loan application created'),
    ('LOAN_APPLICATION_SUBMITTED', 'Loan application submitted'),
    ('LOAN_APPLICATION_UPDATED', 'Loan application updated'),
    ('CREDIT_ASSESSED', 'Credit assessment performed'),
    ('LOAN_RECOMMENDED', 'Loan recommended'),
    ('LOAN_APPROVED', 'Loan approved'),
    ('LOAN_REJECTED', 'Loan rejected'),
    ('LOAN_DISBURSED', 'Loan disbursed'),
    ('LOAN_RESTRUCTURED', 'Loan restructured'),
    ('LOAN_WRITTEN_OFF', 'Loan written off'),
    ('REPAYMENT_CREATED', 'Repayment created'),
    ('REPAYMENT_REVERSED', 'Repayment reversed'),
    ('SAVINGS_DEPOSIT', 'Savings deposit'),
    ('SAVINGS_WITHDRAWAL', 'Savings withdrawal'),
    ('TELLER_OPENED', 'Teller session opened'),
    ('TELLER_CLOSED', 'Teller session closed'),
    ('CASH_ADJUSTED', 'Cash adjusted'),
    ('JOURNAL_CREATED', 'Journal entry created'),
    ('JOURNAL_APPROVED', 'Journal entry approved'),
    ('JOURNAL_POSTED', 'Journal entry posted'),
    ('EXPENSE_CREATED', 'Expense created'),
    ('SETTING_CHANGED', 'System setting changed'),
    ('DATA_EXPORTED', 'Data exported'),
    ('SYSTEM_EVENT', 'System event'),
]

ALL_ACTIONS = [c[0] for c in ACTION_CHOICES]


class AuditLog(TimeStampedModel):
    user = models.ForeignKey(
        'accounts.User', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='audit_logs',
    )
    action = models.CharField(max_length=40, choices=ACTION_CHOICES, db_index=True)
    object_type = models.CharField(max_length=120, blank=True)
    object_id = models.CharField(max_length=40, blank=True)
    object_repr = models.CharField(max_length=255, blank=True)
    branch = models.ForeignKey(
        'organization.Branch', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='audit_logs',
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    previous_value = models.JSONField(default=dict, blank=True, encoder=DjangoJSONEncoder)
    new_value = models.JSONField(default=dict, blank=True, encoder=DjangoJSONEncoder)
    reason = models.CharField(max_length=500, blank=True)
    reference = models.CharField(max_length=40, blank=True, help_text='Request/reference ID')
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = 'Audit logs'

    def __str__(self):
        who = self.user.get_full_name() if self.user else 'System'
        return f'{self.timestamp:%Y-%m-%d %H:%M} {who} {self.action} {self.object_repr}'


def audit(user, action, obj=None, branch=None, previous=None, new=None,
          reason='', reference='', request=None):
    """Create an audit record. All sensitive operations should call this."""
    ip = None
    if request is not None:
        ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR'))
        if ip and ',' in ip:
            ip = ip.split(',')[0].strip()

    if obj is not None:
        object_type = obj.__class__.__name__
        object_id = str(obj.pk)
        object_repr = str(obj)[:255]
        if branch is None and hasattr(obj, 'branch_id') and obj.branch_id:
            branch = obj.branch
    else:
        object_type = ''
        object_id = ''
        object_repr = ''

    return AuditLog.objects.create(
        user=user if user and user.is_authenticated else None,
        action=action,
        object_type=object_type,
        object_id=object_id,
        object_repr=object_repr,
        branch=branch,
        ip_address=ip,
        previous_value=previous or {},
        new_value=new or {},
        reason=reason,
        reference=reference,
    )
