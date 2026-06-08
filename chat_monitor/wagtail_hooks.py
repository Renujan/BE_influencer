from django.urls import path, reverse
from django.utils.html import format_html
from wagtail import hooks
from wagtail.admin.viewsets.model import ModelViewSet
from campegin.models import Campaign
from .views import chat_monitor_view_chat_view, chat_monitor_review_view

class ChatMonitorCampaignViewSet(ModelViewSet):
    model = Campaign
    menu_label = "Chat Monitor"
    icon = "mail"
    menu_icon = "mail"
    menu_item_name = "chat_monitor"
    url_prefix = "chat-monitor"
    url_namespace = "chat_monitor_campaigns"
    add_to_admin_menu = True
    create_view_enabled = False
    list_display_add_buttons = None
    exclude_form_fields = []
    list_display = ("get_business_name", "get_creator_name", "get_last_chat_time", "get_view_chat_btn", "get_review_btn")
    list_export = ("name", "brand__username", "creator__username", "status", "budget", "progress")

    @property
    def permission_policy(self):
        from wagtail.permissions import ModelPermissionPolicy
        
        class NoModifyPermissionPolicy(ModelPermissionPolicy):
            def user_has_permission(self, user, action):
                if action in ("add", "edit", "delete"):
                    return False
                return super().user_has_permission(user, action)
        
        return NoModifyPermissionPolicy(self.model)


@hooks.register("register_admin_viewset")
def register_chat_monitor_viewset():
    return ChatMonitorCampaignViewSet()

@hooks.register("register_admin_urls")
def register_chat_monitor_custom_urls():
    return [
        path("chat-monitor/view-chat/<int:campaign_id>/", chat_monitor_view_chat_view, name="chat_monitor_view_chat"),
        path("chat-monitor/review/<int:campaign_id>/", chat_monitor_review_view, name="chat_monitor_review"),
    ]
