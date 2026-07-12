from django.urls import path
from .analytics_views import creator_analytics

app_name = "analytics"

urlpatterns = [
    path("creator/", creator_analytics, name="creator_analytics"),
]
