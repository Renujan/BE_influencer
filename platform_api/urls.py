from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SendOTPView, VerifyOTPView, RegisterView, LoginView, MeView,
    NicheViewSet, CreatorViewSet, CampaignViewSet, RequestViewSet,
    TransactionHistoryViewSet
)

router = DefaultRouter()
router.register(r"niches", NicheViewSet, basename="niche")
router.register(r"creators", CreatorViewSet, basename="creator")
router.register(r"campaigns", CampaignViewSet, basename="campaign")
router.register(r"requests", RequestViewSet, basename="request")
router.register(r"transactions", TransactionHistoryViewSet, basename="transaction")

urlpatterns = [
    # Auth endpoints
    path("auth/send-otp/", SendOTPView.as_view(), name="send_otp"),
    path("auth/verify-otp/", VerifyOTPView.as_view(), name="verify_otp"),
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/signup/", RegisterView.as_view(), name="signup"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/me/", MeView.as_view(), name="me"),
    
    # Include Router viewsets
    path("", include(router.urls)),
]
