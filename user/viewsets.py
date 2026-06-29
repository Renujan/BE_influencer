from wagtail.users.views.users import UserViewSet as WagtailUserViewSet

class CustomUserViewSet(WagtailUserViewSet):
    def get_queryset(self):
        qs = super().get_queryset()
        # Filter out users who have an associated Business or Creator profile.
        # This keeps the Settings > Users admin list restricted to staff, superusers, and manually-added admin accounts.
        return qs.filter(business_profile__isnull=True, creator_profile__isnull=True)
