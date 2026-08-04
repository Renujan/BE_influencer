from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CampaignViewSet, RequestViewSet, CampaignSettingsView, CampaignStatsView, PitchViewSet, CreatorEarningsView, BusinessAnalyticsView, CampaignCategoryApiViewSet, CampaignNicheViewSet, CampaignDeliverableApiViewSet

router = DefaultRouter()
router.register(r"campaigns", CampaignViewSet, basename="campaign")
router.register(r"requests", RequestViewSet, basename="request")
router.register(r"pitches", PitchViewSet, basename="pitch")
router.register(r"categories", CampaignCategoryApiViewSet, basename="campaign-category")
router.register(r"campaign-niches", CampaignNicheViewSet, basename="campaign-niche")
router.register(r"deliverables", CampaignDeliverableApiViewSet, basename="campaign-deliverable")

urlpatterns = [
    path("campaign-settings/", CampaignSettingsView.as_view(), name="campaign-settings"),
    path("campaign-stats/", CampaignStatsView.as_view(), name="campaign-stats"),
    path("business-analytics/", BusinessAnalyticsView.as_view(), name="business-analytics"),
    path("creator-earnings/", CreatorEarningsView.as_view(), name="creator-earnings"),
    path("", include(router.urls)),
]
