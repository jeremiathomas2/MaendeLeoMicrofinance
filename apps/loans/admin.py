from django.contrib import admin

from apps.loans.models import (
    Collateral, Guarantor, Loan, LoanApplication, LoanApproval,
    LoanInstallment, LoanProduct,
)


@admin.register(LoanProduct)
class LoanProductAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'min_amount', 'max_amount', 'interest_rate',
                    'interest_method', 'repayment_frequency', 'status')
    list_filter = ('status', 'interest_method', 'repayment_frequency')


@admin.register(LoanApplication)
class LoanApplicationAdmin(admin.ModelAdmin):
    list_display = ('application_number', 'customer', 'branch', 'product',
                    'requested_amount', 'status', 'loan_officer')
    list_filter = ('status', 'branch', 'product')
    search_fields = ('application_number', 'customer__full_name')


@admin.register(LoanApproval)
class LoanApprovalAdmin(admin.ModelAdmin):
    list_display = ('application', 'approver', 'authority_level', 'decision',
                    'amount_approved', 'decided_at')


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ('loan_number', 'customer', 'branch', 'principal', 'outstanding_principal', 'status')
    list_filter = ('status', 'branch', 'product')
    search_fields = ('loan_number', 'customer__full_name')


@admin.register(LoanInstallment)
class LoanInstallmentAdmin(admin.ModelAdmin):
    list_display = ('loan', 'installment_number', 'due_date', 'total_due', 'total_paid', 'status')
    list_filter = ('status',)


@admin.register(Collateral)
class CollateralAdmin(admin.ModelAdmin):
    list_display = ('customer', 'collateral_type', 'estimated_value', 'verification_status')


@admin.register(Guarantor)
class GuarantorAdmin(admin.ModelAdmin):
    list_display = ('name', 'customer', 'guarantee_amount', 'verification_status')
