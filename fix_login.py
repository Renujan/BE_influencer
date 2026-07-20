import re

with open("user/views.py", "r") as f:
    content = f.read()

target = """        # If the frontend sent a role, enforce it — reject cross-role logins
        if requested_role and requested_role != actual_role:
            role_label = "Business" if requested_role == "business" else "Creator"
            return Response(
                {"error": f"No {role_label} account found with these credentials. Please check your role selection."},
                status=status.HTTP_403_FORBIDDEN
            )"""

replacement = """        # If the frontend sent a role, enforce it — reject cross-role logins
        if requested_role and requested_role != actual_role:
            return Response(
                {"error": f"This email is registered as a {'Creator' if actual_role == 'influencer' else 'Business'}. Please log in with the correct role selection."},
                status=status.HTTP_403_FORBIDDEN
            )"""

if target in content:
    content = content.replace(target, replacement)
    with open("user/views.py", "w") as f:
        f.write(content)
    print("Success")
else:
    print("Failed to find target block")
