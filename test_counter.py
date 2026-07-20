import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings.base') # Try this first
try:
    django.setup()
except:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
    django.setup()

from campegin.models import Campaign
c = Campaign.objects.filter(status="Countered").first()
if not c:
    c = Campaign.objects.first()
    if c:
        c.status = "Countered"
        c.counter_price = 150
        c.save()

if c:
    print(f"Testing accept_counter on {c.id}")
    try:
        c.budget = c.counter_price
        c.status = "Live"
        c.progress = 62
        c.save()
        print("Success")
    except Exception as e:
        print("Error:", e)
