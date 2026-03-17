from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import json

User = get_user_model()

# Lista de módulos disponibles (debe coincidir con SIDEBARS en horilla_apps.py)
AVAILABLE_MODULES = [
    'recruitment',      # Reclutamiento
    'onboarding',       # Incorporación
    'employee',        # Empleados
    'attendance',      # Asistencia
    'leave',           # Permisos
    'payroll',         # Nómina
    'pms',             # Rendimiento
    'offboarding',     # Desembarco
    'asset',           # Activos
    'helpdesk',        # Soporte
    'project',          # Proyectos
    'report',          # Reportes
]

class LicensePlan(models.Model):
    """
    Modelo para los planes de licencia
    """
    # Auditoría básica
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    # Información del Plan
    plan_name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    price_yearly = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    currency = models.CharField(max_length=3, default='USD')

    # Límites del Plan
    max_employees = models.IntegerField()
    
    # NUEVO: Módulos permitidos (JSONField con lista de strings)
    allowed_modules = models.JSONField(
        default=list,
        help_text="Lista de módulos permitidos para este plan. Ejemplo: ['employee', 'attendance', 'leave']"
    )

    # Control de Acceso
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')

    class Meta:
        db_table = 'license_licenseplan'
        ordering = ['price_monthly', 'plan_name']
        unique_together = [('plan_name',)]

    def __str__(self):
        return f"{self.plan_name} ({'Activo' if self.is_active else 'Inactivo'})"
    
    def has_module(self, module_name):
        """Verifica si el plan tiene acceso a un módulo"""
        if not self.allowed_modules:
            return False
        return module_name in self.allowed_modules
    
    def get_allowed_modules(self):
        """Retorna la lista de módulos permitidos"""
        return self.allowed_modules if self.allowed_modules else []


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

    # Agregar método helper para verificar módulos
    def has_module_access(self, module_name):
        """Verifica si la licencia permite acceso a un módulo"""
        if not self.is_active or self.license_status != 'active':
            return False
        if self.is_expired:
            return False
        return self.plan.has_module(module_name)


class UserRole(models.Model):
    """
    Modelo para almacenar el rol del usuario
    Roles disponibles: 1=superadmin, 2=admin, 3=user
    """
    ROLE_SUPERADMIN = 1
    ROLE_ADMIN = 2
    ROLE_USER = 3
    
    ROLE_CHOICES = [
        (ROLE_SUPERADMIN, 'Super Administrator'),
        (ROLE_ADMIN, 'License Administrator'),
        (ROLE_USER, 'Normal User'),
    ]
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='user_role',
        verbose_name='Usuario'
    )
    rol = models.IntegerField(
        choices=ROLE_CHOICES,
        default=ROLE_USER,
        verbose_name='Rol'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'license_userrole'
        verbose_name = 'Rol de Usuario'
        verbose_name_plural = 'Roles de Usuarios'
    
    def __str__(self):
        return f"{self.user.username} - {self.get_rol_display()}"
