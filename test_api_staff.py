import os
import sys
import django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings.dev")
django.setup()

from django.test import Client
from django.contrib.auth.models import User
c = Client()
u, _ = User.objects.get_or_create(username='staff_test', defaults={'is_staff': True, 'is_superuser': False})
c.force_login(u)

res = c.get('/api/campegins/campaigns/1347/')
print("API STATUS CODE:", res.status_code)
if res.status_code == 500:
    print(res.content.decode()[:2000])

res2 = c.get('/admin/chat-monitor/view-chat/1347/')
print("VIEW STATUS CODE:", res2.status_code)
if res2.status_code == 500:
    print(res2.content.decode()[:2000])
