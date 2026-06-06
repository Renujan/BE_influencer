from wagtail import hooks
from wagtail.admin.viewsets.model import ModelViewSet
from wagtail.admin.menu import MenuItem
from wagtail.admin.views.generic import IndexView, InspectView
from django.urls import reverse
from django.db.models import Sum, Avg
from .models import UserProfile, Campaign, AdminComplianceTicket
from complaint.models import Complaint

# 1. Custom Django Admin Views & Viewsets
class CustomUserProfileIndexView(IndexView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Calculate real-time statistics based on the queryset (supporting search and filters)
        queryset = self.get_queryset()
        
        total_profiles = queryset.count()
        total_creators = queryset.filter(role="influencer").count()
        total_brands = queryset.filter(role="business").count()
        
        # Wallet metrics
        total_balance = queryset.aggregate(total=Sum('wallet_balance'))['total'] or 0.0
        avg_balance = queryset.aggregate(avg=Avg('wallet_balance'))['avg'] or 0.0
        
        # OTP verification rate
        verified_count = queryset.filter(otp_verified=True).count()
        otp_verified_rate = int((verified_count / total_profiles * 100)) if total_profiles > 0 else 0
        
        context.update({
            'total_profiles': total_profiles,
            'total_creators': total_creators,
            'total_brands': total_brands,
            'total_balance': float(total_balance),
            'avg_balance': float(avg_balance),
            'otp_verified_rate': otp_verified_rate,
        })
        return context

class CustomUserProfileInspectView(InspectView):
    pass

class CustomCampaignIndexView(IndexView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        
        total_campaigns = queryset.count()
        live_campaigns = queryset.filter(status="Live").count()
        completed_campaigns = queryset.filter(status="Completed").count()
        pending_campaigns = queryset.filter(status="Pending").count()
        
        total_budget = queryset.aggregate(total=Sum('budget'))['total'] or 0.0
        avg_progress = queryset.aggregate(avg=Avg('progress'))['avg'] or 0.0
        
        context.update({
            'total_campaigns': total_campaigns,
            'live_campaigns': live_campaigns,
            'completed_campaigns': completed_campaigns,
            'pending_campaigns': pending_campaigns,
            'total_budget': float(total_budget),
            'avg_progress': float(avg_progress),
        })
        return context

class CustomCampaignInspectView(InspectView):
    pass

class CustomComplaintIndexView(IndexView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        
        total_tickets = queryset.count()
        pending_tickets = queryset.filter(status="pending").count()
        investigating_tickets = queryset.filter(status="investigating").count()
        resolved_tickets = queryset.filter(status="resolved").count()
        dismissed_tickets = queryset.filter(status="dismissed").count()
        
        context.update({
            'total_tickets': total_tickets,
            'pending_tickets': pending_tickets,
            'investigating_tickets': investigating_tickets,
            'resolved_tickets': resolved_tickets,
            'dismissed_tickets': dismissed_tickets,
        })
        return context

class CustomComplaintInspectView(InspectView):
    pass

class UserProfileViewSet(ModelViewSet):
    model = UserProfile
    menu_label = "User Profiles"
    menu_icon = "user"
    menu_item_name = "user_profiles"
    add_to_admin_menu = True
    exclude_form_fields = []
    create_view_enabled = False  # Disable manual creation, hide add button
    list_display_add_buttons = None  # Hide the add button from list display header
    list_display = ("user", "role", "phone", "otp_verified", "is_approved", "average_rate", "get_details", "wallet_balance")
    list_export = ("id", "user__username", "user__email", "role", "phone", "location", "wallet_balance", "otp_verified", "is_approved", "average_rate", "company_name", "business_type", "website")
    list_filter = ("role", "otp_verified", "is_approved")
    search_fields = ("user__username", "user__email", "company_name", "phone")

    # Custom views and template overrides
    inspect_view_enabled = True
    index_view_class = CustomUserProfileIndexView
    inspect_view_class = CustomUserProfileInspectView
    index_template_name = "wagtailadmin/user_profiles/index.html"
    inspect_template_name = "wagtailadmin/user_profiles/inspect.html"

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
    menu_icon = "tasks"
    menu_item_name = "campaigns"
    add_to_admin_menu = True
    exclude_form_fields = []
    list_display = ("name", "brand", "creator", "status", "budget", "progress")
    list_export = ("id", "name", "brand__username", "creator__username", "status", "budget", "start_date", "progress")
    list_filter = ("status",)
    search_fields = ("name", "brand__username", "creator__username")

    # Custom views and template overrides
    inspect_view_enabled = True
    index_view_class = CustomCampaignIndexView
    inspect_view_class = CustomCampaignInspectView
    index_template_name = "wagtailadmin/campaigns/index.html"
    inspect_template_name = "wagtailadmin/campaigns/inspect.html"

class AdminComplianceTicketViewSet(ModelViewSet):
    model = AdminComplianceTicket
    menu_label = "Compliance & Tickets"
    menu_icon = "lock"
    menu_item_name = "compliance_tickets"
    add_to_admin_menu = False
    exclude_form_fields = []
    list_display = ("campaign", "category", "status", "date")
    list_filter = ("category", "status")
    search_fields = ("campaign__name", "message")

class ComplaintViewSet(ModelViewSet):
    model = Complaint
    menu_label = "Complaints & Tickets"
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

    # Custom views and template overrides
    inspect_view_enabled = True
    index_view_class = CustomComplaintIndexView
    inspect_view_class = CustomComplaintInspectView
    index_template_name = "wagtailadmin/complaints/index.html"
    inspect_template_name = "wagtailadmin/complaints/inspect.html"

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

# Trigger dev server reload to refresh template cache - campaigns & tickets added
