from django.contrib import admin
from .models import CreatorSettings, CreatorPayoutMethod, BusinessSettings, BusinessPayoutMethod

@admin.register(CreatorSettings)
class CreatorSettingsAdmin(admin.ModelAdmin):
    list_display = ("creator", "plan", "tax_id", "tax_form_submitted", "currency", "two_factor_enabled")
    search_fields = ("creator__user__username", "creator__user__email", "tax_id")

@admin.register(CreatorPayoutMethod)
class CreatorPayoutMethodAdmin(admin.ModelAdmin):
    list_display = ("creator", "full_name", "bank_name", "account_number", "is_primary")
    search_fields = ("creator__user__username", "creator__user__email", "full_name", "bank_name", "account_number")
    list_filter = ("is_primary",)

@admin.register(BusinessSettings)
class BusinessSettingsAdmin(admin.ModelAdmin):
    list_display = ("business", "plan", "card_last_four", "card_expiry", "theme", "two_factor_enabled")
    search_fields = ("business__company_name", "business__user__username", "business__user__email")

@admin.register(BusinessPayoutMethod)
class BusinessPayoutMethodAdmin(admin.ModelAdmin):
    list_display = ("business", "full_name", "bank_name", "account_number", "is_primary")
    search_fields = ("business__company_name", "business__user__username", "business__user__email", "full_name", "bank_name", "account_number")
    list_filter = ("is_primary",)
