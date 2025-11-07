from django.shortcuts import redirect
from django.utils import timezone
from django.contrib import messages
from .models import UserLicense


class LicenseMiddleware:
    """
    Verifica que la empresa seleccionada tenga licencia activa y no expirada.
    - NO aplica a superusers (bypass completo).
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

        # Excluir peticiones HTMX/AJAX (evita duplicados por carga de widgets)
        if request.headers.get('HX-Request') == 'true' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return self.get_response(request)

        # Solo con sesión iniciada
        if not request.user.is_authenticated:
            return self.get_response(request)

        # BYPASS: Superusers no tienen restricciones de licencia
        if request.user.is_superuser:
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

class SuperuserRestrictionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

        # Rutas completas (nombre reversado → path absoluto)
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

        self.allowed_exact_paths = {
            "/",
            "/dashboard/",
            "/licenses/admin/",
            "/settings/",
        } | resolved_paths  # unimos los paths resueltos

        # Prefijos que siempre deben quedar libres para superusers
        self.allowed_prefixes = (
            "/licenses/admin/",
            "/settings/",
            "/accounts/",           # ← añade todo el árbol de cuentas
            "/static/",
            "/media/",
            "/api/",
        )

    def __call__(self, request):
        if (
            request.user.is_authenticated
            and request.user.is_superuser
            and not request.path.startswith("/admin/")  # Django admin original
        ):
            # Paths exactos permitidos (ej. /accounts/logout/, /accounts/password_change/)
            if request.path in self.allowed_exact_paths:
                return self.get_response(request)

            # Prefijos permitidos (ej. /accounts/…)
            if any(request.path.startswith(prefix) for prefix in self.allowed_prefixes):
                return self.get_response(request)

            # Todo lo demás redirige al dashboard de licencias
            messages.warning(
                request,
                "Como superadministrador, solo puedes acceder a la gestión de licencias y configuraciones.",
            )
            return redirect("license_admin_dashboard")

        return self.get_response(request)