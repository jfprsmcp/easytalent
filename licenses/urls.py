from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.license_dashboard, name='license_dashboard'),
    path('change/', views.change_plan, name='license_change'),
]