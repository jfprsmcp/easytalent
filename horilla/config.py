"""
horilla/config.py

Horilla app configurations
"""

import importlib
import logging

from django.apps import apps
from django.conf import settings
from django.contrib.auth.context_processors import PermWrapper

from horilla.horilla_apps import SIDEBARS
# Remover el import de nivel de módulo para evitar import circular

logger = logging.getLogger(__name__)


def get_apps_in_base_dir():
    return SIDEBARS


def import_method(accessibility):
    module_path, method_name = accessibility.rsplit(".", 1)
    module = __import__(module_path, fromlist=[method_name])
    accessibility_method = getattr(module, method_name)
    return accessibility_method


ALL_MENUS = {}


def sidebar(request):

    base_dir_apps = get_apps_in_base_dir()

    if not request.user.is_anonymous:
        request.MENUS = []
        MENUS = request.MENUS
        
        # IMPORTANTE: 
        # - Superusers ven TODOS los módulos (sin restricciones)
        # - Admins de licencias NO ven módulos de empresa (lista vacía)
        # - Usuarios normales ven solo módulos permitidos por su plan
        
        # Lazy import para evitar import circular durante la inicialización de Django
        from licenses.utils import is_license_admin
        
        if request.user.is_superuser:
            # Superusers ven todos los módulos - no filtrar
            allowed_modules = None  # None = mostrar todos
        elif is_license_admin(request.user):
            # Admins de licencias NO ven módulos de empresa
            allowed_modules = []  # Lista vacía = no mostrar ningún módulo
        else:
            # Obtener módulos permitidos para usuarios normales
            from licenses.utils import get_allowed_modules_for_company
            cid = request.session.get('selected_company')
            if cid:
                from base.models import Company
                company = Company.objects.filter(id=cid).first()
                if company:
                    allowed_modules = get_allowed_modules_for_company(company)
                else:
                    allowed_modules = []
            else:
                allowed_modules = []

        # Procesar el sidebar de 'licenses' primero (siempre se muestra si cumple accesibilidad)
        # Este menú es especial porque muestra información de la empresa, no es un módulo de empresa
        if apps.is_installed("licenses"):
            try:
                licenses_sidebar = importlib.import_module("licenses.sidebar")
                if licenses_sidebar:
                    accessibility = None
                    if getattr(licenses_sidebar, "ACCESSIBILITY", None):
                        accessibility = import_method(licenses_sidebar.ACCESSIBILITY)

                    if hasattr(licenses_sidebar, "MENU") and (
                        not accessibility
                        or accessibility(
                            request,
                            licenses_sidebar.MENU,
                            PermWrapper(request.user),
                        )
                    ):
                        MENU = {}
                        MENU["menu"] = licenses_sidebar.MENU
                        MENU["app"] = "licenses"
                        MENU["img_src"] = licenses_sidebar.IMG_SRC
                        MENU["submenu"] = []
                        MENUS.append(MENU)
                        
                        # Obtener submenús (dinámicos o estáticos)
                        submenus_to_process = []
                        if hasattr(licenses_sidebar, 'get_submenus'):
                            # Si existe función get_submenus, usarla para generar submenús dinámicamente
                            try:
                                submenus_to_process = licenses_sidebar.get_submenus(request)
                            except Exception as e:
                                logger.error(f"Error generating dynamic submenus for licenses: {e}")
                                submenus_to_process = getattr(licenses_sidebar, 'SUBMENUS', [])
                        else:
                            # Usar SUBMENUS estáticos
                            submenus_to_process = getattr(licenses_sidebar, 'SUBMENUS', [])
                        
                        for submenu in submenus_to_process:
                            accessibility = None

                            if submenu.get("accessibility"):
                                accessibility = import_method(submenu["accessibility"])
                            redirect: str = submenu["redirect"]
                            redirect = redirect.split("?")
                            submenu["redirect"] = redirect[0]

                            if not accessibility or accessibility(
                                request,
                                submenu,
                                PermWrapper(request.user),
                            ):
                                MENU["submenu"].append(submenu)
            except Exception as e:
                logger.error(f"Error loading licenses sidebar: {e}")

        # Procesar los demás módulos
        for app in base_dir_apps:
            # Saltar 'licenses' porque ya se procesó arriba
            if app == "licenses":
                continue
                
            if apps.is_installed(app):
                # Si allowed_modules es None (superuser), mostrar todos los módulos
                if allowed_modules is not None and app not in allowed_modules:
                    continue  # Saltar este módulo si no está permitido
                
                try:
                    sidebar = importlib.import_module(app + ".sidebar")

                except Exception as e:
                    logger.error(e)
                    continue

                if sidebar:
                    accessibility = None
                    if getattr(sidebar, "ACCESSIBILITY", None):
                        accessibility = import_method(sidebar.ACCESSIBILITY)

                    if hasattr(sidebar, "MENU") and (
                        not accessibility
                        or accessibility(
                            request,
                            sidebar.MENU,
                            PermWrapper(request.user),
                        )
                    ):
                        MENU = {}
                        MENU["menu"] = sidebar.MENU
                        MENU["app"] = app
                        MENU["img_src"] = sidebar.IMG_SRC
                        MENU["submenu"] = []
                        MENUS.append(MENU)
                        
                        # Obtener submenús (dinámicos o estáticos)
                        submenus_to_process = []
                        if hasattr(sidebar, 'get_submenus'):
                            # Si existe función get_submenus, usarla para generar submenús dinámicamente
                            try:
                                submenus_to_process = sidebar.get_submenus(request)
                            except Exception as e:
                                logger.error(f"Error generating dynamic submenus for {app}: {e}")
                                submenus_to_process = getattr(sidebar, 'SUBMENUS', [])
                        else:
                            # Usar SUBMENUS estáticos
                            submenus_to_process = getattr(sidebar, 'SUBMENUS', [])
                        
                        for submenu in submenus_to_process:
                            accessibility = None

                            if submenu.get("accessibility"):
                                accessibility = import_method(submenu["accessibility"])
                            redirect: str = submenu["redirect"]
                            redirect = redirect.split("?")
                            submenu["redirect"] = redirect[0]

                            if not accessibility or accessibility(
                                request,
                                submenu,
                                PermWrapper(request.user),
                            ):
                                MENU["submenu"].append(submenu)
        ALL_MENUS[request.session.session_key] = MENUS


def get_MENUS(request):
    ALL_MENUS[request.session.session_key] = []
    sidebar(request)
    return {"sidebar": ALL_MENUS.get(request.session.session_key)}
