import os

file_path = "Setting/serializers.py"

with open(file_path, "r") as f:
    content = f.read()

# 1. Import Country
if 'Country' not in content.split('from user.models import')[1].split('\n')[0]:
    content = content.replace(
        'from user.models import CreatorProfile, BusinessProfile, Niche, CreatorRate, CreatorSocialAccount',
        'from user.models import CreatorProfile, BusinessProfile, Niche, CreatorRate, CreatorSocialAccount, Country'
    )

# 2. Add country field to CreatorFullSettingsSerializer
if 'country = serializers.CharField' not in content.split('class CreatorFullSettingsSerializer')[1].split('class BusinessFullSettingsSerializer')[0]:
    content = content.replace(
        '    location = serializers.CharField(required=False, allow_null=True, allow_blank=True)\n    bio = serializers.CharField(required=False, allow_null=True, allow_blank=True)',
        '    location = serializers.CharField(required=False, allow_null=True, allow_blank=True)\n    country = serializers.CharField(required=False, allow_null=True, allow_blank=True)\n    bio = serializers.CharField(required=False, allow_null=True, allow_blank=True)'
    )

# 3. Update CreatorFullSettingsSerializer.update
creator_update = """        instance.bio = validated_data.get("bio", instance.bio)
        instance.avatar_url = validated_data.get("avatar_url", instance.avatar_url)
        
        if "country" in validated_data:
            country_name = validated_data["country"]
            if country_name:
                country_obj, _ = Country.objects.get_or_create(name=country_name.strip())
                instance.country = country_obj
            else:
                instance.country = None
                
        instance.save()"""

if 'if "country" in validated_data:' not in content.split('class CreatorFullSettingsSerializer')[1].split('class BusinessFullSettingsSerializer')[0]:
    content = content.replace(
        '        instance.bio = validated_data.get("bio", instance.bio)\n        instance.avatar_url = validated_data.get("avatar_url", instance.avatar_url)\n        instance.save()',
        creator_update
    )

# 4. Add country field to BusinessFullSettingsSerializer
if 'country = serializers.CharField' not in content.split('class BusinessFullSettingsSerializer')[1]:
    content = content.replace(
        '    time_zone = serializers.CharField(required=False, allow_null=True, allow_blank=True)\n    avatar_url = serializers.CharField(required=False, allow_null=True, allow_blank=True)',
        '    time_zone = serializers.CharField(required=False, allow_null=True, allow_blank=True)\n    country = serializers.CharField(required=False, allow_null=True, allow_blank=True)\n    avatar_url = serializers.CharField(required=False, allow_null=True, allow_blank=True)'
    )

# 5. Update BusinessFullSettingsSerializer.update
business_update = """        instance.time_zone = validated_data.get("time_zone", instance.time_zone)
        instance.avatar_url = validated_data.get("avatar_url", instance.avatar_url)
        
        if "country" in validated_data:
            country_name = validated_data["country"]
            if country_name:
                country_obj, _ = Country.objects.get_or_create(name=country_name.strip())
                instance.country = country_obj
            else:
                instance.country = None"""

if 'if "country" in validated_data:' not in content.split('class BusinessFullSettingsSerializer')[1]:
    content = content.replace(
        '        instance.time_zone = validated_data.get("time_zone", instance.time_zone)\n        instance.avatar_url = validated_data.get("avatar_url", instance.avatar_url)',
        business_update
    )

with open(file_path, "w") as f:
    f.write(content)

print("Updated Setting/serializers.py")
