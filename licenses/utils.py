from django.core.exceptions import ValidationError
from .models import UserLicense, LicensePlan
from .models import UserRole

def check_employee_limit(company):
    from employee.models import EmployeeWorkInformation
    current = UserLicense.objects.filter(company=company, is_active=True).order_by('-end_date').first()
    if not current:
        raise ValidationError('No hay licencia activa para la empresa.')
    max_emp = current.plan.max_employees
    # Cuenta empleados activos de esa empresa
    count = EmployeeWorkInformation.objects.filter(company_id=company).count()
    if count >= max_emp:
        raise ValidationError(f'Límite de empleados alcanzado para el plan {current.plan.plan_name} ({max_emp}).')


def get_active_license_for_company(company):
    """
    Obtiene la licencia activa para una empresa
    """
    return (
        UserLicense.objects
        .filter(company=company, is_active=True, license_status='active')
        .order_by('-end_date', '-created_at')
        .first()
    )


def get_allowed_modules_for_company(company):
    """
    Obtiene la lista de módulos permitidos para una empresa según su licencia activa
    """
    license_obj = get_active_license_for_company(company)
    if not license_obj:
        return []
    
    plan = license_obj.plan
    if not plan:
        return []
    
    # Verificar que la licencia no esté expirada
    from django.utils import timezone
    if license_obj.end_date and timezone.now().date() > license_obj.end_date:
        return []
    
    # Retornar los módulos permitidos del plan
    if hasattr(plan, 'allowed_modules') and plan.allowed_modules:
        return plan.allowed_modules
    return []


def check_module_access(company, module_name):
    """
    Verifica si una empresa tiene acceso a un módulo específico según su licencia activa
    
    Args:
        company: Instancia de Company
        module_name: Nombre del módulo (ej: 'employee', 'attendance')
    
    Returns:
        bool: True si tiene acceso, False en caso contrario
    """
    allowed_modules = get_allowed_modules_for_company(company)
    return module_name in allowed_modules


def get_user_rol(user):
    """
    Obtiene el rol del usuario como entero. Si no tiene rol asignado:
    - Si es superuser, retorna 1 (superadmin)
    - Si no, retorna 3 (user)
    """
    if not user or not user.is_authenticated:
        return None
    
    try:
        user_role = user.user_role
        return user_role.rol
    except:
        # Si no tiene rol asignado, determinar por defecto
        if user.is_superuser:
            return UserRole.ROLE_SUPERADMIN  # 1
        return UserRole.ROLE_USER  # 3

def is_license_admin(user):
    """
    Verifica si el usuario es administrador de licencias (rol 2 = admin)
    """
    return get_user_rol(user) == UserRole.ROLE_ADMIN  # 2

def is_superadmin(user):
    """
    Verifica si el usuario es superadministrador.
    Los superusers (is_superuser=True) SIEMPRE son superadmins sin restricciones.
    """
    if user.is_superuser:
        return True
    rol = get_user_rol(user)
    return rol == UserRole.ROLE_SUPERADMIN  # 1

def is_regular_user(user):
    """
    Verifica si el usuario es un usuario normal (rol 3 = user)
    """
    # Si es superuser, no es usuario regular
    if user.is_superuser:
        return False
    rol = get_user_rol(user)
    return rol == UserRole.ROLE_USER or (rol is None and not user.is_superuser)  # 3