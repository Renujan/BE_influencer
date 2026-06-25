from django.shortcuts import redirect
from django.contrib import messages
from wagtail import hooks
from wagtail.admin.viewsets.model import ModelViewSet, ModelViewSetGroup
from wagtail.admin.views.generic.models import InspectView, IndexView
from campegin.models import AdminComplianceTicket
from complaint.models import Complaint, SupportMessage

class AdminComplianceTicketIndexView(IndexView):
    def get_edit_url(self, instance):
        return None

    def get_list_more_buttons(self, instance):
        buttons = super().get_list_more_buttons(instance)
        for item in buttons:
            if hasattr(item, "label") and (str(item.label) == "Inspect" or item.label == "Inspect"):
                item.label = "View"
                item.icon_name = "view"
        return buttons

class AdminComplianceTicketInspectView(InspectView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["instance"] = self.object
        return context

class AdminComplianceTicketViewSet(ModelViewSet):
    model = AdminComplianceTicket
    menu_label = "Compliance & Tickets"
    icon = "lock"
    menu_icon = "lock"
    menu_item_name = "compliance_tickets"
    add_to_admin_menu = False
    exclude_form_fields = []
    inspect_view_enabled = True
    inspect_view_class = AdminComplianceTicketInspectView
    inspect_template_name = "complaint/inspect_ticket.html"
    index_view_class = AdminComplianceTicketIndexView
    edit_view_enabled = False  # Link list table rows to inspect view instead of edit view
    list_display = ("campaign", "category", "status", "date")
    list_filter = ("category", "status")
    search_fields = ("campaign__name", "message")

class ComplaintIndexView(IndexView):
    def get_edit_url(self, instance):
        return None

    def get_list_more_buttons(self, instance):
        buttons = super().get_list_more_buttons(instance)
        for item in buttons:
            if hasattr(item, "label") and (str(item.label) == "Inspect" or item.label == "Inspect"):
                item.label = "View / Review"
                item.icon_name = "view"
        return buttons

class ComplaintInspectView(InspectView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["instance"] = self.object
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        status = request.POST.get("status")
        admin_reply = request.POST.get("admin_reply")

        if status in [choice[0] for choice in self.model.STATUS_CHOICES]:
            self.object.status = status

        self.object.admin_reply = admin_reply or ""
        self.object.save()

        messages.success(request, "Ticket updated successfully.")
        return redirect(self.request.path)

class ComplaintViewSet(ModelViewSet):
    model = Complaint
    url_namespace = "complaint_admin"
    menu_label = "Tickets"
    icon = "warning"
    menu_icon = "warning"
    menu_item_name = "complaints_tickets"
    add_to_admin_menu = False
    exclude_form_fields = []
    create_view_enabled = False  # Disable manual creation, hide add button
    list_display_add_buttons = None  # Hide add button from list display
    inspect_view_enabled = True
    inspect_view_class = ComplaintInspectView
    inspect_template_name = "complaint/inspect_complaint.html"
    index_view_class = ComplaintIndexView
    edit_view_enabled = False  # Link list table rows to inspect view instead of edit view
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
    add_to_admin_menu = False
    exclude_form_fields = []
    list_display = ("id", "user", "sender_role", "message", "created_at")
    list_filter = ("sender_role",)
    search_fields = ("message", "user__username")

class ComplaintGroup(ModelViewSetGroup):
    items = (ComplaintViewSet, SupportMessageViewSet)
    menu_label = "Complaints"
    menu_icon = "warning"
    menu_name = "complaints_group"
    menu_order = 150

@hooks.register("register_admin_viewset")
def register_compliance_ticket_viewset():
    return AdminComplianceTicketViewSet()

@hooks.register("register_admin_viewset")
def register_complaint_group_viewset():
    return ComplaintGroup()
