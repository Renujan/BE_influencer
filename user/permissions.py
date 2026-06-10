from rest_framework.permissions import BasePermission

class IsNotRestricted(BasePermission):
    """
    Custom permission to block users whose profiles have been restricted.
    """
    def has_permission(self, request, view):
        # Allow non-authenticated requests to pass standard authentication/permission steps.
        # Authenticated requests will be checked for restriction status.
        if not request.user or not request.user.is_authenticated:
            return True
            
        profile = getattr(request.user, "business_profile", None) or getattr(request.user, "creator_profile", None)
        if profile and profile.status == "restricted":
            return False
            
        return True
