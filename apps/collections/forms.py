from django import forms

from apps.collections.models import CollectionAction
from apps.loans.models import Loan


class CollectionActionForm(forms.ModelForm):
    loan = forms.ModelChoiceField(queryset=Loan.objects.filter(status__in=['OVERDUE', 'PAR', 'DEFAULT']))

    class Meta:
        model = CollectionAction
        fields = ['loan', 'action_type', 'notes', 'promised_date', 'promised_amount', 'follow_up_date']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 2}),
            'promised_date': forms.DateInput(attrs={'type': 'date'}),
            'follow_up_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def save(self, commit=True):
        action = super().save(commit=False)
        action.customer = action.loan.customer
        if commit:
            action.save()
        return action
