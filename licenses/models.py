from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class LicensePlan(models.Model):
    """
    Modelo para los planes de licencia
    """
    # Auditoría básica
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    # Información del Plan
    plan_name = models.CharField(max_length=100)  # 'Basic', 'Pro', 'Enterprise', 'Trial'
    description = models.TextField(blank=True, null=True)
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    price_yearly = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    currency = models.CharField(max_length=3, default='USD')

    # Límites del Plan
    max_employees = models.IntegerField()

    # Control de Acceso
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')

    class Meta:
        db_table = 'license_licenseplan'
        ordering = ['price_monthly', 'plan_name']
        unique_together = [('plan_name',)]

    def __str__(self):
        return f"{self.plan_name} ({'Activo' if self.is_active else 'Inactivo'})"


class UserLicense(models.Model):
    """
    Modelo para las licencias de los usuarios
    """
    # Auditoría básica
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    # Relaciones
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='licenses')
    # Vincular con base_company (Company) existente
    from base.models import Company  # evita import circular al runtime
    company = models.ForeignKey('base.Company', on_delete=models.CASCADE, related_name='licenses')
    plan = models.ForeignKey(LicensePlan, on_delete=models.PROTECT, related_name='user_licenses')

    # Período de Licencia
    start_date = models.DateField()
    end_date = models.DateField()
    is_trial = models.BooleanField(default=False)
    trial_days = models.IntegerField(default=0)

    # Estado de Licencia
    license_status = models.CharField(max_length=20)  # 'active', 'expired', 'suspended', 'cancelled'
    renewal_reminder_sent = models.BooleanField(default=False)

    # Auditoría
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')

    class Meta:
        db_table = 'license_userlicense'
        indexes = [
            models.Index(fields=['company', 'license_status']),
            models.Index(fields=['end_date']),
        ]

    def __str__(self):
        return f"{self.company} - {self.plan.plan_name} - {self.license_status}"

    @property
    def is_expired(self):
        return timezone.now().date() > self.end_date

    def mark_expired_if_needed(self):
        if self.is_expired and self.license_status != 'expired':
            self.license_status = 'expired'
            self.is_active = False
            self.save(update_fields=['license_status', 'is_active'])
