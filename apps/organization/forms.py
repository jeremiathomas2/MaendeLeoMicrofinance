from django import forms

from apps.organization.models import Branch


class BranchForm(forms.ModelForm):
    class Meta:
        model = Branch
        fields = ['code', 'name', 'region', 'address', 'phone', 'email', 'opening_date', 'operating_hours']
        widgets = {'opening_date': forms.DateInput(attrs={'type': 'date'})}
