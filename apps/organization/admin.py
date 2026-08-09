from django.contrib import admin

from apps.organization.models import Branch, Department, Organization, SystemSetting


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'registration_number', 'phone', 'email', 'currency')


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'region', 'manager', 'status')
    list_filter = ('status',)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'branch')


@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    list_display = ('key', 'label', 'value', 'category')
    list_filter = ('category',)
    search_fields = ('key', 'label')
