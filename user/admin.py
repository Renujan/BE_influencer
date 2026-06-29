from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

# Unregister the default UserAdmin
admin.site.unregister(User)

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Only show accounts that do not have an associated Business or Creator profile.
        # This keeps the default "Users" admin list restricted to staff, superusers, and manually-added admin accounts.
        return qs.filter(business_profile__isnull=True, creator_profile__isnull=True)

