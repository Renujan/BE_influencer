from django.urls import path
from terms.views import api_list_terms

app_name = "terms"

urlpatterns = [
    path("", api_list_terms, name="api_list_terms_default"),
    path("list/", api_list_terms, name="api_list_terms"),
]
