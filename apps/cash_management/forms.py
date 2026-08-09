from django import forms

from apps.organization.models import Branch


class OpenSessionForm(forms.Form):
    branch = forms.ModelChoiceField(queryset=Branch.objects.filter(status='ACTIVE'), required=False)
    opening_balance = forms.DecimalField(min_value=0, max_digits=16, decimal_places=2)


class CloseSessionForm(forms.Form):
    actual_closing = forms.DecimalField(min_value=0, max_digits=16, decimal_places=2)
    variance_reason = forms.CharField(required=False, max_length=500)
