from django.contrib import admin
from .models import CreatorSettings, CreatorPayoutMethod, BusinessSettings, BusinessPayoutMethod

@admin.register(CreatorSettings)
class CreatorSettingsAdmin(admin.ModelAdmin):
    list_display = ("creator", "plan", "currency", "two_factor_enabled")
    search_fields = ("creator__user__username", "creator__user__email")

@admin.register(CreatorPayoutMethod)
class CreatorPayoutMethodAdmin(admin.ModelAdmin):
    list_display = ("creator", "bank_name", "account_number", "is_primary")
    search_fields = ("creator__user__username", "creator__user__email", "bank_name")
    list_filter = ("is_primary",)

@admin.register(BusinessSettings)
class BusinessSettingsAdmin(admin.ModelAdmin):
    list_display = ("business", "plan", "theme", "two_factor_enabled")
    search_fields = ("business__company_name", "business__user__username", "business__user__email")

@admin.register(BusinessPayoutMethod)
class BusinessPayoutMethodAdmin(admin.ModelAdmin):
    list_display = ("business", "bank_name", "account_number", "is_primary")
    search_fields = ("business__company_name", "business__user__username", "business__user__email", "bank_name")
    list_filter = ("is_primary",)
