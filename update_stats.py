import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from campegin.views import CampaignStatsView
print("Done")
