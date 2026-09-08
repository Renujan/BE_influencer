from wagtail import hooks
from wagtail.admin.viewsets.model import ModelViewSet, ModelViewSetGroup
from .models import CreatorSettings, BusinessSettings, CreatorPayoutMethod, BusinessPayoutMethod

class CreatorSettingsViewSet(ModelViewSet):
    model = CreatorSettings
    menu_label = "Creator Settings"
    icon = "cog"
    menu_icon = "cog"
    menu_item_name = "creator_settings"
    add_to_admin_menu = False
    exclude_form_fields = []
    list_display = ("creator", "plan", "tax_id", "tax_form_submitted", "currency", "two_factor_enabled")
    search_fields = ("creator__user__username", "creator__user__email")

class BusinessSettingsViewSet(ModelViewSet):
    model = BusinessSettings
    menu_label = "Business Settings"
    icon = "cog"
    menu_icon = "cog"
    menu_item_name = "business_settings"
    add_to_admin_menu = False
    exclude_form_fields = []
    list_display = ("business", "plan", "card_last_four", "card_expiry", "theme", "two_factor_enabled")
    search_fields = ("business__company_name", "business__user__username", "business__user__email")

class CreatorPayoutMethodViewSet(ModelViewSet):
    model = CreatorPayoutMethod
    menu_label = "Creator Payout Methods"
    icon = "credit-card"
    menu_icon = "credit-card"
    menu_item_name = "creator_payout_methods"
    add_to_admin_menu = False
    exclude_form_fields = []
    list_display = ("creator", "full_name", "bank_name", "account_number", "is_primary")
    search_fields = ("creator__user__username", "creator__user__email", "full_name", "bank_name", "account_number")

class BusinessPayoutMethodViewSet(ModelViewSet):
    model = BusinessPayoutMethod
    menu_label = "Business Payout Methods"
    icon = "credit-card"
    menu_icon = "credit-card"
    menu_item_name = "business_payout_methods"
    add_to_admin_menu = False
    exclude_form_fields = []
    list_display = ("business", "full_name", "bank_name", "account_number", "is_primary")
    search_fields = ("business__company_name", "business__user__username", "business__user__email", "full_name", "bank_name", "account_number")

class UserSettingsGroup(ModelViewSetGroup):
    items = (CreatorSettingsViewSet, BusinessSettingsViewSet, CreatorPayoutMethodViewSet, BusinessPayoutMethodViewSet)
    menu_icon = "cog"
    menu_label = "User Settings"
    menu_name = "user_settings"
    menu_order = 160

# @hooks.register("register_admin_viewset")
# def register_user_settings_group():
#     return UserSettingsGroup()

