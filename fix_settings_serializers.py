import re

with open("Setting/serializers.py", "r") as f:
    content = f.read()

# Add province and district to fields
target_fields = """    # Profile fields
    phone = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    location = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    country = serializers.CharField(required=False, allow_null=True, allow_blank=True)"""

replacement_fields = """    # Profile fields
    phone = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    location = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    country = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    province = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    district = serializers.CharField(required=False, allow_null=True, allow_blank=True)"""

if "province = serializers.CharField" not in content:
    content = content.replace(target_fields, replacement_fields)

# Update update() method
target_update = """        if "country" in validated_data:
            country_name = validated_data["country"]
            if country_name:
                country_obj, _ = Country.objects.get_or_create(name=country_name.strip())
                instance.country = country_obj
            else:
                instance.country = None"""

replacement_update = """        if "country" in validated_data:
            country_name = validated_data["country"]
            if country_name:
                country_obj, _ = Country.objects.get_or_create(name=country_name.strip())
                instance.country = country_obj
            else:
                instance.country = None
                
        if "province" in validated_data:
            from user.models import Province
            province_name = validated_data["province"]
            if province_name:
                province_obj = Province.objects.filter(name=province_name.strip()).first()
                if province_obj:
                    instance.province = province_obj
            else:
                instance.province = None
                
        if "district" in validated_data:
            from user.models import District
            district_name = validated_data["district"]
            if district_name:
                district_obj = District.objects.filter(name=district_name.strip()).first()
                if district_obj:
                    instance.district = district_obj
            else:
                instance.district = None"""

if "if \"province\" in validated_data:" not in content:
    content = content.replace(target_update, replacement_update)

# Also update BusinessFullSettingsSerializer just in case it doesn't process them yet
target_biz_update = """        if "country" in validated_data:
            country_name = validated_data["country"]
            if country_name:
                country_obj, _ = Country.objects.get_or_create(name=country_name.strip())
                instance.country = country_obj
            else:
                instance.country = None"""

replacement_biz_update = """        if "country" in validated_data:
            country_name = validated_data["country"]
            if country_name:
                country_obj, _ = Country.objects.get_or_create(name=country_name.strip())
                instance.country = country_obj
            else:
                instance.country = None
                
        if "province" in validated_data:
            from user.models import Province
            province_name = validated_data["province"]
            if province_name:
                province_obj = Province.objects.filter(name=province_name.strip()).first()
                if province_obj:
                    instance.province = province_obj
            else:
                instance.province = None
                
        if "district" in validated_data:
            from user.models import District
            district_name = validated_data["district"]
            if district_name:
                district_obj = District.objects.filter(name=district_name.strip()).first()
                if district_obj:
                    instance.district = district_obj
            else:
                instance.district = None"""

# Note: BusinessFullSettingsSerializer already has country block, wait, let's check if it has province in fields.
# Actually let's just write the content first
with open("Setting/serializers.py", "w") as f:
    f.write(content)

