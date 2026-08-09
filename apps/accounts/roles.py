"""
Role definitions and authorization helpers.

Roles are backed by Django Groups and Permissions (SRS section 6). These
constants and helpers keep role checks readable without hard-coding them
inside templates (SRS section 108).
"""

ROLE_SYSTEM_ADMIN = 'System Administrator'
ROLE_GENERAL_MANAGER = 'General Manager'
ROLE_HEAD_OF_OPERATIONS = 'Head of Operations'
ROLE_BRANCH_MANAGER = 'Branch Manager'
ROLE_CREDIT_OFFICER = 'Credit Officer'
ROLE_LOAN_OFFICER = 'Loan Officer'
ROLE_TELLER = 'Teller'
ROLE_AUDITOR = 'Auditor'
ROLE_ACCOUNTANT = 'Accountant'

ALL_ROLES = [
    ROLE_SYSTEM_ADMIN,
    ROLE_GENERAL_MANAGER,
    ROLE_HEAD_OF_OPERATIONS,
    ROLE_BRANCH_MANAGER,
    ROLE_CREDIT_OFFICER,
    ROLE_LOAN_OFFICER,
    ROLE_TELLER,
    ROLE_AUDITOR,
    ROLE_ACCOUNTANT,
]

# Roles that see across all branches.
ORG_WIDE_ROLES = [
    ROLE_SYSTEM_ADMIN,
    ROLE_GENERAL_MANAGER,
    ROLE_HEAD_OF_OPERATIONS,
    ROLE_AUDITOR,
]

APPROVAL_ROLES = [
    ROLE_BRANCH_MANAGER,
    ROLE_HEAD_OF_OPERATIONS,
    ROLE_GENERAL_MANAGER,
]

FINANCIAL_ROLES = [
    ROLE_TELLER,
    ROLE_BRANCH_MANAGER,
]


def role_names_for(user):
    return set(user.groups.values_list('name', flat=True))


def user_has_any_role(user, roles):
    return bool(role_names_for(user) & set(roles))


def is_org_wide(user):
    if user.is_superuser:
        return True
    return user_has_any_role(user, ORG_WIDE_ROLES)


def can_approve(user):
    if user.is_superuser:
        return True
    return user_has_any_role(user, APPROVAL_ROLES)


def can_disburse(user):
    if user.is_superuser:
        return True
    return user_has_any_role(user, FINANCIAL_ROLES)
