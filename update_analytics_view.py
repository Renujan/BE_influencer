import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

with open("campegin/views.py", "r") as f:
    content = f.read()

new_view = """
class BusinessAnalyticsView(APIView):
    \"\"\"Return aggregated business analytics and top campaigns.\"\"\"
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from django.db.models import Sum, Avg
        user = request.user
        qs = Campaign.objects.filter(brand=user)

        total_budget = float(qs.aggregate(total=Sum("budget"))["total"] or 0)
        avg_progress = float(qs.aggregate(avg=Avg("progress"))["avg"] or 0)
        avg_engagement = round(3.0 + (avg_progress / 100) * 9.0, 1)

        total_reach = int(total_budget * 1000)
        total_impressions = int(total_budget * 2500)
        total_roi = 4.1 if total_budget > 0 else 0.0

        # Top campaigns by engagement/progress
        top_campaigns_qs = qs.exclude(status="Pending").order_by("-progress")[:5]
        top_campaigns = []
        for c in top_campaigns_qs:
            er = round(3.0 + (c.progress / 100) * 9.0, 1) if c.progress else 6.5
            spend = float(c.budget or 0)
            reach_val = c.reach if c.reach else f"{round(spend/1000, 1)}M"
            top_campaigns.append({
                "name": c.name,
                "er": er,
                "reach": reach_val,
                "roi": "4.1x" if spend > 0 else "0x",
                "spend": spend,
                "trend": "up"
            })

        return Response({
            "stats": {
                "total_reach": total_reach,
                "total_impressions": total_impressions,
                "avg_engagement": avg_engagement,
                "total_roi": total_roi,
            },
            "top_campaigns": top_campaigns
        })
"""

# Insert before PitchViewSet
pitch_view_index = content.find("class PitchViewSet")
if pitch_view_index != -1:
    new_content = content[:pitch_view_index] + new_view + "\n" + content[pitch_view_index:]
    with open("campegin/views.py", "w") as f:
        f.write(new_content)
    print("Added BusinessAnalyticsView")
else:
    print("PitchViewSet not found")

