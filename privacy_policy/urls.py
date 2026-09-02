from django.urls import path
from .views import api_list_privacy_policies

urlpatterns = [
    path("", api_list_privacy_policies, name="api_list_privacy_policies"),
]
