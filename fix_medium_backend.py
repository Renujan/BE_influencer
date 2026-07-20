import re

with open("Setting/serializers.py", "r") as f:
    content = f.read()

# Add mediums to fields
target_fields = """    # Niches (list of strings)
    niches = serializers.ListField(child=serializers.CharField(), required=False, write_only=True)"""

replacement_fields = """    # Niches (list of strings)
    niches = serializers.ListField(child=serializers.CharField(), required=False, write_only=True)
    
    # Mediums (list of strings)
    mediums = serializers.ListField(child=serializers.CharField(), required=False, write_only=True)"""

if "mediums = serializers.ListField(" not in content:
    content = content.replace(target_fields, replacement_fields)


target_update = """        # Update niches
        if "niches" in validated_data:
            niche_names = validated_data["niches"]
            niche_objects = []
            for name in niche_names:
                niche_obj, _ = Niche.objects.get_or_create(name=name)
                niche_objects.append(niche_obj)
            instance.niches.set(niche_objects)"""

replacement_update = """        # Update niches
        if "niches" in validated_data:
            niche_names = validated_data["niches"]
            niche_objects = []
            for name in niche_names:
                niche_obj, _ = Niche.objects.get_or_create(name=name)
                niche_objects.append(niche_obj)
            instance.niches.set(niche_objects)
            
        # Update mediums
        if "mediums" in validated_data:
            from user.models import Medium
            medium_names = validated_data["mediums"]
            medium_objects = []
            for name in medium_names:
                # First try to find medium by name and country if creator has a country
                if instance.country:
                    medium_obj = Medium.objects.filter(name__iexact=name, country=instance.country).first()
                else:
                    medium_obj = Medium.objects.filter(name__iexact=name).first()
                
                # If not found, we shouldn't create it blindly because it requires a country
                # We will just append it if found
                if medium_obj:
                    medium_objects.append(medium_obj)
            instance.mediums.set(medium_objects)"""

if "if \"mediums\" in validated_data:" not in content:
    content = content.replace(target_update, replacement_update)

with open("Setting/serializers.py", "w") as f:
    f.write(content)

