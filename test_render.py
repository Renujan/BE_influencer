import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "BE_influencer.settings")
django.setup()

from django.test import RequestFactory
from django.urls import reverse
from campegin.models import Campaign
from chat_monitor.views import chat_monitor_view_chat_view
from django.contrib.auth.models import User

factory = RequestFactory()
request = factory.get('/admin/chat-monitor/view-chat/1347/')
request.user = User.objects.filter(is_staff=True).first()

try:
    response = chat_monitor_view_chat_view(request, 1347)
    print("Response status:", response.status_code)
except Exception as e:
    import traceback
    traceback.print_exc()
