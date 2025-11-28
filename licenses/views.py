from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.db.models import Count, Q
from django.http import JsonResponse
from django.core.paginator import Paginator
from .models import UserLicense, LicensePlan
from .forms import ChangePlanForm, UserLicenseEditForm, LicensePlanForm
from django.contrib.auth import get_user_model
from base.models import Company
from .decorators import license_admin_required  # Cambiar este import

User = get_user_model()

def _get_selected_company(request):
    cid = request.session.get('selected_company')
    if not cid:
        return None
    from base.models import Company
    return Company.objects.filter(id=cid).first()

@login_required
def license_dashboard(request):
    """Dashboard de licencias para usuarios normales (NO superusers)"""
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
    """Cambiar plan para usuarios normales (NO superusers)"""
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
                end = start + timedelta(days=30)
            else:
                from datetime import timedelta
                end = start + timedelta(days=365)

            if current:
                current.is_active = False
                current.license_status = 'cancelled'
                current.save(update_fields=['is_active', 'license_status'])

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

    plans = LicensePlan.objects.filter(is_active=True).order_by('price_monthly')

    return render(request, 'licenses/change_plan.html', {
        'company': company,
        'current': current,
        'form': form,
        'plans': plans,
    })


# ========== PANEL DE ADMINISTRACIÓN ==========
# Todas las funciones de abajo son SOLO para superusers

@login_required
@license_admin_required  # Cambiar este decorador
def admin_dashboard(request):
    """Panel principal de administración de licencias - Para admins de licencias y superadmins"""
    from datetime import timedelta
    from django.contrib.auth import get_user_model
    from licenses.models import LicensePlan
    
    User = get_user_model()
    
    # Estadísticas generales
    total_licenses = UserLicense.objects.count()
    active_licenses = UserLicense.objects.filter(is_active=True).count()
    inactive_licenses = UserLicense.objects.filter(is_active=False).count()
    cancelled_licenses = UserLicense.objects.filter(license_status='cancelled').count()
    expired_licenses = UserLicense.objects.filter(license_status='expired').count()
    trial_licenses = UserLicense.objects.filter(is_trial=True).count()
    
    # Licencias no activas o canceladas (combinado)
    inactive_or_cancelled = UserLicense.objects.filter(
        Q(is_active=False) | Q(license_status='cancelled')
    ).count()
    
    # Nuevos usuarios (últimos 30 días)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    new_users = User.objects.filter(
        date_joined__gte=thirty_days_ago,
        is_superuser=False  # Excluir superusers del conteo
    ).count()
    
    # Obtener todos los planes activos y contar usuarios por cada plan (dinámico)
    plans_with_users = []
    all_plans = LicensePlan.objects.filter(is_active=True).order_by('plan_name')
    
    for plan in all_plans:
        user_count = UserLicense.objects.filter(
            plan=plan,
            is_active=True
        ).count()
        plans_with_users.append({
            'plan': plan,
            'plan_name': plan.plan_name,
            'user_count': user_count,
        })
    
    # Estadísticas por plan (todas las licencias)
    licenses_by_plan = UserLicense.objects.values('plan__plan_name').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Usuarios por plan (activos) - para gráficas
    active_by_plan = UserLicense.objects.filter(is_active=True).values(
        'plan__plan_name'
    ).annotate(count=Count('id')).order_by('-count')
    
    # Licencias por estado
    licenses_by_status = UserLicense.objects.values('license_status').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Licencias próximas a vencer (últimos 30 días)
    upcoming_expiry = timezone.now().date() + timedelta(days=30)
    expiring_soon = UserLicense.objects.filter(
        end_date__lte=upcoming_expiry,
        end_date__gte=timezone.now().date(),
        is_active=True
    ).count()
    
    # Total de empresas con licencias
    companies_with_licenses = Company.objects.filter(licenses__isnull=False).distinct().count()
    
    context = {
        'total_licenses': total_licenses,
        'active_licenses': active_licenses,
        'inactive_licenses': inactive_licenses,
        'cancelled_licenses': cancelled_licenses,
        'inactive_or_cancelled': inactive_or_cancelled,
        'expired_licenses': expired_licenses,
        'trial_licenses': trial_licenses,
        'new_users': new_users,
        'plans_with_users': plans_with_users,  # Nueva variable dinámica
        'expiring_soon': expiring_soon,
        'companies_with_licenses': companies_with_licenses,
        'licenses_by_plan': list(licenses_by_plan),
        'active_by_plan': list(active_by_plan),
        'licenses_by_status': list(licenses_by_status),
    }
    
    return render(request, 'licenses/admin_dashboard.html', context)


@login_required
@license_admin_required  # Cambiar este decorador
def license_list(request):
    """Listado de todas las licencias de usuarios - SOLO para superusers"""
    # Por defecto, mostrar solo licencias activas
    licenses = UserLicense.objects.select_related('owner', 'company', 'plan', 'created_by', 'modified_by').filter(is_active=True)
    
    # Filtros
    search = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    plan_filter = request.GET.get('plan', '')
    is_active_filter = request.GET.get('is_active', '')
    
    # Si se especifica explícitamente el filtro is_active, aplicar el filtro
    if is_active_filter == 'true':
        licenses = licenses.filter(is_active=True)
    elif is_active_filter == 'false':
        # Si se pide ver inactivos, cambiar el queryset base
        licenses = UserLicense.objects.select_related('owner', 'company', 'plan', 'created_by', 'modified_by').filter(is_active=False)
    
    if search:
        licenses = licenses.filter(
            Q(owner__first_name__icontains=search) |
            Q(owner__last_name__icontains=search) |
            Q(owner__email__icontains=search) |
            Q(company__company__icontains=search) |
            Q(plan__plan_name__icontains=search)
        )
    
    if status_filter:
        licenses = licenses.filter(license_status=status_filter)
    
    if plan_filter:
        licenses = licenses.filter(plan_id=plan_filter)
    
    # Ordenamiento
    order_by = request.GET.get('order_by', '-created_at')
    licenses = licenses.order_by(order_by)
    
    # Paginación
    paginator = Paginator(licenses, 20)
    page = request.GET.get('page', 1)
    licenses_page = paginator.get_page(page)
    
    plans = LicensePlan.objects.filter(is_active=True).order_by('plan_name')
    
    context = {
        'licenses': licenses_page,
        'plans': plans,
        'search': search,
        'status_filter': status_filter,
        'plan_filter': plan_filter,
        'is_active_filter': is_active_filter,
        'order_by': order_by,
    }
    
    return render(request, 'licenses/admin_license_list.html', context)


@login_required
@license_admin_required  # Cambiar este decorador
@transaction.atomic
def license_edit(request, license_id):
    """Editar una licencia de usuario - SOLO para superusers"""
    license_obj = get_object_or_404(UserLicense, id=license_id)
    
    if request.method == 'POST':
        form = UserLicenseEditForm(request.POST, instance=license_obj)
        if form.is_valid():
            license_obj = form.save(commit=False)
            license_obj.modified_by = request.user
            license_obj.save()
            messages.success(request, 'La licencia ha sido actualizada correctamente.')
            return redirect('admin_license_list')
    else:
        form = UserLicenseEditForm(instance=license_obj)
    
    return render(request, 'licenses/admin_license_edit.html', {
        'form': form,
        'license': license_obj,
    })


@login_required
@license_admin_required  # Cambiar este decorador
@transaction.atomic
def license_delete(request, license_id):
    """Eliminar una licencia de usuario - SOLO para superusers (eliminación lógica)"""
    license_obj = get_object_or_404(UserLicense, id=license_id)
    
    if request.method == 'POST':
        # Eliminación lógica: marcar como inactivo
        license_obj.is_active = False
        license_obj.license_status = 'cancelled'
        license_obj.modified_by = request.user
        license_obj.save(update_fields=['is_active', 'license_status', 'modified_by'])
        messages.success(request, 'La licencia ha sido eliminada correctamente.')
        return redirect('admin_license_list')
    
    return render(request, 'licenses/admin_license_delete.html', {
        'license': license_obj,
    })


@login_required
@license_admin_required  # Cambiar este decorador
def plan_list(request):
    """Listado de todos los planes de licencia - SOLO para superusers"""
    # Por defecto, mostrar solo planes activos
    plans = LicensePlan.objects.select_related('created_by', 'modified_by').filter(is_active=True)
    
    # Filtros
    search = request.GET.get('search', '')
    is_active_filter = request.GET.get('is_active', '')
    
    # Si se especifica explícitamente el filtro is_active, aplicar el filtro
    if is_active_filter == 'true':
        plans = plans.filter(is_active=True)
    elif is_active_filter == 'false':
        # Si se pide ver inactivos, cambiar el queryset base
        plans = LicensePlan.objects.select_related('created_by', 'modified_by').filter(is_active=False)
    
    if search:
        plans = plans.filter(
            Q(plan_name__icontains=search) |
            Q(description__icontains=search)
        )
    
    # Ordenamiento
    order_by = request.GET.get('order_by', '-created_at')
    plans = plans.order_by(order_by)
    
    # Paginación
    paginator = Paginator(plans, 20)
    page = request.GET.get('page', 1)
    plans_page = paginator.get_page(page)
    
    context = {
        'plans': plans_page,
        'search': search,
        'is_active_filter': is_active_filter,
        'order_by': order_by,
    }
    
    return render(request, 'licenses/admin_plan_list.html', context)


@login_required
@license_admin_required  # Cambiar este decorador
@transaction.atomic
def plan_create(request):
    """Crear un nuevo plan de licencia - SOLO para superusers"""
    if request.method == 'POST':
        form = LicensePlanForm(request.POST)
        if form.is_valid():
            plan = form.save(commit=False)
            plan.created_by = request.user
            plan.save()
            messages.success(request, 'El plan ha sido creado correctamente.')
            return redirect('admin_plan_list')
    else:
        form = LicensePlanForm()
    
    return render(request, 'licenses/admin_plan_form.html', {
        'form': form,
        'action': 'Crear',
    })


@login_required
@license_admin_required  # Cambiar este decorador
@transaction.atomic
def plan_edit(request, plan_id):
    """Editar un plan de licencia - SOLO para superusers"""
    plan = get_object_or_404(LicensePlan, id=plan_id)
    
    if request.method == 'POST':
        form = LicensePlanForm(request.POST, instance=plan)
        if form.is_valid():
            plan = form.save(commit=False)
            plan.modified_by = request.user
            plan.save()
            messages.success(request, 'El plan ha sido actualizado correctamente.')
            return redirect('admin_plan_list')
    else:
        form = LicensePlanForm(instance=plan)
    
    return render(request, 'licenses/admin_plan_form.html', {
        'form': form,
        'plan': plan,
        'action': 'Editar',
    })


@login_required
@license_admin_required  # Cambiar este decorador
@transaction.atomic
def plan_delete(request, plan_id):
    """Eliminar un plan de licencia - SOLO para superusers (eliminación lógica)"""
    plan = get_object_or_404(LicensePlan, id=plan_id)
    
    if request.method == 'POST':
        # Verificar si hay licencias activas usando este plan
        licenses_count = UserLicense.objects.filter(plan=plan, is_active=True).count()
        if licenses_count > 0:
            messages.error(request, f'No se puede eliminar el plan porque tiene {licenses_count} licencia(s) activa(s) asociada(s).')
            return redirect('admin_plan_list')
        
        # Eliminación lógica: marcar como inactivo
        plan.is_active = False
        plan.modified_by = request.user
        plan.save(update_fields=['is_active', 'modified_by'])
        messages.success(request, 'El plan ha sido eliminado correctamente.')
        return redirect('admin_plan_list')
    
    # Contar solo licencias activas
    licenses_count = UserLicense.objects.filter(plan=plan, is_active=True).count()
    
    return render(request, 'licenses/admin_plan_delete.html', {
        'plan': plan,
        'licenses_count': licenses_count,
    })
