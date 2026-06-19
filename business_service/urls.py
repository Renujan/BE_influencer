from django.urls import path
from .views import api_list_business_services, download_business_service_pdf, api_business_service_inquiries

app_name = "business_service"

urlpatterns = [
    path("", api_list_business_services, name="api_list_business_services_default"),
    path("list/", api_list_business_services, name="api_list_business_services"),
    path("pdf/<int:pk>/", download_business_service_pdf, name="download_business_service_pdf"),
    path("inquiries/", api_business_service_inquiries, name="api_business_service_inquiries"),
]

