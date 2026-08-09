from decimal import Decimal


def money(value, currency='TZS'):
    """Format a Decimal as a compact money string, e.g. TZS 8.42 Bn."""
    if value in (None, ''):
        return '—'
    try:
        v = Decimal(value)
    except (TypeError, ValueError):
        return '—'
    if currency:
        prefix = f'{currency} '
    else:
        prefix = ''
    if v == 0:
        return f'{prefix}0'
    negative = v < 0
    v = abs(v)
    if v >= 1_000_000_000:
        txt = f'{prefix}{_trim(v / 1_000_000_000)} Bn'
    elif v >= 1_000_000:
        txt = f'{prefix}{_trim(v / 1_000_000)} M'
    elif v >= 1_000:
        txt = f'{prefix}{v.quantize(Decimal("1")).to_integral_value():,}'
    else:
        txt = f'{prefix}{_trim(v)}'
    return ('−' if negative else '') + txt


def money_full(value, currency='TZS'):
    """Format a Decimal as a full comma-separated number, e.g. TZS 8,420,000,000."""
    if value in (None, ''):
        return '—'
    try:
        v = Decimal(value)
    except (TypeError, ValueError):
        return '—'
    neg = v < 0
    v = abs(v)
    whole = v.to_integral_value()
    txt = f'{currency} {whole:,}'
    return ('−' if neg else '') + txt


def _trim(v):
    v = Decimal(v)
    if v == v.to_integral_value():
        return f'{v.to_integral_value():,}'
    return f'{v.quantize(Decimal("0.01")):,.2f}'


def percent(value, digits=1):
    if value is None:
        return '—'
    return f'{Decimal(value):.{digits}f}%'


def days_overdue(due_date, today=None):
    from django.utils import timezone
    today = today or timezone.now().date()
    delta = (today - due_date).days
    return max(delta, 0)
