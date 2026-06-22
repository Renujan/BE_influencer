from django.urls import path
from inquire.views import InquiryCreateView

app_name = "inquire"

urlpatterns = [
    path("", InquiryCreateView.as_view(), name="submit_inquiry_default"),
    path("submit/", InquiryCreateView.as_view(), name="submit_inquiry"),
]
