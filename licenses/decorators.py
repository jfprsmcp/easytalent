from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse

def superuser_required(view_func):
    """
    Decorador que verifica que el usuario sea superuser.
    Si no lo es, redirige al dashboard normal.
    """
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())
        
        if not request.user.is_superuser:
            messages.error(request, 'No tienes permisos para acceder a esta sección.')
            return redirect('home-page')
        
        return view_func(request, *args, **kwargs)
    return wrapped_view