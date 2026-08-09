from django.contrib import admin

from apps.customers.models import Customer, CustomerDocument, CustomerGroup, GroupMember


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('customer_number', 'full_name', 'branch', 'phone', 'status', 'risk_rating', 'credit_score')
    list_filter = ('status', 'risk_rating', 'branch')
    search_fields = ('customer_number', 'full_name', 'national_id', 'phone')


@admin.register(CustomerGroup)
class CustomerGroupAdmin(admin.ModelAdmin):
    list_display = ('group_number', 'name', 'branch', 'status', 'member_count')


@admin.register(GroupMember)
class GroupMemberAdmin(admin.ModelAdmin):
    list_display = ('group', 'customer', 'role')


@admin.register(CustomerDocument)
class CustomerDocumentAdmin(admin.ModelAdmin):
    list_display = ('customer', 'document_type', 'upload_date', 'verification_status', 'verified_by')
    list_filter = ('verification_status', 'document_type')
