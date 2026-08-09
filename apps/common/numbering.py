"""
Concurrency-safe sequential reference numbering.

Generates references like::

    CUS-MOS-000001
    APP-DAR-2026-000001
    LOAN-MOS-2026-000001
    RCT-DAR-2026-000001
    TXN-MOS-2026-000001
    SAV-ARI-000001
    JRN-2026-000001
    GRP-DAR-000001

Counters are stored in :class:`NumberSequence` and incremented inside a
``SELECT ... FOR UPDATE`` transaction so concurrent requests never produce
duplicate numbers.
"""

from django.db import models, transaction

from apps.common.models import TimeStampedModel


class NumberSequence(TimeStampedModel):
    prefix = models.CharField(max_length=10, db_index=True)
    branch_code = models.CharField(max_length=12, blank=True, default='')
    year = models.IntegerField(null=True, blank=True)
    last_value = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('prefix', 'branch_code', 'year')
        verbose_name_plural = 'Number sequences'

    def __str__(self):
        return f'{self.prefix}-{self.branch_code}-{self.year} -> {self.last_value}'


def next_number(prefix, branch=None, include_year=True, width=6):
    """
    Return the next reference for a prefix.

    * ``branch``  -- optional Branch instance; uses its ``code``.
    * ``include_year`` -- appends the current year to the reference.
    """
    from django.utils import timezone

    branch_code = branch.code if branch else ''
    year = timezone.now().year if include_year else None

    with transaction.atomic():
        seq, created = NumberSequence.objects.select_for_update().get_or_create(
            prefix=prefix,
            branch_code=branch_code,
            year=year,
            defaults={'last_value': 0},
        )
        seq.last_value += 1
        seq.save(update_fields=['last_value', 'updated_at'])
        value = seq.last_value

    parts = [prefix]
    if branch_code:
        parts.append(branch_code)
    if year:
        parts.append(str(year))
    parts.append(str(value).zfill(width))
    return '-'.join(parts)
