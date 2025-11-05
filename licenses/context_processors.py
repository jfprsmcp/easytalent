from licenses.models import UserLicense

def current_license(request):
    try:
        cid = request.session.get('selected_company')
        if not cid:
            return {'current_license': None}
        from base.models import Company
        company = Company.objects.filter(id=cid).first()
        if not company:
            return {'current_license': None}
        # Obtener la licencia más reciente (incluso si está expirada o inactiva)
        lic = UserLicense.objects.filter(
            company=company
        ).order_by('-end_date', '-created_at').first()
        return {'current_license': lic}
    except Exception:
        return {'current_license': None}