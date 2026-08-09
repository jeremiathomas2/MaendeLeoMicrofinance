from django.db import models

from apps.common.models import TimeStampedModel


class CollectionAction(TimeStampedModel):
    ACTION_CALL = 'PHONE_CALL'
    ACTION_SMS = 'SMS'
    ACTION_VISIT = 'VISIT'
    ACTION_REMINDER = 'REMINDER'
    ACTION_PROMISE = 'PROMISE_TO_PAY'
    ACTION_ESCALATE = 'ESCALATION'
    ACTION_CHOICES = [
        (ACTION_CALL, 'Phone call'),
        (ACTION_SMS, 'SMS'),
        (ACTION_VISIT, 'Visit'),
        (ACTION_REMINDER, 'Reminder'),
        (ACTION_PROMISE, 'Promise to pay'),
        (ACTION_ESCALATE, 'Escalation'),
    ]

    STATUS_OPEN = 'OPEN'
    STATUS_RESOLVED = 'RESOLVED'
    STATUS_CHOICES = [(STATUS_OPEN, 'Open'), (STATUS_RESOLVED, 'Resolved')]

    loan = models.ForeignKey('loans.Loan', on_delete=models.CASCADE, related_name='collection_actions')
    customer = models.ForeignKey('customers.Customer', on_delete=models.PROTECT, related_name='collection_actions')
    officer = models.ForeignKey(
        'accounts.User', on_delete=models.PROTECT, related_name='collection_actions',
    )
    action_type = models.CharField(max_length=15, choices=ACTION_CHOICES)
    date = models.DateField(auto_now_add=True)
    notes = models.TextField(blank=True)
    promised_date = models.DateField(null=True, blank=True)
    promised_amount = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_OPEN)
    follow_up_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f'{self.customer} - {self.get_action_type_display()}'
