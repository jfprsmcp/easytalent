from django.urls import path
from . import views

urlpatterns = [
    # URLs existentes
    path('dashboard/', views.license_dashboard, name='license_dashboard'),
    path('change/', views.change_plan, name='license_change'),
    
    # URLs del panel de administración
    path('admin/', views.admin_dashboard, name='license_admin_dashboard'),
    
    # URLs de gestión de licencias
    path('admin/licenses/', views.license_list, name='admin_license_list'),
    path('admin/licenses/<int:license_id>/edit/', views.license_edit, name='admin_license_edit'),
    path('admin/licenses/<int:license_id>/delete/', views.license_delete, name='admin_license_delete'),
    
    # URLs de gestión de planes
    path('admin/plans/', views.plan_list, name='admin_plan_list'),
    path('admin/plans/create/', views.plan_create, name='admin_plan_create'),
    path('admin/plans/<int:plan_id>/edit/', views.plan_edit, name='admin_plan_edit'),
    path('admin/plans/<int:plan_id>/delete/', views.plan_delete, name='admin_plan_delete'),
]