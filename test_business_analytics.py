import os
import django
import sys
import traceback

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings.dev")
django.setup()

from campegin.models import Campaign
from django.db.models import Sum, Avg

try:
    qs = Campaign.objects.all()
    total_budget = float(qs.aggregate(total=Sum("budget"))["total"] or 0)
    avg_progress = float(qs.aggregate(avg=Avg("progress"))["avg"] or 0)
    
    top_campaigns_qs = qs.exclude(status="Pending").order_by("-progress")[:5]
    for c in top_campaigns_qs:
        er = round(3.0 + (c.progress / 100) * 9.0, 1) if c.progress else 6.5
        spend = float(c.budget or 0)
        reach_val = c.reach if c.reach else f"{round(spend/1000, 1)}M"
        
    print("Success")
except Exception as e:
    traceback.print_exc()
