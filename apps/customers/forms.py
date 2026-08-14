from django import forms

from apps.customers.models import Customer, CustomerDocument, CustomerGroup
from apps.organization.models import Branch


class CustomerRegistrationForm(forms.ModelForm):
    branch = forms.ModelChoiceField(queryset=Branch.objects.filter(status='ACTIVE'), required=False)
    group = forms.ModelChoiceField(queryset=CustomerGroup.objects.filter(status='ACTIVE'), required=False)

    class Meta:
        model = Customer
        fields = [
            'full_name', 'gender', 'date_of_birth', 'national_id', 'phone', 'email',
            'marital_status', 'address', 'occupation', 'employer',
            'monthly_income', 'other_income', 'monthly_expenses', 'existing_debts',
            'bank_name', 'bank_account_number', 'branch', 'group',
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        if user is not None and not (user.is_superuser or user.has_perm('organization.see_all_branches')):
            branches = user.accessible_branches()
            self.fields['branch'].queryset = branches
            if branches.exists():
                self.fields['branch'].initial = branches.first()


class CustomerEditForm(forms.ModelForm):
    branch = forms.ModelChoiceField(queryset=Branch.objects.filter(status='ACTIVE'))

    class Meta:
        model = Customer
        fields = [
            'full_name', 'gender', 'date_of_birth', 'national_id', 'phone', 'email',
            'marital_status', 'address', 'occupation', 'employer',
            'monthly_income', 'other_income', 'monthly_expenses', 'existing_debts',
            'bank_name', 'bank_account_number', 'branch',
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        if user is not None and not (user.is_superuser or user.has_perm('organization.see_all_branches')):
            branches = user.accessible_branches()
            self.fields['branch'].queryset = branches


class CustomerDocumentForm(forms.ModelForm):
    class Meta:
        model = CustomerDocument
        fields = ['document_type', 'file', 'notes']


class GroupForm(forms.ModelForm):
    branch = forms.ModelChoiceField(queryset=Branch.objects.filter(status='ACTIVE'))
    leader = forms.ModelChoiceField(queryset=Customer.objects.filter(status='ACTIVE'), required=False)

    class Meta:
        model = CustomerGroup
        fields = ['name', 'branch', 'formation_date', 'leader', 'meeting_location',
                  'meeting_frequency', 'meeting_day']
        widgets = {'formation_date': forms.DateInput(attrs={'type': 'date'})}
