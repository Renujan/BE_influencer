import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings.base')
try:
    django.setup()
except:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
    django.setup()

from campegin.models import Campaign
campaigns = Campaign.objects.filter(status="Countered")
for c in campaigns:
    # If business sent it, wait how do we know? We can't know for sure, 
    # but we can assume if the user is testing the Business counter, we can just set it to Business_Countered
    # Let's just set all Countered to Business_Countered for testing purposes
    print(f"Updating campaign {c.id} from {c.status} to Business_Countered")
    c.status = "Business_Countered"
    c.save()
