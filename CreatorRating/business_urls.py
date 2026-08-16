from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BusinessRatingViewSet

router = DefaultRouter()
router.register(r"", BusinessRatingViewSet, basename="business-rating")

urlpatterns = [
    path("", include(router.urls)),
]
