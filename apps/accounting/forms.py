from django import forms

from apps.accounting.models import Account, Expense
from apps.organization.models import Branch


class JournalForm(forms.Form):
    account = forms.ModelChoiceField(queryset=Account.objects.filter(is_active=True))
    counter_account = forms.ModelChoiceField(
        queryset=Account.objects.filter(is_active=True), label='Counter account',
    )
    debit = forms.DecimalField(max_digits=16, decimal_places=2)
    credit = forms.DecimalField(max_digits=16, decimal_places=2)
    description = forms.CharField(max_length=255, required=False)
    branch = forms.ModelChoiceField(queryset=Branch.objects.filter(status='ACTIVE'), required=False)


class ExpenseForm(forms.ModelForm):
    branch = forms.ModelChoiceField(queryset=Branch.objects.filter(status='ACTIVE'), required=False)

    class Meta:
        model = Expense
        fields = ['category', 'vendor', 'amount', 'description', 'receipt']
        widgets = {'description': forms.Textarea(attrs={'rows': 2})}
