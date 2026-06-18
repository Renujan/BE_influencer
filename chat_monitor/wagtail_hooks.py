from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.translation import gettext as _
from wagtail import hooks
from wagtail.admin.viewsets.model import ModelViewSet
from wagtail.admin.views.generic.models import IndexView, MenuItem as GenericMenuItem
from campegin.models import Campaign
from .views import chat_monitor_view_chat_view, chat_monitor_review_view, chat_monitor_detail_view


# Custom Index View: adds "View Campaign" and "Download PDF" to the row dropdown menu
class ChatMonitorIndexView(IndexView):
    def get_list_more_buttons(self, instance):
        buttons = super().get_list_more_buttons(instance)

        # Add "View" — comprehensive detail page (chat + campaign + profiles)
        try:
            detail_url = reverse("chat_monitor_detail", args=[instance.pk])
            buttons.append(
                GenericMenuItem(
                    _("View"),
                    url=detail_url,
                    icon_name="view",
                    priority=30,
                )
            )
        except Exception:
            pass

        # Add "Download PDF"
        try:
            pdf_url = reverse("download_campaign_pdf", args=[instance.pk])
            buttons.append(
                GenericMenuItem(
                    _("Download PDF"),
                    url=pdf_url,
                    icon_name="download",
                    priority=35,
                )
            )
        except Exception:
            pass

        return buttons


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

    # Use our custom index view for the dropdown additions
    index_view_class = ChatMonitorIndexView

    # "View Chat" and "Review" stay as inline buttons; campaign detail and PDF go into the dropdown
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
        path("chat-monitor/detail/<int:campaign_id>/", chat_monitor_detail_view, name="chat_monitor_detail"),
    ]
