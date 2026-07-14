import os
import django
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings.dev")
django.setup()

from notifications.models import Notification

for n in Notification.objects.all():
    print(n.title, n.category)
