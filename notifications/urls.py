from django.urls import path
from notifications.views import (
    admin_notifications_view,
    toggle_read_notification,
    delete_notification,
    bulk_action_notification,
    mark_all_read,
    read_and_redirect,
)

app_name = "notifications"

urlpatterns = [
    path("", admin_notifications_view, name="admin_notifications_list"),
    path("toggle-read/<int:pk>/", toggle_read_notification, name="toggle_read"),
    path("delete/<int:pk>/", delete_notification, name="delete_notification"),
    path("bulk-action/", bulk_action_notification, name="bulk_action"),
    path("mark-all-read/", mark_all_read, name="mark_all_read"),
    path("redirect/<int:pk>/", read_and_redirect, name="read_and_redirect"),
]
