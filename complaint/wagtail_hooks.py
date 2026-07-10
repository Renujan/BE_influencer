from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse
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
    list_export = ("id", "user.username", "campaign.name", "category", "subject", "description", "status", "admin_reply", "created_at")
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

class SupportMessageIndexView(IndexView):
    def get_queryset(self):
        from django.db.models import Max
        # Fetch only the latest SupportMessage ID for each user to group chat threads
        latest_ids = SupportMessage.objects.values("user").annotate(latest_id=Max("id")).values_list("latest_id", flat=True)
        return SupportMessage.objects.filter(id__in=latest_ids).order_by("-created_at")

    def get_edit_url(self, instance):
        return None

    def get_list_more_buttons(self, instance):
        buttons = super().get_list_more_buttons(instance)
        for item in buttons:
            if hasattr(item, "label") and (str(item.label) == "Inspect" or item.label == "Inspect"):
                item.label = "Chat"
                item.icon_name = "comment"
        return buttons

class SupportMessageInspectView(InspectView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["instance"] = self.object
        target_user = self.object.user
        profile_url = None
        
        # Determine the user's Wagtail admin inspect page URL based on role
        if hasattr(target_user, "business_profile") and target_user.business_profile:
            profile_url = reverse("businessprofile:inspect", args=[target_user.business_profile.pk])
        elif hasattr(target_user, "creator_profile") and target_user.creator_profile:
            profile_url = reverse("creatorprofile:inspect", args=[target_user.creator_profile.pk])
        else:
            profile_url = reverse("wagtailusers_users:edit", args=[target_user.pk])

        context["profile_url"] = profile_url
        # Retrieve complete chronological conversation history for this user
        context["chat_messages"] = SupportMessage.objects.filter(user=target_user).order_by("created_at")
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        action = request.POST.get("action", "send_msg")

        if action == "delete_chat":
            # Delete whole chat history for this user
            SupportMessage.objects.filter(user=self.object.user).delete()
            messages.success(request, "Conversation cleared successfully.")
            return redirect(reverse("support_message_admin:index"))

        elif action == "delete_msg":
            # Delete single message
            message_id = request.POST.get("message_id")
            SupportMessage.objects.filter(id=message_id, user=self.object.user).delete()
            messages.success(request, "Message deleted.")
            return redirect(self.request.path)

        elif action == "edit_msg":
            # Edit single message content
            message_id = request.POST.get("message_id")
            new_text = request.POST.get("message", "").strip()
            SupportMessage.objects.filter(id=message_id, user=self.object.user).update(message=new_text)
            messages.success(request, "Message updated.")
            return redirect(self.request.path)

        else:
            # Send new message/media (default action)
            message_text = request.POST.get("message", "").strip()
            attachment_file = request.FILES.get("attachment")
            is_voice_val = request.POST.get("is_voice") == "true"

            if message_text or attachment_file:
                SupportMessage.objects.create(
                    user=self.object.user,
                    sender_role="admin",
                    message=message_text,
                    attachment=attachment_file,
                    is_voice=is_voice_val
                )
                messages.success(request, "Message sent.")
            return redirect(self.request.path)

class SupportMessageViewSet(ModelViewSet):
    model = SupportMessage
    url_namespace = "support_message_admin"
    menu_label = "Support Chats"
    icon = "mail"
    menu_icon = "mail"
    menu_item_name = "support_chats"
    add_to_admin_menu = False
    exclude_form_fields = []
    inspect_view_enabled = True
    inspect_view_class = SupportMessageInspectView
    inspect_template_name = "complaint/inspect_support_chat.html"
    index_view_class = SupportMessageIndexView
    edit_view_enabled = False
    create_view_enabled = False  # Hides 'Add support message' button
    list_display_add_buttons = None
    list_display = ("id", "user", "get_thread_sender_role", "message", "created_at")
    list_filter = ()
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
