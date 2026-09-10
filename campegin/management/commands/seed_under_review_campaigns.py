from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from campegin.models import Campaign, Deliverable

class Command(BaseCommand):
    help = "Seed under-review campaigns in the database for checking"

    def handle(self, *args, **options):
        brand_user = User.objects.filter(username="sakthiveljanakan").first()
        if not brand_user:
            brand_user = User.objects.filter(business_profile__isnull=False).first()
        if not brand_user:
            self.stdout.write(self.style.ERROR("No business user found."))
            return

        creators = {
            "priya": User.objects.filter(username="priya").first(),
            "james": User.objects.filter(username="james").first(),
            "maya": User.objects.filter(username="maya").first(),
            "lightning": User.objects.filter(username="lightning").first(),
        }

        seed_data = [
            {
                "name": "Summer Glow Skincare Launch",
                "creator": creators.get("priya") or creators.get("lightning"),
                "status": "Under_Review",
                "budget": 2500,
                "min_budget": 2000,
                "max_budget": 3500,
                "min_price": 2000,
                "max_price": 3500,
                "per_creator_budget": 3500,
                "category": "Instagram - Reel / Short Video (15s - 60s)",
                "campaign_category": "Instagram - Reel / Short Video (15s - 60s)",
                "niche": "Beauty",
                "platform": "Instagram",
                "medium": "Tamil, English",
                "delivery_language": "Tamil, English",
                "country": "Sri Lanka",
                "province": "Western Province",
                "district": "Colombo",
                "start_date": "2026-06-01",
                "end_date": "2026-06-30",
                "brief": "Promote our upcoming summer glow organic skincare collection with high-energy reels and story teasers.",
                "created_via": "direct_request",
                "deliverables": [
                    {"name": "1 × Instagram Reel (30s)", "type": "reel", "brief": "Highlight natural ingredients and morning routine."},
                    {"name": "2 × Instagram Stories", "type": "story", "brief": "Swipe-up link to store product page."}
                ]
            },
            {
                "name": "CyberTech Pro Gaming Collab",
                "creator": creators.get("james") or creators.get("lightning"),
                "status": "Under_Review",
                "budget": 3200,
                "min_budget": 2500,
                "max_budget": 4000,
                "min_price": 2500,
                "max_price": 4000,
                "per_creator_budget": 4000,
                "category": "TikTok - TikTok Video (15s - 60s)",
                "campaign_category": "TikTok - TikTok Video (15s - 60s)",
                "niche": "Gaming",
                "platform": "TikTok",
                "medium": "English",
                "delivery_language": "English",
                "country": "Sri Lanka",
                "province": "Western Province",
                "district": "Gampaha",
                "start_date": "2026-06-10",
                "end_date": "2026-07-10",
                "brief": "Showcase new RGB mechanical gaming keyboard and wireless headset unboxing on TikTok.",
                "created_via": "direct_request",
                "deliverables": [
                    {"name": "1 × TikTok Video (60s)", "type": "video", "brief": "Sound test and aesthetic RGB setup showcase."}
                ]
            },
            {
                "name": "Island Odyssey Travel Showcase",
                "creator": creators.get("maya") or creators.get("lightning"),
                "status": "Under_Review",
                "budget": 1800,
                "min_budget": 1500,
                "max_budget": 2800,
                "min_price": 1500,
                "max_price": 2800,
                "per_creator_budget": 2800,
                "category": "Instagram - Story (24hr)",
                "campaign_category": "Instagram - Story (24hr)",
                "niche": "Travel",
                "platform": "Instagram",
                "medium": "Tamil, English",
                "delivery_language": "Tamil, English",
                "country": "Sri Lanka",
                "province": "Southern Province",
                "district": "Galle",
                "start_date": "2026-06-15",
                "end_date": "2026-07-15",
                "brief": "Create captivating 24hr stories documenting boutique coastal resort experience in Galle.",
                "created_via": "direct_request",
                "deliverables": [
                    {"name": "3 × Instagram Stories (24hr)", "type": "story", "brief": "Sunset view, private villa tour, and breakfast spread."}
                ]
            }
        ]

        created_count = 0
        for item in seed_data:
            delivs = item.pop("deliverables", [])
            campaign, created = Campaign.objects.get_or_create(
                brand=brand_user,
                name=item["name"],
                defaults=item
            )
            if not created:
                # Ensure status is Under_Review for checking
                campaign.status = "Under_Review"
                for k, v in item.items():
                    setattr(campaign, k, v)
                campaign.save()
            else:
                created_count += 1
                for d in delivs:
                    Deliverable.objects.create(
                        campaign=campaign,
                        name=d["name"],
                        type=d["type"],
                        brief=d.get("brief", ""),
                        status="PENDING_SUBMISSION"
                    )

            self.stdout.write(self.style.SUCCESS(f"Campaign '{campaign.name}' (ID: {campaign.id}) is Under_Review for brand '{brand_user.username}'"))

        self.stdout.write(self.style.SUCCESS(f"Successfully processed {len(seed_data)} under-review campaigns ({created_count} created)."))
