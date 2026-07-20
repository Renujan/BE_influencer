import re

with open("user/views.py", "r") as f:
    content = f.read()

target = """            # Validate role against the actual account type
            actual_role = "business" if hasattr(user, "business_profile") else "influencer"
            if requested_role != actual_role:
                role_label = "Business" if requested_role == "business" else "Creator"
                return Response(
                    {"error": f"No {role_label} account found with these credentials. Please check your role selection."},
                    status=status.HTTP_403_FORBIDDEN
                )"""

replacement = """            # Validate role against the actual account type
            actual_role = "business" if hasattr(user, "business_profile") else "influencer"
            if requested_role != actual_role:
                return Response(
                    {"error": f"This email is already registered as a {'Creator' if actual_role == 'influencer' else 'Business'}. Please use a different email or log in with the correct role."},
                    status=status.HTTP_403_FORBIDDEN
                )"""

if target in content:
    content = content.replace(target, replacement)
    with open("user/views.py", "w") as f:
        f.write(content)
    print("Success")
else:
    print("Failed to find target block")
