from django.shortcuts import redirect
from django.utils import timezone
from django.contrib import messages
from .models import UserLicense
from .utils import is_license_admin


class LicenseMiddleware:
    """
    Verifica que la empresa seleccionada tenga licencia activa y no expirada.
    - NO aplica a superusers (bypass completo - acceso total).
    - NO aplica a admins de licencias (bypass completo).
    - Solo muestra mensajes en el banner del dashboard (messages framework).
    - Evita spamear: muestra 1 vez por sesión.
    - Si la licencia no es válida, redirige al panel de licencias.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        self.allow_prefixes = (
            '/admin/', '/accounts/', '/login', '/logout',
            '/settings/licenses/', '/static/', '/media/',
            '/register', '/api/', '/i18n/', '/jsi18n/',
            '/health/', '/notifications',
            '/inbox/notifications/',
            '/favicon', '/robots.txt', '/sitemap',
            '/module/',  # Rutas públicas de detalle de módulos
        )
        # Ruta donde sí queremos mostrar recordatorios
        self.dashboard_prefixes = (
            '/dashboard/',  # home principal
            '',  # ruta raíz también puede ser dashboard
        )

    def __call__(self, request):
        path = request.path or ''

        # Excluir rutas públicas y de recursos
        if any(path.startswith(p) for p in self.allow_prefixes):
            return self.get_response(request)

        # Excluir la ruta raíz (landing page) - debe ser completamente pública
        if path == '/' or path == '':
            return self.get_response(request)

        # Excluir peticiones HTMX/AJAX (evita duplicados por carga de widgets)
        if request.headers.get('HX-Request') == 'true' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return self.get_response(request)

        # Solo con sesión iniciada
        if not request.user.is_authenticated:
            return self.get_response(request)

        # BYPASS: Superusers tienen acceso completo sin restricciones
        if request.user.is_superuser:
            return self.get_response(request)

        # BYPASS: Admins de licencias no tienen restricciones de licencia
        if is_license_admin(request.user):
            return self.get_response(request)

        company_id = request.session.get('selected_company')
        if not company_id:
            return self.get_response(request)

        current = UserLicense.objects.filter(
            company_id=company_id, is_active=True
        ).order_by('-end_date').first()
        today = timezone.now().date()

        # Sin licencia activa → mostrar mensaje y redirigir
        if not current:
            self._show_message_once_per_session(
                request,
                key='license_no_active_shown',
                message='No hay licencia activa para la empresa seleccionada. Ve al panel de licencias para activarla.',
                level=messages.ERROR
            )
            return redirect('license_dashboard')

        # Expirada/inactiva → marcar y redirigir
        if (today > current.end_date or
            current.license_status in ('expired', 'suspended', 'cancelled') or
            not current.is_active):

            if today > current.end_date and current.license_status != 'expired':
                current.license_status = 'expired'
                current.is_active = False
                current.save(update_fields=['license_status', 'is_active'])

            self._show_message_once_per_session(
                request,
                key='license_expired_shown',
                message=f'Tu licencia del plan {current.plan.plan_name} para la empresa {current.company} ha expirado o está inactiva. Renueva tu plan.',
                level=messages.ERROR
            )
            return redirect('license_dashboard')

        # Recordatorios (7,3,1) solo en la vista de dashboard (no en sub‑cargas)
        if any(path.startswith(p) for p in self.dashboard_prefixes) or path == '/':
            days_left = (current.end_date - today).days
            if days_left in (7, 3, 1):
                self._show_message_once_per_session(
                    request,
                    key=f'license_reminder_{days_left}_shown',
                    message=f'⚠️ Tu licencia del plan {current.plan.plan_name} para la empresa {current.company} vence en {days_left} día(s). Fecha de vencimiento: {current.end_date}.',
                    level=messages.WARNING
                )

        return self.get_response(request)

    def _show_message_once_per_session(self, request, key, message, level=messages.INFO):
        """
        Muestra un mensaje en el banner del dashboard una sola vez por sesión.
        Usa flags en sesión para evitar duplicados.
        """
        if not request.session.get(key, False):
            messages.add_message(request, level, message)
            request.session[key] = True


from django.urls import resolve, reverse, NoReverseMatch

class AdminRestrictionMiddleware:
    """
    Middleware que restringe el acceso de usuarios con rol 'admin' 
    (administradores de licencias) solo a las funciones de gestión de licencias.
    Los superusers (is_superuser=True) NO tienen restricciones - acceso completo.
    """
    def __init__(self, get_response):
        self.get_response = get_response

        # Rutas completas (nombre reversado → path absoluto) para autenticación
        auth_named_urls = [
            "login", "logout",
            "password_change", "password_change_done",
            "password_reset", "password_reset_done",
            "password_reset_confirm", "password_reset_complete",
        ]
        resolved_paths = set()
        for name in auth_named_urls:
            try:
                resolved_paths.add(reverse(name))
            except NoReverseMatch:
                pass

        # Rutas exactas permitidas para admins de licencias
        self.allowed_exact_paths = {
            "/",
            "/dashboard/",
            "/change-password",      # Cambio de contraseña
            "/change-username",       # Cambio de nombre de usuario
            "/logout",               # Cerrar sesión
            "/two-factor",           # Autenticación de dos factores
            "/send-otp",             # Envío de OTP
        } | resolved_paths  # unimos los paths resueltos

        # Prefijos permitidos (solo los necesarios para admins de licencias)
        # IMPORTANTE: Verificar estos ANTES de blocked_prefixes
        self.allowed_prefixes = (
            "/settings/licenses/",   # TODAS las rutas de licencias (incluye admin/licenses/, admin/plans/, etc.)
            "/employee-profile/",    # Perfil del empleado/usuario
            "/accounts/",            # Autenticación de Django
            "/static/",
            "/media/",
            "/api/",
            "/inbox/notifications/", # Notificaciones
            "/jsi18n/",              # Internacionalización JS
            "/module/",              # Rutas públicas de detalle de módulos
        )
        
        # Prefijos explícitamente bloqueados para admins de licencias
        self.blocked_prefixes = (
            "/settings/",            # Bloquear configuraciones generales (excepto licenses)
            "/employee/",            # Módulo de empleados
            "/attendance/",          # Módulo de asistencia
            "/leave/",               # Módulo de permisos
            "/payroll/",             # Módulo de nómina
            "/recruitment/",         # Módulo de reclutamiento
            "/onboarding/",          # Módulo de incorporación
            "/offboarding/",         # Módulo de desembarco
            "/pms/",                 # Módulo de rendimiento
            "/asset/",               # Módulo de activos
            "/helpdesk/",            # Módulo de soporte
            "/project/",             # Módulo de proyectos
            "/report/",              # Módulo de reportes
        )

    def __call__(self, request):
        path = request.path
        
        # IMPORTANTE: Permitir rutas de autenticación (login, logout) SIN restricciones
        # Esto debe ir ANTES de cualquier verificación de usuario
        if path in self.allowed_exact_paths or path.startswith("/accounts/"):
            return self.get_response(request)
        
        # IMPORTANTE: Superusers NO tienen restricciones - acceso completo
        if request.user.is_authenticated and request.user.is_superuser:
            return self.get_response(request)
        
        # Solo aplicar restricciones a usuarios con rol 'admin' (NO a superusers)
        if (
            request.user.is_authenticated
            and is_license_admin(request.user)
            and not path.startswith("/admin/")  # Django admin original
        ):
            # 1. Paths exactos permitidos (ya verificados arriba, pero por seguridad)
            if path in self.allowed_exact_paths:
                return self.get_response(request)

            # 2. IMPORTANTE: Verificar prefijos permitidos ANTES de blocked_prefixes
            # Esto asegura que /settings/licenses/ se permita antes de verificar /settings/
            # Verificar de manera más explícita
            for allowed_prefix in self.allowed_prefixes:
                if path.startswith(allowed_prefix):
                    return self.get_response(request)

            # 3. Verificar si la ruta está bloqueada (solo si no pasó por allowed_prefixes)
            # IMPORTANTE: Verificar blocked_prefixes pero EXCLUIR /settings/licenses/
            for blocked_prefix in self.blocked_prefixes:
                if path.startswith(blocked_prefix):
                    # Excepción: si empieza con /settings/licenses/, ya debería haber sido permitido arriba
                    # pero por si acaso, lo verificamos aquí también
                    if path.startswith("/settings/licenses/"):
                        return self.get_response(request)
                    # Si no es /settings/licenses/, entonces está bloqueado
                    messages.warning(
                        request,
                        "Como administrador de licencias, solo puedes acceder a la gestión de licencias y planes, "
                        "así como a tu perfil y configuración de cuenta.",
                    )
                    return redirect("license_admin_dashboard")


            return redirect("license_admin_dashboard")

        return self.get_response(request)