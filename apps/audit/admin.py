from django.contrib import admin

from apps.audit.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'action', 'object_repr', 'branch', 'ip_address')
    list_filter = ('action', 'branch')
    search_fields = ('object_repr', 'object_id', 'reference', 'user__username')
    readonly_fields = ('timestamp', 'previous_value', 'new_value')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
