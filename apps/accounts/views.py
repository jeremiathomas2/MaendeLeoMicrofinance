from django.contrib import messages
from django.contrib.auth import update_session_auth_hash, views as auth_views
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404

from apps.accounts.models import User
from apps.accounts.roles import ALL_ROLES
from apps.audit.models import audit


def splash(request):
    """First-load splash screen; JS redirects to login after the animation."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'splash.html')


class MaendeleoLoginView(auth_views.LoginView):
    template_name = 'registration/login.html'
    redirect_authenticated_user = True
    next_page = 'dashboard'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['demo_accounts'] = (
            User.objects.filter(groups__name__in=ALL_ROLES)
            .select_related('staff_profile')
            .filter(is_active=True)
            .order_by('groups__name')
            .distinct()
        )
        return context


@login_required
def users_page(request):
    if not (request.user.is_superuser or request.user.has_perm('auth.change_user')):
        messages.error(request, 'You do not have permission to manage users.')
        return redirect('dashboard')
    users = User.objects.select_related('staff_profile').order_by('groups__name', 'first_name')
    context = {
        'users': users,
        'roles': Group.objects.filter(name__in=ALL_ROLES).order_by('name'),
        'branches': request.user.accessible_branches(),
    }
    return render(request, 'pages/users.html', context)


@login_required
def users_toggle_status(request, user_id):
    if not request.user.is_superuser:
        messages.error(request, 'Only administrators can change user status.')
        return redirect('users_page')
    target = get_object_or_404(User, pk=user_id)
    if target == request.user:
        messages.error(request, 'You cannot deactivate your own account.')
    else:
        target.is_active = not target.is_active
        target.save(update_fields=['is_active'])
        messages.success(request, f'{target.get_full_name()} {"activated" if target.is_active else "deactivated"}.')
    return redirect('users_page')


@login_required
def mark_notifications_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return redirect('dashboard')


@login_required
def profile_page(request):
    """View and edit the signed-in user's own profile."""
    user = request.user
    branch = getattr(user, 'staff_profile', None)

    if request.method == 'POST':
        if 'profile_save' in request.POST:
            user.first_name = request.POST.get('first_name', '').strip()
            user.last_name = request.POST.get('last_name', '').strip()
            user.email = request.POST.get('email', '').strip()
            user.phone = request.POST.get('phone', '').strip()
            user.save(update_fields=['first_name', 'last_name', 'email', 'phone'])
            audit(user, 'USER_UPDATED', user, request=request,
                  new={'fields': ['first_name', 'last_name', 'email', 'phone']})
            messages.success(request, 'Profile updated.')
            return redirect('profile_page')

        if 'password_save' in request.POST:
            form = PasswordChangeForm(user, request.POST)
            if form.is_valid():
                form.save()
                update_session_auth_hash(request, form.user)
                audit(user, 'SYSTEM_EVENT', user, request=request, reason='Password changed')
                messages.success(request, 'Password changed.')
                return redirect('profile_page')
            messages.error(request, 'Could not change password — check your current password.')

    context = {
        'profile': user,
        'staff_profile': branch,
        'password_form': PasswordChangeForm(user),
    }
    return render(request, 'pages/profile.html', context)
