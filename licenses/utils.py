from django.core.exceptions import ValidationError
from .models import UserLicense

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