from django.urls import path
from complaint.views import api_create_complaint, api_list_complaints

app_name = "complaint"

urlpatterns = [
    path("create/", api_create_complaint, name="api_create_complaint"),
    path("list/", api_list_complaints, name="api_list_complaints"),
]
