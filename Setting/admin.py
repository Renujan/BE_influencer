from django.contrib import admin
from .models import CreatorSettings, CreatorPayoutMethod, BusinessSettings

@admin.register(CreatorSettings)
class CreatorSettingsAdmin(admin.ModelAdmin):
    list_display = ("creator", "plan", "currency", "two_factor_enabled")
    search_fields = ("creator__user__username", "creator__user__email")

@admin.register(CreatorPayoutMethod)
class CreatorPayoutMethodAdmin(admin.ModelAdmin):
    list_display = ("creator", "method_type", "details", "is_primary")
    search_fields = ("creator__user__username", "creator__user__email", "method_type")
    list_filter = ("method_type", "is_primary")

@admin.register(BusinessSettings)
class BusinessSettingsAdmin(admin.ModelAdmin):
    list_display = ("business", "plan", "theme", "two_factor_enabled")
    search_fields = ("business__company_name", "business__user__username", "business__user__email")
