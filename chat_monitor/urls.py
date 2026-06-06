from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CampaignChatsViewSet

router = DefaultRouter()
router.register(r"campaigns", CampaignChatsViewSet, basename="chat-campaign")

urlpatterns = [
    path("", include(router.urls)),
]
