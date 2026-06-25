from wagtail import hooks
from wagtail.admin.viewsets.model import ModelViewSet
from campegin.models import AdminComplianceTicket
from complaint.models import Complaint, SupportMessage

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

class SupportMessageViewSet(ModelViewSet):
    model = SupportMessage
    url_namespace = "support_message_admin"
    menu_label = "Support Chats"
    icon = "mail"
    menu_icon = "mail"
    menu_item_name = "support_chats"
    add_to_admin_menu = True
    exclude_form_fields = []
    list_display = ("id", "user", "sender_role", "message", "created_at")
    list_filter = ("sender_role",)
    search_fields = ("message", "user__username")

@hooks.register("register_admin_viewset")
def register_compliance_ticket_viewset():
    return AdminComplianceTicketViewSet()

@hooks.register("register_admin_viewset")
def register_complaint_viewset():
    return ComplaintViewSet()

@hooks.register("register_admin_viewset")
def register_support_message_viewset():
    return SupportMessageViewSet()
