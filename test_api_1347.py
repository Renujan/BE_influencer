import os
import sys
import django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings.dev")
django.setup()

from django.test import Client
from django.contrib.auth.models import User
c = Client()
u = User.objects.filter(is_superuser=True).first()
c.force_login(u)

res = c.get('/api/campegins/campaigns/1347/')
print("STATUS CODE:", res.status_code)
if res.status_code == 500:
    print(res.content.decode()[:2000])
