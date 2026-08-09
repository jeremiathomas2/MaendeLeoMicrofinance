from django import forms

from apps.credit.models import CreditAssessment
from apps.customers.models import Customer
from apps.loans.models import LoanApplication, LoanProduct
from apps.organization.models import Branch


class LoanApplicationForm(forms.ModelForm):
    product = forms.ModelChoiceField(queryset=LoanProduct.objects.filter(status='ACTIVE'))
    customer = forms.ModelChoiceField(queryset=Customer.objects.filter(status='ACTIVE'))
    requested_amount = forms.DecimalField(min_value=0.01, max_digits=16, decimal_places=2)
    requested_term_months = forms.IntegerField(min_value=1, max_value=120)

    class Meta:
        model = LoanApplication
        fields = ['customer', 'product', 'requested_amount', 'requested_term_months', 'purpose', 'proposed_installment']
        widgets = {'purpose': forms.Textarea(attrs={'rows': 2})}

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        if user is not None:
            branches = user.accessible_branches()
            if not (user.is_superuser or user.has_perm('organization.see_all_branches')):
                self.fields['customer'].queryset = Customer.objects.filter(branch__in=branches, status='ACTIVE')

    def clean_requested_amount(self):
        amount = self.cleaned_data['requested_amount']
        product = self.cleaned_data.get('product')
        if product:
            if amount < product.min_amount:
                raise forms.ValidationError(f'Amount below product minimum of {product.min_amount}')
            if amount > product.max_amount:
                raise forms.ValidationError(f'Amount exceeds product maximum of {product.max_amount}')
        return amount


class CreditAssessmentForm(forms.ModelForm):
    class Meta:
        model = CreditAssessment
        fields = ['verified_income', 'verified_expenses', 'existing_obligations', 'credit_score',
                  'risk_rating', 'recommendation', 'recommended_amount', 'recommended_term_months',
                  'collateral_assessed', 'capacity_notes', 'character_notes', 'collateral_notes',
                  'conditions_notes', 'overall_notes']
        widgets = {
            'capacity_notes': forms.Textarea(attrs={'rows': 2}),
            'character_notes': forms.Textarea(attrs={'rows': 2}),
            'collateral_notes': forms.Textarea(attrs={'rows': 2}),
            'conditions_notes': forms.Textarea(attrs={'rows': 2}),
            'overall_notes': forms.Textarea(attrs={'rows': 2}),
        }
