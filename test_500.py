import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "BE_influencer.settings")
django.setup()

from django.test import Client
from django.contrib.auth.models import User

c = Client()
u, created = User.objects.get_or_create(username='admin_test', defaults={'is_staff': True, 'is_superuser': True})
if created:
    u.set_password('admin_test')
    u.save()

c.force_login(u)
response = c.get('/admin/chat-monitor/view-chat/1347/')
print("STATUS CODE:", response.status_code)
if response.status_code == 500:
    print("500 ERROR CAUGHT")
    with open('/tmp/err.html', 'w') as f:
        f.write(response.content.decode())
    print("Saved to /tmp/err.html")
