from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ActiveQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def inactive(self):
        return self.filter(is_active=False)


class SoftDeleteMixin(models.Model):
    is_active = models.BooleanField(default=True)
    objects = ActiveQuerySet.as_manager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def deactivate(self):
        self.is_active = False
        self.save(update_fields=['is_active'])
