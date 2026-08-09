"""Teller session services (SRS sections 37-39)."""

from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from apps.cash_management.models import TellerSession
from apps.audit.models import audit

ZERO = Decimal('0.00')


def open_session(user, branch, opening_balance):
    opening_balance = Decimal(opening_balance)
    active = TellerSession.objects.filter(
        teller=user, status__in=[TellerSession.STATUS_OPEN, TellerSession.STATUS_RECONCILING],
    ).first()
    if active:
        raise ValueError('You already have an open session')

    session = TellerSession.objects.create(
        teller=user,
        branch=branch,
        opening_balance=opening_balance,
        expected_closing=opening_balance,
    )
    audit(user, 'TELLER_OPENED', session, new={'opening': str(opening_balance)})
    return session


@transaction.atomic
def reconcile_session(session, user, actual_closing, variance_reason=''):
    actual = Decimal(actual_closing)
    expected = session.recompute_expected()
    session.actual_closing = actual
    session.variance = actual - expected
    session.variance_reason = variance_reason
    session.status = TellerSession.STATUS_RECONCILING
    session.save(update_fields=['expected_closing', 'actual_closing', 'variance',
                                'variance_reason', 'status', 'updated_at'])
    audit(user, 'TELLER_CLOSED', session,
          new={'expected': str(expected), 'actual': str(actual), 'variance': str(session.variance)},
          reason=variance_reason)
    return session


@transaction.atomic
def close_session(session, user, actual_closing=None, variance_reason=''):
    expected = session.recompute_expected()
    actual = Decimal(actual_closing) if actual_closing is not None else expected
    session.expected_closing = expected
    session.actual_closing = actual
    session.variance = actual - expected
    session.variance_reason = variance_reason
    session.status = TellerSession.STATUS_CLOSED
    session.closing_time = timezone.now()
    session.closed_by = user
    session.save(update_fields=['expected_closing', 'actual_closing', 'variance',
                                'variance_reason', 'status', 'closing_time', 'closed_by', 'updated_at'])
    audit(user, 'TELLER_CLOSED', session,
          new={'expected': str(expected), 'actual': str(actual), 'variance': str(session.variance)},
          reason=variance_reason)
    return session
