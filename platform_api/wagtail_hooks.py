from wagtail import hooks
from wagtail.admin.viewsets.model import ModelViewSet
from wagtail.admin.menu import MenuItem
from django.urls import reverse
from .models import UserProfile, Campaign, AdminComplianceTicket
from complaint.models import Complaint

# 1. Custom Django Admin Viewsets
class UserProfileViewSet(ModelViewSet):
    model = UserProfile
    menu_label = "User Profiles"
    icon = "user"
    menu_icon = "user"
    menu_item_name = "user_profiles"
    add_to_admin_menu = True
    exclude_form_fields = []
    create_view_enabled = False  # Disable manual creation, hide add button
    list_display_add_buttons = None  # Hide the add button from list display header
    list_display = ("user", "role", "phone", "otp_verified", "get_details", "wallet_balance")
    list_export = ("id", "user__username", "user__email", "role", "phone", "location", "wallet_balance", "otp_verified", "company_name", "business_type", "website")
    list_filter = ("role", "otp_verified")
    search_fields = ("user__username", "user__email", "company_name", "phone")

    @property
    def permission_policy(self):
        from wagtail.permissions import ModelPermissionPolicy
        
        class NoAddUserProfilePermissionPolicy(ModelPermissionPolicy):
            def user_has_permission(self, user, action):
                if action == "add":
                    return False
                return super().user_has_permission(user, action)
        
        return NoAddUserProfilePermissionPolicy(self.model)

class CampaignViewSet(ModelViewSet):
    model = Campaign
    menu_label = "Campaign Workspaces"
    icon = "tasks"
    menu_icon = "tasks"
    menu_item_name = "campaigns"
    add_to_admin_menu = True
    create_view_enabled = False
    exclude_form_fields = []
    list_display = ("name", "brand", "creator", "status", "budget", "progress")
    list_export = ("id", "name", "brand__username", "creator__username", "status", "budget", "start_date", "progress")
    list_filter = ("status",)
    search_fields = ("name", "brand__username", "creator__username")

class AdminComplianceTicketViewSet(ModelViewSet):
    model = AdminComplianceTicket
    menu_label = "Compliance & Tickets"
    icon = "lock"
    menu_icon = "lock"
    menu_item_name = "compliance_tickets"
    add_to_admin_menu = False
    exclude_form_fields = []
    list_display = ("campaign", "category", "status", "date")
    list_filter = ("category", "status")
    search_fields = ("campaign__name", "message")

class ComplaintViewSet(ModelViewSet):
    model = Complaint
    url_namespace = "complaint_admin"
    menu_label = "Complaints & Tickets"
    icon = "warning"
    menu_icon = "warning"
    menu_item_name = "complaints_tickets"
    add_to_admin_menu = True
    exclude_form_fields = []
    create_view_enabled = False  # Disable manual creation, hide add button
    list_display_add_buttons = None  # Hide add button from list display
    list_display = ("id", "user", "category", "subject", "status", "created_at")
    list_export = ("id", "user__username", "campaign__name", "category", "subject", "description", "status", "admin_reply", "created_at")
    list_filter = ("status", "category")
    search_fields = ("subject", "description", "user__username")

    @property
    def permission_policy(self):
        from wagtail.permissions import ModelPermissionPolicy
        
        class NoAddComplaintPermissionPolicy(ModelPermissionPolicy):
            def user_has_permission(self, user, action):
                if action == "add":
                    return False
                return super().user_has_permission(user, action)
        
        return NoAddComplaintPermissionPolicy(self.model)

# 2. Register Viewsets
@hooks.register("register_admin_viewset")
def register_user_profile_viewset():
    return UserProfileViewSet()

@hooks.register("register_admin_viewset")
def register_campaign_viewset():
    return CampaignViewSet()

@hooks.register("register_admin_viewset")
def register_compliance_ticket_viewset():
    return AdminComplianceTicketViewSet()

@hooks.register("register_admin_viewset")
def register_complaint_viewset():
    return ComplaintViewSet()

@hooks.register('register_admin_menu_item')
def register_main_admin_menu_item():
    return MenuItem(
        'Dashboard',
        reverse('wagtailadmin_home'),
        icon_name='home',
        order=1
    )

@hooks.register('construct_main_menu')
def hide_unwanted_menu_items(request, menu_items):
    print("SIDEBAR MENU ITEMS:", [item.name for item in menu_items])
    # Hide reports, images, documents, help, explorer (Pages), and snippets items from the main menu sidebar
    menu_items[:] = [item for item in menu_items if item.name not in ['reports', 'images', 'documents', 'help', 'explorer', 'snippets']]

@hooks.register('construct_settings_menu')
def hide_unwanted_settings_menu_items(request, menu_items):
    # Keep only users and groups inside the settings menu
    menu_items[:] = [item for item in menu_items if item.name in ['users', 'groups']]
