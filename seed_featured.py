import os
import django
import random

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from user.models import BusinessProfile

profiles = BusinessProfile.objects.all()
for p in profiles:
    p.is_featured = True
    p.status = "approved"
    p.total_spent = random.randint(1500, 25000)
    p.campaign_count = random.randint(2, 25)
    
    # ensure it has a good bio
    if not p.bio:
        p.bio = f"We are a leading brand looking for passionate creators to collaborate on exciting new campaigns! We love creative minds."
        
    p.save()

print(f"Successfully featured {profiles.count()} businesses.")
