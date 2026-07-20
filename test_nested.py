import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings.dev")
django.setup()

from user.models import Country, Province
from wagtail.admin.panels import InlinePanel

print(Country.panels)
print(Province.panels)
