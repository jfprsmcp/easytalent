"""
licenses/sidebar.py
Sidebar para mostrar información de la empresa y licencia
"""

from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from datetime import datetime

MENU = _("Mi Empresa")
IMG_SRC = "images/ui/company.png"  # Cambiar de .svg a .png

# Función para generar submenús dinámicamente
def get_submenus(request):
    """
    Genera los submenús dinámicamente basándose en la información de la empresa y licencia
    """
    submenus = []
    
    # Información de la empresa
    if request.session.get('selected_company_instance'):
        company_info = request.session['selected_company_instance']
        submenus.append({
            "menu": f"🏢 {company_info.get('company', 'Mi Empresa')}",
            "redirect": "#",
        })
    
    # Información de la licencia
    from licenses.context_processors import current_license
    license_data = current_license(request)
    
    current_lic = license_data.get('current_license')
    if current_lic and current_lic.plan and not request.user.is_superuser:
        # Plan
        plan_name = current_lic.plan.plan_name
        if current_lic.is_trial:
            plan_display = _("Prueba")
        elif plan_name == 'Basic':
            plan_display = _("Básico")
        elif plan_name == 'Pro':
            plan_display = _("Pro")
        elif plan_name == 'Enterprise':
            plan_display = _("Empresa")
        else:
            plan_display = plan_name
        
        submenus.append({
            "menu": f"📦 {_('Plan')}: {plan_display}",
            "redirect": reverse("license_dashboard"),
        })
        
        # Días restantes
        days_left = license_data.get('license_days_left')
        if days_left is not None:
            if days_left < 0:
                days_text = _("Expirado")
            elif days_left == 0:
                days_text = _("Hoy expira")
            else:
                days_text = f"{days_left} {_('día')}{'s' if days_left != 1 else ''}"
            
            submenus.append({
                "menu": f"📅 {_('Días restantes')}: {days_text}",
                "redirect": reverse("license_dashboard"),
            })
        
        # Horas restantes
        hours_left = license_data.get('license_hours_left')
        if hours_left is not None and days_left is not None and days_left >= 0:
            hours_text = f"{hours_left} {_('hora')}{'s' if hours_left != 1 else ''}"
            submenus.append({
                "menu": f"⏰ {_('Horas restantes')}: {hours_text}",
                "redirect": reverse("license_dashboard"),
            })
    
    # Si no hay información, mostrar un mensaje
    if not submenus:
        submenus.append({
            "menu": _("No hay información disponible"),
            "redirect": "#",
        })
    
    return submenus

# Submenús estáticos (se reemplazarán dinámicamente si existe get_submenus)
SUBMENUS = []

def menu_accessibility(request, menu, user_perms, *args, **kwargs):
    """
    Determina si el menú debe mostrarse
    Solo mostrar para usuarios autenticados que no sean superusers o admins de licencias
    """
    if not request.user.is_authenticated:
        return False
    
    from licenses.utils import is_license_admin
    
    # No mostrar para superusers (ya tienen acceso completo)
    if request.user.is_superuser:
        return False
    
    # No mostrar para admins de licencias (ellos tienen su propio dashboard)
    if is_license_admin(request.user):
        return False
    
    return True

ACCESSIBILITY = "licenses.sidebar.menu_accessibility"
