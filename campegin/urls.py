from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CampaignViewSet, RequestViewSet, CampaignSettingsView

router = DefaultRouter()
router.register(r"campaigns", CampaignViewSet, basename="campaign")
router.register(r"requests", RequestViewSet, basename="request")

urlpatterns = [
    path("campaign-settings/", CampaignSettingsView.as_view(), name="campaign-settings"),
    path("", include(router.urls)),
]
