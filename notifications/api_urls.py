from django.urls import path
from .api_views import get_notifications, mark_read, mark_all_read_api

app_name = "notifications_api"

urlpatterns = [
    path("", get_notifications, name="get_notifications"),
    path("<int:pk>/read/", mark_read, name="mark_read"),
    path("read-all/", mark_all_read_api, name="mark_all_read_api"),
]
