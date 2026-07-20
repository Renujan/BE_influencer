import os
import sys
import django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings.dev")
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from campegin.models import Campaign

c = Client()
u = User.objects.filter(is_superuser=True).first()
c.force_login(u)

# Get an actual campaign ID
camp = Campaign.objects.first()
if not camp:
    print("NO CAMPAIGN FOUND")
else:
    print(f"Testing with campaign ID: {camp.id}")
    res = c.get(f'/admin/chat-monitor/view-chat/{camp.id}/')
    print("STATUS CODE:", res.status_code)
    if res.status_code != 200:
        print(res.content.decode()[:1000])
