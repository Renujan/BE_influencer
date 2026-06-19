from django.urls import path
from notifications.views import mark_all_read, read_and_redirect

app_name = "notifications"

urlpatterns = [
    path("mark-all-read/", mark_all_read, name="mark_all_read"),
    path("redirect/<int:pk>/", read_and_redirect, name="read_and_redirect"),
]

