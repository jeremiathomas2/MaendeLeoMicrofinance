from django import forms

from apps.customers.models import Customer
from apps.organization.models import Branch
from apps.savings.models import SavingsAccount, SavingsProduct


class SavingsOpenForm(forms.Form):
    customer = forms.ModelChoiceField(queryset=Customer.objects.filter(status='ACTIVE'))
    product = forms.ModelChoiceField(queryset=SavingsProduct.objects.filter(is_active=True))
    opening_deposit = forms.DecimalField(min_value=0, required=False, max_digits=16, decimal_places=2)


class DepositForm(forms.Form):
    account = forms.ModelChoiceField(queryset=SavingsAccount.objects.filter(status='ACTIVE'))
    amount = forms.DecimalField(min_value=0.01, max_digits=16, decimal_places=2)
    description = forms.CharField(required=False, max_length=255)


class WithdrawalForm(forms.Form):
    account = forms.ModelChoiceField(queryset=SavingsAccount.objects.filter(status='ACTIVE'))
    amount = forms.DecimalField(min_value=0.01, max_digits=16, decimal_places=2)
    description = forms.CharField(required=False, max_length=255)
