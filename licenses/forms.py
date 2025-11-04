from django import forms
from .models import LicensePlan

class ChangePlanForm(forms.Form):
    plan = forms.ModelChoiceField(queryset=LicensePlan.objects.filter(is_active=True).exclude(plan_name='Trial'))
    cycle = forms.ChoiceField(choices=[('monthly','Mensual'), ('yearly','Anual')])