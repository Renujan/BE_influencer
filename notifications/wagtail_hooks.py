from django.urls import path, reverse
from wagtail import hooks
from wagtail.admin.menu import MenuItem
from wagtail.admin.viewsets.model import ModelViewSet
from notifications.models import Notification


class NotificationViewSet(ModelViewSet):
    model = Notification
    menu_label = "Notifications Log"
    menu_icon = "bell"
    menu_item_name = "notifications_log"
    add_to_admin_menu = False
    exclude_form_fields = []
    create_view_enabled = False  # Disable manual creation
    list_display_add_buttons = None
    list_display = ("title", "category", "message", "is_read", "created_at")
    list_filter = ("category", "is_read")
    search_fields = ("title", "message")

    @property
    def permission_policy(self):
        from wagtail.permissions import ModelPermissionPolicy

        class NoAddNotificationPermissionPolicy(ModelPermissionPolicy):
            def user_has_permission(self, user, action):
                if action == "add":
                    return False
                return super().user_has_permission(user, action)

        return NoAddNotificationPermissionPolicy(self.model)


@hooks.register("register_admin_viewset")
def register_notification_viewset():
    return NotificationViewSet()


@hooks.register("register_icons")
def register_notification_icons(icons):
    return icons + ["wagtailadmin/icons/bell.svg"]


@hooks.register("register_admin_urls")
def register_notifications_admin_urls():
    from notifications.views import admin_notifications_view

    return [
        path("notifications-panel/", admin_notifications_view, name="admin_notifications_panel"),
    ]


@hooks.register("register_admin_menu_item")
def register_notifications_menu_item():
    """
    Register dedicated 'Notifications' menu item in Super Admin sidebar.
    Placed with order 160 immediately after Complaints (order 150).
    """
    return MenuItem(
        "Notifications",
        reverse("notifications:admin_notifications_list"),
        icon_name="bell",
        order=160,
        name="notifications",
    )


@hooks.register("construct_main_menu", order=100)
def order_notifications_after_complaints(request, menu_items):
    """
    Ensure the Notifications navigation link is positioned immediately
    after the 'Complaints' section in the Super Admin sidebar.
    """
    notif_item = None
    complaints_idx = None
    for i, item in enumerate(menu_items):
        if getattr(item, "name", "") in ["notifications", "notifications_list"] or getattr(item, "label", "") == "Notifications":
            notif_item = item
        elif getattr(item, "name", "") == "complaints_group" or getattr(item, "label", "") == "Complaints":
            complaints_idx = i

    if notif_item and complaints_idx is not None:
        menu_items.remove(notif_item)
        for i, item in enumerate(menu_items):
            if getattr(item, "name", "") == "complaints_group" or getattr(item, "label", "") == "Complaints":
                complaints_idx = i
                break
        menu_items.insert(complaints_idx + 1, notif_item)
