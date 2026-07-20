import re

with open("Setting/serializers.py", "r") as f:
    content = f.read()

# 1. Add username to fields
target_fields = """    # User fields
    first_name = serializers.CharField(source="user.first_name", required=False, allow_blank=True)"""
replacement_fields = """    # User fields
    username = serializers.CharField(source="user.username", required=False, allow_blank=True)
    first_name = serializers.CharField(source="user.first_name", required=False, allow_blank=True)"""

if "username = serializers.CharField(source=" not in content:
    content = content.replace(target_fields, replacement_fields)

# 2. Add username uniqueness validation
target_validate = """    def update(self, instance, validated_data):"""
replacement_validate = """    def validate(self, attrs):
        user_data = attrs.get("user", {})
        if "username" in user_data:
            username = user_data["username"]
            from django.contrib.auth.models import User
            # Check if another user has this username
            if User.objects.filter(username=username).exclude(pk=self.instance.user.pk).exists():
                raise serializers.ValidationError({"username": "This username is already taken."})
        return attrs

    def update(self, instance, validated_data):"""
if "def validate(self, attrs):" not in content[:content.find("class BusinessSettingsSerializer")]:
    content = content.replace(target_validate, replacement_validate)

# 3. Add username update in update()
target_update = """        if "email" in user_data:
            user.email = user_data["email"]
        user.save()"""
replacement_update = """        if "email" in user_data:
            user.email = user_data["email"]
        if "username" in user_data:
            user.username = user_data["username"]
        user.save()"""
if 'if "username" in user_data:' not in content[:content.find("class BusinessSettingsSerializer")]:
    content = content.replace(target_update, replacement_update)

with open("Setting/serializers.py", "w") as f:
    f.write(content)
