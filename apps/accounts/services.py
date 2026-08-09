from apps.accounts.models import StaffProfile, StaffBranchAssignment
from apps.accounts.roles import role_names_for, is_org_wide
from apps.common.utils import money, money_full, percent, days_overdue  # noqa: F401


def get_primary_branch(user):
    profile = getattr(user, 'staff_profile', None)
    return profile.primary_branch if profile and profile.primary_branch else None


def get_branch_ids(user):
    """Set of branch IDs the user may operate on."""
    if is_org_wide(user) or user.is_superuser:
        return None  # None means "all branches"
    return set(user.accessible_branches().values_list('id', flat=True))


def filter_by_scope(user, qs, branch_field='branch'):
    """Filter a queryset to the branches the user is allowed to see.

    Returns the queryset unchanged for organization-wide users.
    """
    branch_ids = get_branch_ids(user)
    if branch_ids is None:
        return qs
    kwargs = {f'{branch_field}__id__in': branch_ids}
    return qs.filter(**kwargs)


def create_staff_profile(user, branch, job_title='', department=None):
    profile, _ = StaffProfile.objects.get_or_create(user=user)
    profile.primary_branch = branch
    if job_title:
        profile.job_title = job_title
    if department:
        profile.department = department
    profile.save()
    StaffBranchAssignment.objects.get_or_create(user=user, branch=branch, defaults={'is_primary': True})
    return profile
