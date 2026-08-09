"""Workflow helpers: approval routing and maker-checker controls."""

from apps.workflows.models import required_approval_role


def can_approve_amount(user, amount):
    """Return True if the user's roles include the required authority."""
    from apps.accounts.roles import role_names_for, APPROVAL_ROLES

    if user.is_superuser:
        return True
    required = required_approval_role(amount)
    roles = role_names_for(user)
    if required == 'General Manager':
        return 'General Manager' in roles
    if required == 'Head of Operations':
        return any(r in roles for r in ('Head of Operations', 'General Manager'))
    if required == 'Branch Manager':
        return any(r in roles for r in ('Branch Manager', 'Head of Operations', 'General Manager'))
    return bool(roles & set(APPROVAL_ROLES))


def maker_checker_ok(user, application):
    """Segregation of duties: the creator cannot approve their own application."""
    if user.is_superuser:
        return True
    if application.loan_officer_id == user.id:
        return False
    existing = application.approvals.filter(approver=user).exists()
    return not existing


def authority_label(amount):
    role = required_approval_role(amount)
    return role
