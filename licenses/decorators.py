from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse
from licenses.utils import check_module_access, is_license_admin

def license_admin_required(view_func):
    """
    Decorador que verifica que el usuario sea admin de licencias o superuser.
    Los superusers tienen acceso completo.
    """
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())
        
        # Superusers tienen acceso completo
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        
        # Verificar si es admin de licencias
        if not is_license_admin(request.user):
            messages.error(request, 'No tienes permisos para acceder a esta sección.')
            return redirect('home-page')
        
        return view_func(request, *args, **kwargs)
    return wrapped_view


def module_required(module_name):
    """
    Decorador que verifica que la empresa tenga acceso al módulo según su plan.
    Los superusers tienen acceso completo a todos los módulos.
    Los admins de licencias NO tienen acceso a módulos de empresa.
    
    Usage:
        @module_required('employee')
        def my_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            # Superusers tienen acceso completo - sin restricciones
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            
            # IMPORTANTE: Admins de licencias NO tienen acceso a módulos de empresa
            if is_license_admin(request.user):
                messages.error(
                    request, 
                    'Los administradores de licencias no tienen acceso a módulos de empresa. '
                    'Solo pueden gestionar licencias y planes.'
                )
                return redirect('license_admin_dashboard')
            
            # Obtener la empresa de la sesión
            cid = request.session.get('selected_company')
            if not cid:
                messages.error(request, 'No hay empresa seleccionada.')
                return redirect('home-page')
            
            from base.models import Company
            company = Company.objects.filter(id=cid).first()
            
            if not company:
                messages.error(request, 'Empresa no encontrada.')
                return redirect('home-page')
            
            # Verificar acceso al módulo
            if not check_module_access(company, module_name):
                messages.error(
                    request, 
                    f'Tu plan actual no incluye acceso al módulo {module_name}. '
                    'Por favor, actualiza tu plan para acceder a esta funcionalidad.'
                )
                return redirect('license_dashboard')
            
            return view_func(request, *args, **kwargs)
        return wrapped_view
    return decorator