from licenses.models import UserLicense
from licenses.utils import get_active_license_for_company, get_allowed_modules_for_company
from django.utils import timezone
from django.contrib import messages

def current_license(request):
    try:
        # Si es superuser, NO mostrar módulos permitidos (lista vacía)
        if request.user.is_authenticated and request.user.is_superuser:
            return {
                'current_license': None,
                'license_days_left': None,
                'license_hours_left': None,
                'show_license_modal': False,
                'allowed_modules': [],  # Lista vacía para superusers
            }
        
        cid = request.session.get('selected_company')
        if not cid:
            return {
                'current_license': None,
                'license_days_left': None,
                'license_hours_left': None,
                'show_license_modal': False,
                'allowed_modules': [],
            }
        
        from base.models import Company
        company = Company.objects.filter(id=cid).first()
        if not company:
            return {
                'current_license': None,
                'license_days_left': None,
                'license_hours_left': None,
                'show_license_modal': False,
                'allowed_modules': [],
            }
        
        # Obtener la licencia activa
        lic = get_active_license_for_company(company)
        
        # Obtener módulos permitidos
        allowed_modules = get_allowed_modules_for_company(company)
        
        # Determinar si se debe mostrar el modal
        show_modal = False
        
        if not lic:
            modal_key = 'license_modal_no_license_shown'
            if not request.session.get(modal_key, False):
                show_modal = True
                request.session[modal_key] = True
        elif lic.end_date:
            today = timezone.now().date()
            days_left = (lic.end_date - today).days
            
            if days_left >= 0:
                from datetime import datetime
                now = timezone.now()
                end_datetime = datetime.combine(lic.end_date, datetime.max.time())
                end_datetime = timezone.make_aware(end_datetime)
                time_diff = end_datetime - now
                hours_left = int(time_diff.total_seconds() / 3600)
            else:
                days_left = 0
                hours_left = 0
            
            is_expired = (
                today > lic.end_date or
                lic.license_status in ('expired', 'suspended', 'cancelled') or
                not lic.is_active
            )
            
            is_expiring_tomorrow = (days_left == 1 and lic.is_active and lic.license_status == 'active')
            
            if is_expired:
                modal_key = 'license_modal_expired_shown'
                if not request.session.get(modal_key, False):
                    show_modal = True
                    request.session[modal_key] = True
            elif is_expiring_tomorrow:
                modal_key = 'license_modal_expiring_tomorrow_shown'
                if not request.session.get(modal_key, False):
                    show_modal = True
                    request.session[modal_key] = True
        else:
            days_left = None
            hours_left = None
            
        if not lic or not lic.end_date:
            days_left = None
            hours_left = None
            
        return {
            'current_license': lic,
            'license_days_left': days_left,
            'license_hours_left': hours_left,
            'show_license_modal': show_modal,
            'allowed_modules': allowed_modules,
        }
    except Exception:
        return {
            'current_license': None,
            'license_days_left': None,
            'license_hours_left': None,
            'show_license_modal': False,
            'allowed_modules': [],
        }