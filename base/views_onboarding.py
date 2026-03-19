"""
views_onboarding.py

Company onboarding wizard views.
Guides new companies through initial setup after registration.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.translation import gettext as gettext
from django.utils.translation import gettext_lazy as _

from base.forms import CompanyForm
from base.models import (
    Company,
    Department,
    EmployeeShift,
    EmployeeShiftDay,
    EmployeeShiftSchedule,
    EmployeeType,
    Holidays,
    JobPosition,
    WorkType,
)

DEPARTMENT_SUGGESTIONS = [
    "Recursos Humanos",
    "Administración",
    "Finanzas",
    "Contabilidad",
    "Ventas",
    "Marketing",
    "Tecnología",
    "Operaciones",
    "Logística",
    "Atención al Cliente",
    "Legal",
    "Producción",
]

EMPLOYEE_TYPE_SUGGESTIONS = [
    "Tiempo Completo",
    "Medio Tiempo",
    "Temporal",
    "Contratista",
    "Pasante",
    "Freelance",
]

WORK_TYPE_SUGGESTIONS = [
    "Presencial",
    "Remoto",
    "Híbrido",
    "Trabajo de Campo",
]

LEAVE_TYPE_SUGGESTIONS = [
    {
        "name": "Vacaciones",
        "payment": "paid",
        "total_days": 15,
        "icon_name": "sunny-outline",
        "color": "#10b981",
    },
    {
        "name": "Incapacidad",
        "payment": "paid",
        "total_days": 180,
        "icon_name": "medkit-outline",
        "color": "#ef4444",
    },
    {
        "name": "Permiso Personal",
        "payment": "unpaid",
        "total_days": 3,
        "icon_name": "person-outline",
        "color": "#6366f1",
    },
    {
        "name": "Calamidad Doméstica",
        "payment": "paid",
        "total_days": 5,
        "icon_name": "home-outline",
        "color": "#f59e0b",
    },
    {
        "name": "Licencia de Maternidad",
        "payment": "paid",
        "total_days": 126,
        "icon_name": "heart-outline",
        "color": "#ec4899",
    },
    {
        "name": "Licencia de Paternidad",
        "payment": "paid",
        "total_days": 14,
        "icon_name": "heart-outline",
        "color": "#3b82f6",
    },
    {
        "name": "Licencia de Luto",
        "payment": "paid",
        "total_days": 5,
        "icon_name": "flower-outline",
        "color": "#64748b",
    },
]

BOLIVIA_HOLIDAYS = [
    {"name": "Año Nuevo", "date": "01-01", "recurring": True},
    {"name": "Estado Plurinacional", "date": "01-22", "recurring": True},
    {"name": "Día del Trabajo", "date": "05-01", "recurring": True},
    {"name": "Año Nuevo Aymara", "date": "06-21", "recurring": True},
    {"name": "Día de la Independencia", "date": "08-06", "recurring": True},
    {"name": "Día de Todos los Santos", "date": "11-02", "recurring": True},
    {"name": "Navidad", "date": "12-25", "recurring": True},
]

DAY_CHOICES = [
    ("monday", _("Lunes")),
    ("tuesday", _("Martes")),
    ("wednesday", _("Miércoles")),
    ("thursday", _("Jueves")),
    ("friday", _("Viernes")),
    ("saturday", _("Sábado")),
    ("sunday", _("Domingo")),
]

WIZARD_STEPS = [
    (1, _("Bienvenida")),
    (2, _("Empresa")),
    (3, _("Deptos.")),
    (4, _("Puestos")),
    (5, _("Horarios")),
    (6, _("Empleados")),
    (7, _("Trabajo")),
    (8, _("Festivos")),
    (9, _("Permisos")),
    (10, _("Resumen")),
]


def _wizard_context(current_step):
    """Return common wizard context for the step header and progress bar."""
    total = len(WIZARD_STEPS)
    progress = int((current_step - 1) / (total - 1) * 100) if total > 1 else 0
    return {
        "steps": WIZARD_STEPS,
        "current_step": current_step,
        "progress": progress,
    }


def _get_user_company(request):
    """Get the company associated with the current user."""
    company_id = request.session.get("selected_company")
    if company_id and company_id != "all":
        return Company.objects.filter(id=company_id).first()
    try:
        employee = request.user.employee_get
        work_info = getattr(employee, "employee_work_info", None)
        if work_info and work_info.company_id:
            return work_info.company_id
    except Exception:
        pass
    return Company.objects.first()


def needs_onboarding(user):
    """Check if the user's company needs onboarding."""
    if user.is_superuser:
        return False
    try:
        employee = user.employee_get
        work_info = getattr(employee, "employee_work_info", None)
        if work_info and work_info.company_id:
            company = work_info.company_id
            has_departments = Department.objects.filter(
                company_id=company
            ).exists()
            return not has_departments
    except Exception:
        pass
    return False


def _detect_current_step(company):
    """Detect which onboarding step the company should resume from."""
    from leave.models import LeaveType

    # Step 2: Company profile — check if address is filled
    if not company.address:
        return 2

    # Step 3: Departments
    if not Department.objects.filter(company_id=company).exists():
        return 3

    # Step 4: Job positions
    if not JobPosition.objects.filter(company_id=company).exists():
        return 4

    # Step 5: Schedules (shifts)
    if not EmployeeShift.objects.filter(company_id=company).exists():
        return 5

    # Step 6: Employee types
    if not EmployeeType.objects.filter(company_id=company).exists():
        return 6

    # Step 7: Work types
    if not WorkType.objects.filter(company_id=company).exists():
        return 7

    # Step 8: Holidays
    if not Holidays.objects.filter(company_id=company).exists():
        return 8

    # Step 9: Leave types
    if not LeaveType.objects.filter(company_id=company).exists():
        return 9

    # All done — go to summary
    return 10


# ─── Step 1: Welcome / Router ────────────────────────────────────────────────

STEP_ROUTES = {
    2: "company-onboarding-step2",
    3: "company-onboarding-step3",
    4: "company-onboarding-step4",
    5: "company-onboarding-step5",
    6: "company-onboarding-step6",
    7: "company-onboarding-step7",
    8: "company-onboarding-step8",
    9: "company-onboarding-step9",
    10: "company-onboarding-step10",
}


@login_required
def step1_welcome(request):
    """Welcome step — if user already started onboarding, redirect to where they left off."""
    company = _get_user_company(request)
    if company and company.address:
        # User already completed at least step 2, detect where they are
        resume_step = _detect_current_step(company)
        if resume_step in STEP_ROUTES:
            return redirect(STEP_ROUTES[resume_step])
    return render(request, "company_onboarding/step_1_welcome.html", _wizard_context(1))


# ─── Step 2: Company Profile ─────────────────────────────────────────────────

@login_required
def step2_company(request):
    company = _get_user_company(request)
    if not company:
        messages.error(request, _("No se encontró una empresa asociada."))
        return redirect("home-page")

    if request.method == "POST":
        form = CompanyForm(request.POST, request.FILES, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, _("Empresa actualizada correctamente."))
            return redirect("company-onboarding-step3")
    else:
        form = CompanyForm(instance=company)

    return render(request, "company_onboarding/step_2_company.html", {**_wizard_context(2), "form": form})


# ─── Step 3: Departments ─────────────────────────────────────────────────────

@login_required
def step3_departments(request):
    company = _get_user_company(request)
    if not company:
        return redirect("home-page")

    error = None
    if request.method == "POST":
        dept_name = request.POST.get("department_name", "").strip()
        if not dept_name:
            error = _("El nombre del departamento es obligatorio.")
        else:
            existing = Department.objects.filter(
                department__iexact=dept_name, company_id=company
            ).exists()
            if existing:
                error = _("Este departamento ya existe.")
            else:
                dept = Department.objects.create(department=dept_name)
                dept.company_id.add(company)
                messages.success(
                    request,
                    _("Departamento '%(name)s' creado.") % {"name": dept_name},
                )
                return redirect("company-onboarding-step3")

    departments = Department.objects.filter(company_id=company)
    existing_names = list(departments.values_list("department", flat=True))

    return render(
        request,
        "company_onboarding/step_3_departments.html",
        {
            **_wizard_context(3),
            "departments": departments,
            "suggestions": DEPARTMENT_SUGGESTIONS,
            "existing_names": existing_names,
            "error": error,
        },
    )


@login_required
def dept_delete(request, dept_id):
    company = _get_user_company(request)
    if request.method == "POST" and company:
        dept = Department.objects.filter(id=dept_id, company_id=company).first()
        if dept:
            dept.delete()
            messages.success(request, _("Departamento eliminado."))
    return redirect("company-onboarding-step3")


# ─── Step 4: Job Positions ───────────────────────────────────────────────────

@login_required
def step4_positions(request):
    company = _get_user_company(request)
    if not company:
        return redirect("home-page")

    error = None
    if request.method == "POST":
        pos_name = request.POST.get("position_name", "").strip()
        dept_id = request.POST.get("department_id")
        if not pos_name:
            error = _("El nombre del puesto es obligatorio.")
        elif not dept_id:
            error = _("Debes seleccionar un departamento.")
        else:
            dept = Department.objects.filter(
                id=dept_id, company_id=company
            ).first()
            if not dept:
                error = _("Departamento no encontrado.")
            else:
                existing = JobPosition.objects.filter(
                    job_position__iexact=pos_name,
                    department_id=dept,
                    company_id=company,
                ).exists()
                if existing:
                    error = _("Este puesto ya existe en ese departamento.")
                else:
                    pos = JobPosition.objects.create(
                        job_position=pos_name, department_id=dept
                    )
                    pos.company_id.add(company)
                    messages.success(
                        request,
                        _("Puesto '%(name)s' creado.") % {"name": pos_name},
                    )
                    return redirect("company-onboarding-step4")

    departments = Department.objects.filter(company_id=company)
    positions = JobPosition.objects.filter(company_id=company)

    return render(
        request,
        "company_onboarding/step_4_positions.html",
        {
            **_wizard_context(4),
            "departments": departments,
            "positions": positions,
            "error": error,
        },
    )


@login_required
def pos_delete(request, pos_id):
    company = _get_user_company(request)
    if request.method == "POST" and company:
        pos = JobPosition.objects.filter(id=pos_id, company_id=company).first()
        if pos:
            pos.delete()
            messages.success(request, _("Puesto eliminado."))
    return redirect("company-onboarding-step4")


# ─── Step 5: Work Schedule ───────────────────────────────────────────────────

@login_required
def step5_schedule(request):
    company = _get_user_company(request)
    if not company:
        return redirect("home-page")

    error = None
    if request.method == "POST":
        shift_name = request.POST.get("shift_name", "").strip()
        start_time = request.POST.get("start_time", "08:00")
        end_time = request.POST.get("end_time", "17:00")
        work_days = request.POST.getlist("work_days")
        min_hours = request.POST.get("min_hours", "08:00")

        if not shift_name:
            error = _("El nombre del turno es obligatorio.")
        elif not work_days:
            error = _("Debes seleccionar al menos un día laboral.")
        else:
            existing = EmployeeShift.objects.filter(
                employee_shift__iexact=shift_name, company_id=company
            ).exists()
            if existing:
                error = _("Ya existe un turno con ese nombre.")
            else:
                shift = EmployeeShift.objects.create(
                    employee_shift=shift_name,
                    weekly_full_time=f"{len(work_days) * 8}:00",
                    full_time="200:00",
                )
                shift.company_id.add(company)

                for day_value in work_days:
                    day_obj, _created = EmployeeShiftDay.objects.get_or_create(
                        day=day_value
                    )
                    day_obj.company_id.add(company)
                    EmployeeShiftSchedule.objects.create(
                        shift_id=shift,
                        day=day_obj,
                        start_time=start_time,
                        end_time=end_time,
                        minimum_working_hour=min_hours,
                    )

                messages.success(
                    request,
                    _("Turno '%(name)s' creado con %(days)s días.")
                    % {"name": shift_name, "days": len(work_days)},
                )
                return redirect("company-onboarding-step5")

    shifts = EmployeeShift.objects.filter(company_id=company)

    return render(
        request,
        "company_onboarding/step_5_schedule.html",
        {
            **_wizard_context(5),
            "shifts": shifts,
            "days": DAY_CHOICES,
            "error": error,
        },
    )


# ─── Step 6: Employee Types ──────────────────────────────────────────────────

@login_required
def step6_employee_types(request):
    company = _get_user_company(request)
    if not company:
        return redirect("home-page")

    error = None
    if request.method == "POST":
        type_name = request.POST.get("employee_type", "").strip()
        if not type_name:
            error = _("El nombre del tipo de empleado es obligatorio.")
        else:
            existing = EmployeeType.objects.filter(
                employee_type__iexact=type_name, company_id=company
            ).exists()
            if existing:
                error = _("Este tipo de empleado ya existe.")
            else:
                et = EmployeeType.objects.create(employee_type=type_name)
                et.company_id.add(company)
                messages.success(
                    request,
                    _("Tipo '%(name)s' creado.") % {"name": type_name},
                )
                return redirect("company-onboarding-step6")

    employee_types = EmployeeType.objects.filter(company_id=company)
    existing_names = list(employee_types.values_list("employee_type", flat=True))

    return render(
        request,
        "company_onboarding/step_6_employee_types.html",
        {
            **_wizard_context(6),
            "employee_types": employee_types,
            "suggestions": EMPLOYEE_TYPE_SUGGESTIONS,
            "existing_names": existing_names,
            "error": error,
        },
    )


@login_required
def employee_type_delete(request, et_id):
    company = _get_user_company(request)
    if request.method == "POST" and company:
        et = EmployeeType.objects.filter(id=et_id, company_id=company).first()
        if et:
            et.delete()
            messages.success(request, _("Tipo de empleado eliminado."))
    return redirect("company-onboarding-step6")


# ─── Step 7: Work Types ──────────────────────────────────────────────────────

@login_required
def step7_work_types(request):
    company = _get_user_company(request)
    if not company:
        return redirect("home-page")

    error = None
    if request.method == "POST":
        type_name = request.POST.get("work_type", "").strip()
        if not type_name:
            error = _("El nombre del tipo de trabajo es obligatorio.")
        else:
            existing = WorkType.objects.filter(
                work_type__iexact=type_name, company_id=company
            ).exists()
            if existing:
                error = _("Este tipo de trabajo ya existe.")
            else:
                wt = WorkType.objects.create(work_type=type_name)
                wt.company_id.add(company)
                messages.success(
                    request,
                    _("Tipo '%(name)s' creado.") % {"name": type_name},
                )
                return redirect("company-onboarding-step7")

    work_types = WorkType.objects.filter(company_id=company)
    existing_names = list(work_types.values_list("work_type", flat=True))

    return render(
        request,
        "company_onboarding/step_7_work_types.html",
        {
            **_wizard_context(7),
            "work_types": work_types,
            "suggestions": WORK_TYPE_SUGGESTIONS,
            "existing_names": existing_names,
            "error": error,
        },
    )


@login_required
def work_type_delete(request, wt_id):
    company = _get_user_company(request)
    if request.method == "POST" and company:
        wt = WorkType.objects.filter(id=wt_id, company_id=company).first()
        if wt:
            wt.delete()
            messages.success(request, _("Tipo de trabajo eliminado."))
    return redirect("company-onboarding-step7")


# ─── Step 8: Holidays ────────────────────────────────────────────────────────

@login_required
def step8_holidays(request):
    company = _get_user_company(request)
    if not company:
        return redirect("home-page")

    error = None
    if request.method == "POST":
        action = request.POST.get("action", "add")

        if action == "load_bolivia":
            import datetime

            current_year = datetime.date.today().year
            added = 0
            for h in BOLIVIA_HOLIDAYS:
                month, day = h["date"].split("-")
                start = datetime.date(current_year, int(month), int(day))
                exists = Holidays.objects.filter(
                    name=h["name"], company_id=company
                ).exists()
                if not exists:
                    Holidays.objects.create(
                        name=h["name"],
                        start_date=start,
                        end_date=start,
                        recurring=h["recurring"],
                        company_id=company,
                    )
                    added += 1
            if added:
                messages.success(
                    request,
                    _("%(count)s festivos de Bolivia agregados.") % {"count": added},
                )
            else:
                messages.info(request, _("Los festivos ya estaban cargados."))
            return redirect("company-onboarding-step8")

        else:
            holiday_name = request.POST.get("holiday_name", "").strip()
            start_date = request.POST.get("start_date")
            end_date = request.POST.get("end_date") or start_date
            recurring = request.POST.get("recurring") == "on"

            if not holiday_name:
                error = _("El nombre del festivo es obligatorio.")
            elif not start_date:
                error = _("La fecha de inicio es obligatoria.")
            else:
                existing = Holidays.objects.filter(
                    name__iexact=holiday_name, company_id=company
                ).exists()
                if existing:
                    error = _("Este festivo ya existe.")
                else:
                    Holidays.objects.create(
                        name=holiday_name,
                        start_date=start_date,
                        end_date=end_date,
                        recurring=recurring,
                        company_id=company,
                    )
                    messages.success(
                        request,
                        _("Festivo '%(name)s' creado.") % {"name": holiday_name},
                    )
                    return redirect("company-onboarding-step8")

    holidays = Holidays.objects.filter(company_id=company).order_by("start_date")

    return render(
        request,
        "company_onboarding/step_8_holidays.html",
        {
            **_wizard_context(8),
            "holidays": holidays,
            "error": error,
        },
    )


@login_required
def holiday_delete(request, holiday_id):
    company = _get_user_company(request)
    if request.method == "POST" and company:
        h = Holidays.objects.filter(id=holiday_id, company_id=company).first()
        if h:
            h.delete()
            messages.success(request, _("Festivo eliminado."))
    return redirect("company-onboarding-step8")


# ─── Step 9: Leave Types ─────────────────────────────────────────────────────

@login_required
def step9_leave_types(request):
    from leave.models import LeaveType

    company = _get_user_company(request)
    if not company:
        return redirect("home-page")

    error = None
    if request.method == "POST":
        action = request.POST.get("action", "add")

        if action == "load_suggestions":
            added = 0
            for lt_data in LEAVE_TYPE_SUGGESTIONS:
                exists = LeaveType.objects.filter(
                    name__iexact=lt_data["name"], company_id=company
                ).exists()
                if not exists:
                    LeaveType.objects.create(
                        name=lt_data["name"],
                        payment=lt_data["payment"],
                        total_days=lt_data["total_days"],
                        color=lt_data.get("color", ""),
                        reset=True,
                        reset_based="yearly",
                        require_approval="yes",
                        company_id=company,
                    )
                    added += 1
            if added:
                messages.success(
                    request,
                    _("%(count)s tipos de permiso creados.") % {"count": added},
                )
            else:
                messages.info(request, _("Los tipos de permiso ya estaban creados."))
            return redirect("company-onboarding-step9")

        else:
            lt_name = request.POST.get("leave_name", "").strip()
            lt_payment = request.POST.get("payment", "unpaid")
            lt_days = request.POST.get("total_days", "1")

            if not lt_name:
                error = _("El nombre del tipo de permiso es obligatorio.")
            else:
                existing = LeaveType.objects.filter(
                    name__iexact=lt_name, company_id=company
                ).exists()
                if existing:
                    error = _("Este tipo de permiso ya existe.")
                else:
                    try:
                        days_float = float(lt_days)
                    except (ValueError, TypeError):
                        days_float = 1
                    LeaveType.objects.create(
                        name=lt_name,
                        payment=lt_payment,
                        total_days=days_float,
                        reset=True,
                        reset_based="yearly",
                        require_approval="yes",
                        company_id=company,
                    )
                    messages.success(
                        request,
                        _("Tipo de permiso '%(name)s' creado.") % {"name": lt_name},
                    )
                    return redirect("company-onboarding-step9")

    leave_types = LeaveType.objects.filter(company_id=company)

    return render(
        request,
        "company_onboarding/step_9_leave_types.html",
        {
            **_wizard_context(9),
            "leave_types": leave_types,
            "suggestions": LEAVE_TYPE_SUGGESTIONS,
            "error": error,
        },
    )


@login_required
def leave_type_delete(request, lt_id):
    from leave.models import LeaveType

    company = _get_user_company(request)
    if request.method == "POST" and company:
        lt = LeaveType.objects.filter(id=lt_id, company_id=company).first()
        if lt:
            lt.delete()
            messages.success(request, _("Tipo de permiso eliminado."))
    return redirect("company-onboarding-step9")


# ─── Step 10: Summary ────────────────────────────────────────────────────────

@login_required
def step10_summary(request):
    from leave.models import LeaveType

    company = _get_user_company(request)
    if not company:
        return redirect("home-page")

    summary = {
        "company": company,
        "departments": Department.objects.filter(company_id=company).count(),
        "positions": JobPosition.objects.filter(company_id=company).count(),
        "shifts": EmployeeShift.objects.filter(company_id=company).count(),
        "employee_types": EmployeeType.objects.filter(company_id=company).count(),
        "work_types": WorkType.objects.filter(company_id=company).count(),
        "holidays": Holidays.objects.filter(company_id=company).count(),
        "leave_types": LeaveType.objects.filter(company_id=company).count(),
    }

    return render(
        request,
        "company_onboarding/step_10_summary.html",
        {
            **_wizard_context(10),
            "summary": summary,
        },
    )


# ─── Complete / Skip ─────────────────────────────────────────────────────────

@login_required
def onboarding_complete(request):
    request.session["company_onboarding_done"] = True
    # Limpiar breadcrumbs del wizard para que el dashboard no los muestre
    if "breadcrumbs" in request.session:
        del request.session["breadcrumbs"]
    messages.success(
        request,
        _("Configuracion completada! Tu empresa esta lista para usar."),
    )
    return redirect("home-page")


@login_required
def onboarding_dismiss_banner(request):
    """Dismiss the onboarding banner on the dashboard for this session."""
    request.session["onboarding_banner_dismissed"] = True
    return redirect("home-page")


@login_required
def onboarding_skip(request):
    """Only allow skipping if the company has completed the minimum setup (departments + positions)."""
    company = _get_user_company(request)
    has_departments = Department.objects.filter(company_id=company).exists()
    has_positions = JobPosition.objects.filter(department_id__company_id=company).exists()

    if not has_departments or not has_positions:
        messages.warning(
            request,
            _("Debes completar al menos los departamentos y puestos de trabajo antes de continuar."),
        )
        return redirect("company-onboarding")

    request.session["company_onboarding_skipped"] = True
    if "breadcrumbs" in request.session:
        del request.session["breadcrumbs"]
    messages.info(
        request,
        _("Puedes completar la configuración restante desde el menú de Ajustes."),
    )
    return redirect("home-page")
