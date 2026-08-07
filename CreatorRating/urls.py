from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CreatorRatingViewSet

router = DefaultRouter()
router.register(r"", CreatorRatingViewSet, basename="creator-rating")

urlpatterns = [
    path("", include(router.urls)),
]
