from django import template
from licenses.utils import check_module_access

register = template.Library()

@register.filter(name='has_module_access')
def has_module_access(company, module_name):
    """
    Template filter para verificar si una empresa tiene acceso a un módulo
    
    Usage:
        {% if request.session.selected_company_instance|has_module_access:'employee' %}
            ...
        {% endif %}
    """
    if not company:
        return False
    
    # Si es superuser, siempre permitir
    # (esto se verifica en el template con request.user.is_superuser)
    
    return check_module_access(company, module_name)


@register.simple_tag(name='module_allowed')
def module_allowed(request, module_name):
    """
    Template tag para verificar si el módulo está permitido
    
    Usage:
        {% module_allowed request 'employee' as can_access_employee %}
        {% if can_access_employee %}
            ...
        {% endif %}
    """
    # Superusers siempre tienen acceso
    if request.user.is_superuser:
        return True
    
    # Obtener allowed_modules del context processor
    allowed_modules = request.resolver_match.context.get('allowed_modules', [])
    
    # Si allowed_modules es None, significa que es superuser (todos permitidos)
    if allowed_modules is None:
        return True
    
    return module_name in allowed_modules
