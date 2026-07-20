import re

with open("user/serializers.py", "r") as f:
    content = f.read()

# Add DistrictSerializer
district_serializer = """class DistrictSerializer(serializers.ModelSerializer):
    class Meta:
        model = District
        fields = ["id", "name", "province"]

class ProvinceSerializer"""
content = content.replace("class ProvinceSerializer", district_serializer)

# Import District
content = content.replace("Medium, Province", "Medium, Province, District")

# Update CountrySerializer
old_country_ser = """class CountrySerializer(serializers.ModelSerializer):
    provinces = ProvinceSerializer(many=True, read_only=True)

    class Meta:
        model = Country
        fields = ["id", "name", "provinces"]"""

new_country_ser = """class CountrySerializer(serializers.ModelSerializer):
    provinces = ProvinceSerializer(many=True, read_only=True)
    mediums = MediumSerializer(many=True, read_only=True)
    districts = DistrictSerializer(many=True, read_only=True)

    class Meta:
        model = Country
        fields = ["id", "name", "currency", "country_code", "provinces", "mediums", "districts"]"""
content = content.replace(old_country_ser, new_country_ser)

with open("user/serializers.py", "w") as f:
    f.write(content)
