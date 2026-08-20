from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SendOTPView, VerifyOTPView, RegisterView, LoginView, GoogleLoginView, MeView,
    NicheViewSet, BusinessTypeViewSet, CountryViewSet, MediumViewSet, CreatorViewSet, BusinessViewSet, PendingUsersView, ApproveUserView, RestrictUserView,
    SubmitVerificationView, CreatorSubmitVerificationView, WithdrawFundsView, toggle_save_brand,
    RequestCreatorDeletionView, CancelCreatorDeletionView, AdminHandleCreatorDeletionView,
    RequestBusinessDeletionView, CancelBusinessDeletionView, AdminHandleBusinessDeletionView
)
from .geo_views import external_countries, currency, states, cities

router = DefaultRouter()
router.register(r"niches", NicheViewSet, basename="niche")
router.register(r"business-types", BusinessTypeViewSet, basename="business-type")
router.register(r"countries", CountryViewSet, basename="country")
router.register(r"mediums", MediumViewSet, basename="medium")
router.register(r"creators", CreatorViewSet, basename="creator")
router.register(r"businesses", BusinessViewSet, basename="business")

urlpatterns = [
    # Auth endpoints
    path("auth/send-otp/", SendOTPView.as_view(), name="send_otp"),
    path("auth/verify-otp/", VerifyOTPView.as_view(), name="verify_otp"),
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/signup/", RegisterView.as_view(), name="signup"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/google/", GoogleLoginView.as_view(), name="google_login"),
    path("auth/me/", MeView.as_view(), name="me"),
    path("auth/business/submit-verification/", SubmitVerificationView.as_view(), name="submit_verification"),
    path("auth/creator/submit-verification/", CreatorSubmitVerificationView.as_view(), name="creator_submit_verification"),
    path("auth/withdraw/", WithdrawFundsView.as_view(), name="withdraw"),

    # Creator Account Deletion Request endpoints
    path("creator/request-deletion/", RequestCreatorDeletionView.as_view(), name="creator_request_deletion"),
    path("creator/cancel-deletion/", CancelCreatorDeletionView.as_view(), name="creator_cancel_deletion"),
    path("admin/handle-creator-deletion/", AdminHandleCreatorDeletionView.as_view(), name="admin_handle_creator_deletion"),

    # Business Account Deletion Request endpoints
    path("business/request-deletion/", RequestBusinessDeletionView.as_view(), name="business_request_deletion"),
    path("business/cancel-deletion/", CancelBusinessDeletionView.as_view(), name="business_cancel_deletion"),
    path("admin/handle-business-deletion/", AdminHandleBusinessDeletionView.as_view(), name="admin_handle_business_deletion"),

    # Geo Proxy endpoints
    path("geo/countries/", external_countries, name="external_countries"),
    path("currency/<str:country_name>/", currency, name="geo_currency"),
    path("states/<str:country_name>/", states, name="geo_states"),
    path("cities/<str:country_name>/<str:state_name>/", cities, name="geo_cities"),

    # Admin Moderation endpoints
    path("admin/pending-users/", PendingUsersView.as_view(), name="admin_pending_users"),
    path("admin/approve-user/", ApproveUserView.as_view(), name="admin_approve_user"),
    path("admin/restrict-user/", RestrictUserView.as_view(), name="admin_restrict_user"),
    
    path("creators/save-brand/", toggle_save_brand, name="toggle_save_brand"),
    
    # Include Router viewsets
    path("", include(router.urls)),
]
