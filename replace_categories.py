import os
import sys
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings.dev")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from campegin.models import CampaignCategory, CampaignPlatform

# Fetch existing campaign platform names from CampaignPlatform table
available_platforms = list(CampaignPlatform.objects.values_list("name", flat=True))
print(f"Available Campaign Platforms in database: {available_platforms}")

# Build initial categories matching ONLY the platforms in Campaign Platforms section
raw_categories = [
    # Facebook
    {"platform": "Facebook", "type": "Page Feed Post", "duration": "Permanent", "min_price": 10000.00, "max_price": 50000.00},
    {"platform": "Facebook", "type": "Story", "duration": "24hr", "min_price": 8000.00, "max_price": 40000.00},
    {"platform": "Facebook", "type": "Reel", "duration": "15s - 60s", "min_price": 12000.00, "max_price": 60000.00},

    # Instagram
    {"platform": "Instagram", "type": "Story", "duration": "24hr", "min_price": 10000.00, "max_price": 50000.00},
    {"platform": "Instagram", "type": "Feed Post (Photo)", "duration": "Permanent", "min_price": 15000.00, "max_price": 60000.00},
    {"platform": "Instagram", "type": "Reel / Short Video", "duration": "15s - 60s", "min_price": 20000.00, "max_price": 80000.00},
    {"platform": "Instagram", "type": "Carousel Post", "duration": "Multi-slide", "min_price": 18000.00, "max_price": 70000.00},
    {"platform": "Instagram", "type": "Collab Post", "duration": "Permanent", "min_price": 25000.00, "max_price": 100000.00},
    
    # TikTok
    {"platform": "TikTok", "type": "TikTok Video", "duration": "15s - 60s", "min_price": 15000.00, "max_price": 75000.00},
    {"platform": "TikTok", "type": "Multi-Part Series", "duration": "2 - 3 Videos", "min_price": 40000.00, "max_price": 150000.00},
    {"platform": "TikTok", "type": "Live Stream", "duration": "1hr", "min_price": 30000.00, "max_price": 120000.00},

    # YouTube
    {"platform": "YouTube", "type": "YouTube Shorts", "duration": "60s", "min_price": 20000.00, "max_price": 80000.00},
    {"platform": "YouTube", "type": "YouTube Integration", "duration": "60s segment", "min_price": 35000.00, "max_price": 150000.00},
    {"platform": "YouTube", "type": "YouTube Dedicated Video", "duration": "8 - 15 min", "min_price": 60000.00, "max_price": 250000.00},

    # LinkedIn
    {"platform": "LinkedIn", "type": "B2B Article / Post", "duration": "Permanent", "min_price": 20000.00, "max_price": 90000.00},

    # X
    {"platform": "X", "type": "Post / Thread", "duration": "Text & Media", "min_price": 10000.00, "max_price": 40000.00},
]

# Filter to ensure only platforms currently created in Campaign Platforms section are seeded
valid_categories = [c for c in raw_categories if c["platform"] in available_platforms]

print("Deleting all existing campaign categories from database...")
CampaignCategory.objects.all().delete()

print("Re-adding campaign categories matching Campaign Platforms...")
for cat in valid_categories:
    obj = CampaignCategory.objects.create(
        platform=cat["platform"],
        type=cat["type"],
        duration=cat["duration"],
        min_price=cat["min_price"],
        max_price=cat["max_price"],
    )
    print(f"Created #{obj.id}: [{obj.platform}] {obj.name}")

print(f"Successfully cleared and seeded {len(valid_categories)} campaign categories in database!")
