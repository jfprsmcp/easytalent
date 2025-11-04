from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from .models import UserLicense, LicensePlan
from .forms import ChangePlanForm

def _get_selected_company(request):
    cid = request.session.get('selected_company')
    if not cid:
        return None
    from base.models import Company
    return Company.objects.filter(id=cid).first()

@login_required
def license_dashboard(request):
    company = _get_selected_company(request)
    current = None
    if company:
        current = UserLicense.objects.filter(company=company, is_active=True).order_by('-end_date').first()
    plans = LicensePlan.objects.filter(is_active=True).order_by('price_monthly')
    return render(request, 'licenses/dashboard.html', {
        'company': company,
        'current': current,
        'plans': plans,
    })

@login_required
@transaction.atomic
def change_plan(request):
    company = _get_selected_company(request)
    if not company:
        messages.error(request, 'No hay empresa seleccionada.')
        return redirect('license_dashboard')

    current = UserLicense.objects.filter(company=company, is_active=True).order_by('-end_date').first()

    if request.method == 'POST':
        form = ChangePlanForm(request.POST)
        if form.is_valid():
            plan = form.cleaned_data['plan']
            cycle = form.cleaned_data['cycle']
            start = timezone.now().date()
            if cycle == 'monthly':
                from datetime import timedelta
                # Aproximación: 30 días
                end = start + timedelta(days=30)
            else:
                from datetime import timedelta
                end = start + timedelta(days=365)

            # Desactivar licencia actual
            if current:
                current.is_active = False
                current.license_status = 'cancelled'
                current.save(update_fields=['is_active', 'license_status'])

            # Crear nueva licencia
            UserLicense.objects.create(
                owner=request.user,
                company=company,
                plan=plan,
                start_date=start,
                end_date=end,
                is_trial=False,
                trial_days=0,
                license_status='active',
                created_by=request.user
            )
            messages.success(request, 'El plan ha sido actualizado.')
            return redirect('license_dashboard')
    else:
        form = ChangePlanForm()

    return render(request, 'licenses/change_plan.html', {
        'company': company,
        'current': current,
        'form': form,
    })
