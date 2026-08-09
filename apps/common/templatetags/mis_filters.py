"""Display filters shared across templates."""

from django import template

register = template.Library()


@register.filter
def money(value, currency='TZS'):
    try:
        num = float(value or 0)
    except (TypeError, ValueError):
        return f'{currency} 0'
    return f'{currency} {num:,.0f}'.replace(',', ',')


@register.filter
def amount(value):
    try:
        return f'{float(value or 0):,.0f}'
    except (TypeError, ValueError):
        return '0'


@register.filter
def pct(value):
    try:
        return f'{float(value or 0):.1f}%'
    except (TypeError, ValueError):
        return '0.0%'


@register.filter
def get_item(d, key):
    return d.get(key) if hasattr(d, 'get') else None
