from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SendOTPView, VerifyOTPView, RegisterView, LoginView, MeView,
    NicheViewSet, BusinessTypeViewSet, CreatorViewSet, PendingUsersView, ApproveUserView, RestrictUserView,
    SubmitVerificationView, CreatorSubmitVerificationView
)

router = DefaultRouter()
router.register(r"niches", NicheViewSet, basename="niche")
router.register(r"business-types", BusinessTypeViewSet, basename="business-type")
router.register(r"creators", CreatorViewSet, basename="creator")

urlpatterns = [
    # Auth endpoints
    path("auth/send-otp/", SendOTPView.as_view(), name="send_otp"),
    path("auth/verify-otp/", VerifyOTPView.as_view(), name="verify_otp"),
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/signup/", RegisterView.as_view(), name="signup"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/me/", MeView.as_view(), name="me"),
    path("auth/business/submit-verification/", SubmitVerificationView.as_view(), name="submit_verification"),
    path("auth/creator/submit-verification/", CreatorSubmitVerificationView.as_view(), name="creator_submit_verification"),

    
    # Admin Moderation endpoints
    path("admin/pending-users/", PendingUsersView.as_view(), name="admin_pending_users"),
    path("admin/approve-user/", ApproveUserView.as_view(), name="admin_approve_user"),
    path("admin/restrict-user/", RestrictUserView.as_view(), name="admin_restrict_user"),
    
    # Include Router viewsets
    path("", include(router.urls)),
]
