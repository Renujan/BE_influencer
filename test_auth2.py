import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings.base")
django.setup()

from user.models import BusinessProfile, User, Country
profile = BusinessProfile.objects.first()
if profile:
    from Setting.serializers import BusinessFullSettingsSerializer
    from user.serializers import BusinessProfileSerializer
    
    country_obj, _ = Country.objects.get_or_create(name="United States")
    profile.country = country_obj
    profile.save()
    
    settings_data = BusinessFullSettingsSerializer(profile).data
    me_data = BusinessProfileSerializer(profile).data
    
    print("Settings country:", settings_data.get("country"))
    print("MeView country:", me_data.get("country"))
else:
    print("No business profile found")
