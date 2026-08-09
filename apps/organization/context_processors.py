from django.conf import settings


def institution(request):
    from apps.organization.models import Branch, Organization
    org = Organization.get()
    context = {
        'organization': org,
        'CURRENCY': (org.currency if org else 'TZS'),
    }
    if request.user.is_authenticated:
        profile = getattr(request.user, 'staff_profile', None)
        context['user_branches'] = list(request.user.accessible_branches())
        if profile and profile.primary_branch:
            context['user_branch'] = profile.primary_branch
        else:
            context['user_branch'] = None
        context['user_role'] = getattr(request.user, 'role_name', 'Staff')
    return context
