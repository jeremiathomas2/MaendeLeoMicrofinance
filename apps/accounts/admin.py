from django.contrib import admin

from apps.accounts.models import StaffBranchAssignment, StaffProfile, User


class StaffProfileInline(admin.StackedInline):
    model = StaffProfile
    extra = 0


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'get_full_name', 'phone', 'employee_number', 'account_status', 'is_active', 'is_staff')
    list_filter = ('account_status', 'is_active', 'is_staff')
    search_fields = ('username', 'first_name', 'last_name', 'phone', 'employee_number')
    inlines = [StaffProfileInline]
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'phone', 'employee_number', 'profile_photo')}),
        ('Security', {'fields': ('mfa_enabled', 'must_change_password', 'last_password_change', 'account_status')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )


admin.site.register(StaffBranchAssignment)
