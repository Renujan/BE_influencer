from django.urls import path
from FAQ.views import api_list_faq

app_name = "FAQ"

urlpatterns = [
    path("", api_list_faq, name="api_list_faq_default"),
    path("list/", api_list_faq, name="api_list_faq"),
]
