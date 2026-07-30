from rest_framework.routers import DefaultRouter
from .views import RateCardViewSet

router = DefaultRouter()
router.register(r"", RateCardViewSet, basename="rate-card")

urlpatterns = router.urls
