import re

with open("Setting/serializers.py", "r") as f:
    content = f.read()

# Add mediums to fields
field_target = "    business_types = serializers.ListField(child=serializers.CharField(), required=False, write_only=True)"
field_replacement = "    business_types = serializers.ListField(child=serializers.CharField(), required=False, write_only=True)\n    mediums = serializers.ListField(child=serializers.CharField(), required=False, write_only=True)"

if "mediums =" not in content[content.find("class BusinessFullSettingsSerializer"):]:
    content = content.replace(field_target, field_replacement)

# Add mediums to to_representation
rep_target = """        if getattr(instance, "district", None):
            rep["district"] = instance.district.name
            
        return rep"""
rep_replacement = """        if getattr(instance, "district", None):
            rep["district"] = instance.district.name
            
        rep["mediums"] = [m.name for m in instance.mediums.all()]
        return rep"""
if 'rep["mediums"]' not in content[content.find("class BusinessFullSettingsSerializer"):]:
    content = content.replace(rep_target, rep_replacement)

# Add mediums to update()
update_target = """        # Update settings
        settings_data = validated_data.get("settings", {})"""
update_replacement = """        # Update mediums
        if "mediums" in validated_data:
            from user.models import Medium
            medium_names = validated_data["mediums"]
            medium_objects = []
            for name in medium_names:
                if instance.country:
                    medium_obj = Medium.objects.filter(name__iexact=name, country=instance.country).first()
                else:
                    medium_obj = Medium.objects.filter(name__iexact=name).first()
                if medium_obj:
                    medium_objects.append(medium_obj)
            instance.mediums.set(medium_objects)
            
        # Update settings
        settings_data = validated_data.get("settings", {})"""
if 'if "mediums" in validated_data:' not in content[content.find("class BusinessFullSettingsSerializer"):]:
    content = content.replace(update_target, update_replacement)

with open("Setting/serializers.py", "w") as f:
    f.write(content)

