from wagtail import hooks
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
