from django.urls import path
from .views import api_list_guides

urlpatterns = [
    path("", api_list_guides, name="api_list_guides"),
]
