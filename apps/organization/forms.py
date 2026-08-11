from django import forms

from apps.accounts.models import User
from apps.organization.models import Branch


class BranchForm(forms.ModelForm):
    class Meta:
        model = Branch
        fields = ['code', 'name', 'region', 'address', 'phone', 'email', 'manager', 'status',
                  'opening_date', 'operating_hours']
        widgets = {'opening_date': forms.DateInput(attrs={'type': 'date'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['manager'].queryset = User.objects.filter(
            staff_profile__isnull=False,
        ).order_by('first_name', 'last_name')
        self.fields['manager'].label = 'Branch manager'
