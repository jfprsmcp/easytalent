from licenses.models import UserLicense
from django.utils import timezone
from django.contrib import messages

def current_license(request):
    try:
        # Si es superuser, no mostrar información de licencia
        if request.user.is_authenticated and request.user.is_superuser:
            return {
                'current_license': None,
                'license_days_left': None,
                'license_hours_left': None,
                'show_license_modal': False,
            }
        
        cid = request.session.get('selected_company')
        if not cid:
            return {
                'current_license': None,
                'license_days_left': None,
                'license_hours_left': None,
                'show_license_modal': False,
            }
        from base.models import Company
        company = Company.objects.filter(id=cid).first()
        if not company:
            return {
                'current_license': None,
                'license_days_left': None,
                'license_hours_left': None,
                'show_license_modal': False,
            }
        
        # Obtener la licencia más reciente (incluso si está expirada o inactiva)
        lic = UserLicense.objects.filter(
            company=company
        ).order_by('-end_date', '-created_at').first()
        
        # Determinar si se debe mostrar el modal
        show_modal = False
        
        if not lic:
            # No hay licencia - verificar si ya se mostró el modal en esta sesión
            modal_key = 'license_modal_no_license_shown'
            if not request.session.get(modal_key, False):
                show_modal = True
                request.session[modal_key] = True
        elif lic.end_date:
            today = timezone.now().date()
            days_left = (lic.end_date - today).days
            
            # Calcular horas restantes hasta el final del día de expiración
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
            
            # Verificar si debe mostrarse el modal:
            # 1. Licencia expirada o inactiva
            # 2. Falta exactamente 1 día para expirar
            is_expired = (
                today > lic.end_date or
                lic.license_status in ('expired', 'suspended', 'cancelled') or
                not lic.is_active
            )
            
            is_expiring_tomorrow = (days_left == 1 and lic.is_active and lic.license_status == 'active')
            
            if is_expired:
                # Licencia expirada - verificar si ya se mostró el modal
                modal_key = 'license_modal_expired_shown'
                if not request.session.get(modal_key, False):
                    show_modal = True
                    request.session[modal_key] = True
            elif is_expiring_tomorrow:
                # Falta 1 día - verificar si ya se mostró el modal
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
        }
    except Exception:
        return {
            'current_license': None,
            'license_days_left': None,
            'license_hours_left': None,
            'show_license_modal': False,
        }