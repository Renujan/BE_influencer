from django.urls import path
from notifications.views import mark_all_read

app_name = "notifications"

urlpatterns = [
    path("mark-all-read/", mark_all_read, name="mark_all_read"),
]
