import re

with open("user/views.py", "r") as f:
    content = f.read()

target = """            else:
                profile = getattr(user, "business_profile", None) or getattr(user, "creator_profile", None)
                if not profile:
                    if role == "business":
                        profile = BusinessProfile.objects.create(user=user)
                    else:
                        profile = CreatorProfile.objects.create(user=user)"""

replacement = """            else:
                profile = getattr(user, "business_profile", None) or getattr(user, "creator_profile", None)
                if profile:
                    actual_role = "business" if hasattr(user, "business_profile") else "influencer"
                    if role != actual_role:
                        role_label = "Business" if role == "business" else "Creator"
                        return Response(
                            {"error": f"This email is already registered as a {'Creator' if actual_role == 'influencer' else 'Business'}. Please use a different email or log in with the correct role."},
                            status=status.HTTP_403_FORBIDDEN
                        )
                if not profile:
                    if role == "business":
                        profile = BusinessProfile.objects.create(user=user)
                    else:
                        profile = CreatorProfile.objects.create(user=user)"""

if target in content:
    content = content.replace(target, replacement)
    with open("user/views.py", "w") as f:
        f.write(content)
    print("Success")
else:
    print("Failed to find target block")
