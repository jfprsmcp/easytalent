from licenses.models import UserLicense
from django.utils import timezone

def current_license(request):
    try:
        cid = request.session.get('selected_company')
        if not cid:
            return {
                'current_license': None,
                'license_days_left': None,
                'license_hours_left': None,
            }
        from base.models import Company
        company = Company.objects.filter(id=cid).first()
        if not company:
            return {
                'current_license': None,
                'license_days_left': None,
                'license_hours_left': None,
            }
        # Obtener la licencia más reciente (incluso si está expirada o inactiva)
        lic = UserLicense.objects.filter(
            company=company
        ).order_by('-end_date', '-created_at').first()
        
        if lic and lic.end_date:
            today = timezone.now().date()
            days_left = (lic.end_date - today).days
            
            # Calcular horas restantes hasta el final del día de expiración
            if days_left >= 0:
                from datetime import datetime, timedelta
                now = timezone.now()
                end_datetime = datetime.combine(lic.end_date, datetime.max.time())
                end_datetime = timezone.make_aware(end_datetime)
                time_diff = end_datetime - now
                hours_left = int(time_diff.total_seconds() / 3600)
            else:
                days_left = 0
                hours_left = 0
        else:
            days_left = None
            hours_left = None
            
        return {
            'current_license': lic,
            'license_days_left': days_left,
            'license_hours_left': hours_left,
        }
    except Exception:
        return {
            'current_license': None,
            'license_days_left': None,
            'license_hours_left': None,
        }