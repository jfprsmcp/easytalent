from django.contrib import admin
from .models import LicensePlan, UserLicense

@admin.register(LicensePlan)
class LicensePlanAdmin(admin.ModelAdmin):
    list_display = ('plan_name', 'price_monthly', 'price_yearly', 'currency', 'max_employees', 'is_active', 'created_at')
    search_fields = ('plan_name',)
    list_filter = ('is_active', 'currency')

@admin.register(UserLicense)
class UserLicenseAdmin(admin.ModelAdmin):
    list_display = ('company', 'plan', 'owner', 'license_status', 'is_trial', 'start_date', 'end_date', 'is_active')
    search_fields = ('company__company', 'owner__username')
    list_filter = ('license_status', 'is_trial', 'is_active')
