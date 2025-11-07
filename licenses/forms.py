from django import forms
from django.utils.translation import gettext_lazy as _
from .models import LicensePlan, UserLicense
from django.contrib.auth import get_user_model
from base.models import Company

User = get_user_model()

class ChangePlanForm(forms.Form):
    plan = forms.ModelChoiceField(
        queryset=LicensePlan.objects.filter(is_active=True).exclude(plan_name='Trial'),
        label=_("Plan"),
        widget=forms.Select(attrs={"class": "oh-select"}),
        empty_label=_("---Seleccione un plan---")
    )
    cycle = forms.ChoiceField(
        choices=[('monthly', _('Mensual')), ('yearly', _('Anual'))],
        label=_("Ciclo de facturación"),
        widget=forms.Select(attrs={"class": "oh-select"}),
        initial='monthly'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs.setdefault("class", "oh-select")
            elif isinstance(field.widget, forms.TextInput):
                field.widget.attrs.setdefault("class", "oh-input w-100")


class UserLicenseEditForm(forms.ModelForm):
    """Formulario para editar licencias de usuario"""
    owner = forms.ModelChoiceField(
        queryset=User.objects.all(),
        label=_("Propietario"),
        widget=forms.Select(attrs={"class": "oh-select"}),
        required=True
    )
    company = forms.ModelChoiceField(
        queryset=Company.objects.all(),
        label=_("Empresa"),
        widget=forms.Select(attrs={"class": "oh-select"}),
        required=True
    )
    plan = forms.ModelChoiceField(
        queryset=LicensePlan.objects.filter(is_active=True),
        label=_("Plan"),
        widget=forms.Select(attrs={"class": "oh-select"}),
        required=True
    )
    start_date = forms.DateField(
        label=_("Fecha Inicio"),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'oh-input w-100 form-control'}),
        required=True,
        input_formats=['%Y-%m-%d']
    )
    end_date = forms.DateField(
        label=_("Fecha Fin"),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'oh-input w-100 form-control'}),
        required=True,
        input_formats=['%Y-%m-%d']
    )
    is_trial = forms.BooleanField(
        label=_("Es Prueba"),
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'oh-switch__checkbox'})
    )
    trial_days = forms.IntegerField(
        label=_("Días de Prueba"),
        required=False,
        widget=forms.NumberInput(attrs={'class': 'oh-input w-100'})
    )
    license_status = forms.ChoiceField(
        choices=[
            ('active', _('Activa')),
            ('expired', _('Expirada')),
            ('suspended', _('Suspendida')),
            ('cancelled', _('Cancelada'))
        ],
        label=_("Estado de licencia"),
        widget=forms.Select(attrs={"class": "oh-select"}),
        required=True
    )
    renewal_reminder_sent = forms.BooleanField(
        label=_("Recordatorio Enviado"),
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'oh-switch__checkbox'})
    )
    is_active = forms.BooleanField(
        label=_("Activa"),
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'oh-switch__checkbox'})
    )

    class Meta:
        model = UserLicense
        fields = [
            'owner', 'company', 'plan', 'start_date', 'end_date',
            'is_trial', 'trial_days', 'license_status', 'renewal_reminder_sent',
            'is_active'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Configurar el widget de fecha para que use el formato correcto
        self.fields['start_date'].widget.format = '%Y-%m-%d'
        self.fields['end_date'].widget.format = '%Y-%m-%d'
        
        # Si hay una instancia (edición), establecer el valor inicial en formato correcto
        if self.instance and self.instance.pk:
            if self.instance.start_date:
                # Establecer el valor inicial en formato YYYY-MM-DD
                self.initial['start_date'] = self.instance.start_date.strftime('%Y-%m-%d')
            if self.instance.end_date:
                # Establecer el valor inicial en formato YYYY-MM-DD
                self.initial['end_date'] = self.instance.end_date.strftime('%Y-%m-%d')
        
        # Aplicar estilos a los campos
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs.setdefault("class", "oh-select")
            elif isinstance(field.widget, forms.TextInput) or isinstance(field.widget, forms.NumberInput):
                field.widget.attrs.setdefault("class", "oh-input w-100")
            elif isinstance(field.widget, forms.DateInput):
                # Asegurar que el widget tenga el tipo date y las clases correctas
                field.widget.attrs.update({
                    'type': 'date',
                    'class': 'oh-input w-100 form-control'
                })
                field.widget.format = '%Y-%m-%d'


class LicensePlanForm(forms.ModelForm):
    """Formulario para crear/editar planes de licencia"""
    is_active = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'oh-switch__checkbox'}),
        label=_("Activo")
    )

    class Meta:
        model = LicensePlan
        fields = [
            'plan_name', 'description', 'price_monthly', 'price_yearly',
            'currency', 'max_employees', 'is_active'
        ]
        widgets = {
            'plan_name': forms.TextInput(attrs={'class': 'oh-input w-100'}),
            'description': forms.Textarea(attrs={'class': 'oh-input w-100', 'rows': 3}),
            'price_monthly': forms.NumberInput(attrs={'class': 'oh-input w-100', 'step': '0.01'}),
            'price_yearly': forms.NumberInput(attrs={'class': 'oh-input w-100', 'step': '0.01'}),
            'currency': forms.TextInput(attrs={'class': 'oh-input w-100', 'maxlength': 3}),
            'max_employees': forms.NumberInput(attrs={'class': 'oh-input w-100'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.TextInput) or isinstance(field.widget, forms.NumberInput):
                field.widget.attrs.setdefault("class", "oh-input w-100")