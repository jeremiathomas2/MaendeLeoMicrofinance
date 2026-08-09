from django.contrib import admin

from apps.accounting.models import Account, AccountingPeriod, Expense, JournalEntry, JournalEntryLine
from apps.cash_management.models import BankAccount, BankTransaction, CashTransaction, TellerSession
from apps.credit.models import CreditAssessment, CreditScoreComponent
from apps.repayments.models import Repayment
from apps.savings.models import SavingsAccount, SavingsProduct, SavingsTransaction
from apps.workflows.models import ApprovalConfig


admin.site.register(Repayment, admin.ModelAdmin)
admin.site.register(CreditAssessment, admin.ModelAdmin)
admin.site.register(CreditScoreComponent, admin.ModelAdmin)
admin.site.register(ApprovalConfig, admin.ModelAdmin)


@admin.register(SavingsProduct)
class SavingsProductAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'interest_rate', 'minimum_balance')


@admin.register(SavingsAccount)
class SavingsAccountAdmin(admin.ModelAdmin):
    list_display = ('account_number', 'customer', 'product', 'branch', 'balance', 'status')


@admin.register(SavingsTransaction)
class SavingsTransactionAdmin(admin.ModelAdmin):
    list_display = ('reference', 'account', 'transaction_type', 'amount', 'branch')


@admin.register(TellerSession)
class TellerSessionAdmin(admin.ModelAdmin):
    list_display = ('teller', 'branch', 'opening_balance', 'expected_closing', 'variance', 'status')


@admin.register(CashTransaction)
class CashTransactionAdmin(admin.ModelAdmin):
    list_display = ('reference', 'transaction_type', 'amount', 'branch', 'teller', 'transaction_date')


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ('bank_name', 'account_name', 'account_number', 'account_type', 'balance')


@admin.register(BankTransaction)
class BankTransactionAdmin(admin.ModelAdmin):
    list_display = ('reference', 'bank_account', 'transaction_type', 'amount')


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'account_type', 'is_active')
    list_filter = ('account_type',)


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ('reference', 'entry_date', 'description', 'status', 'branch')
    list_filter = ('status',)


@admin.register(JournalEntryLine)
class JournalEntryLineAdmin(admin.ModelAdmin):
    list_display = ('entry', 'account', 'debit', 'credit')


@admin.register(AccountingPeriod)
class AccountingPeriodAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date', 'status')


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('reference', 'category', 'vendor', 'branch', 'amount', 'approval_status', 'paid')
