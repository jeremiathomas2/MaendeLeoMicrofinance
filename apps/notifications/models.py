from django.db import models

from apps.common.models import TimeStampedModel


class Notification(TimeStampedModel):
    TYPE_INFO = 'INFO'
    TYPE_SUCCESS = 'SUCCESS'
    TYPE_WARNING = 'WARNING'
    TYPE_DANGER = 'DANGER'
    TYPE_CHOICES = [
        (TYPE_INFO, 'Info'),
        (TYPE_SUCCESS, 'Success'),
        (TYPE_WARNING, 'Warning'),
        (TYPE_DANGER, 'Danger'),
    ]

    user = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE, related_name='notifications',
    )
    title = models.CharField(max_length=200)
    message = models.TextField(blank=True)
    notification_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default=TYPE_INFO)
    is_read = models.BooleanField(default=False)
    link = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class MessageTemplate(TimeStampedModel):
    CHANNEL_EMAIL = 'EMAIL'
    CHANNEL_SMS = 'SMS'
    CHANNEL_APP = 'APP'
    CHANNEL_CHOICES = [
        (CHANNEL_EMAIL, 'Email'),
        (CHANNEL_SMS, 'SMS'),
        (CHANNEL_APP, 'In-app'),
    ]

    code = models.CharField(max_length=60, unique=True)
    name = models.CharField(max_length=200)
    channel = models.CharField(max_length=8, choices=CHANNEL_CHOICES, default=CHANNEL_APP)
    subject = models.CharField(max_length=200, blank=True)
    body = models.TextField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f'{self.name} ({self.code})'


def notify(user, title, message='', ntype=Notification.TYPE_INFO, link=''):
    return Notification.objects.create(
        user=user, title=title, message=message, notification_type=ntype, link=link,
    )
