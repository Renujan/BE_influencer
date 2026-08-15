import os
import sys
import django

# Setup django environment if executed standalone
if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings.dev")
    django.setup()

from django.contrib.auth.models import User
from portfolio.models import PortfolioItem
from user.models import CreatorProfile


SAMPLE_PORTFOLIO_DATA = [
    {
        "title": "Summer Skincare Routine & Glow Guide",
        "platform": "instagram",
        "media_type": "reel",
        "views": "1.4M",
        "engagement_rate": 8.6,
        "brand": "Lumen Glow",
        "post_link": "https://www.instagram.com/reel/C12345sample/",
        "is_featured": True,
    },
    {
        "title": "Full Review: Nike Air Max Pulse Performance",
        "platform": "youtube",
        "media_type": "video",
        "views": "860K",
        "engagement_rate": 6.8,
        "brand": "Nike Sportswear",
        "post_link": "https://www.youtube.com/watch?v=sampleNike123",
        "is_featured": True,
    },
    {
        "title": "Viral 60-Second Espresso Tonic Hack",
        "platform": "tiktok",
        "media_type": "reel",
        "views": "2.8M",
        "engagement_rate": 14.2,
        "brand": "OatCraft Milk",
        "post_link": "https://www.tiktok.com/@creator/video/9876543210",
        "is_featured": True,
    },
    {
        "title": "Cozy Autumn Aesthetic Desk Setup",
        "platform": "instagram",
        "media_type": "photo",
        "views": "420K",
        "engagement_rate": 5.4,
        "brand": "Keychron Keyboards",
        "post_link": "https://www.instagram.com/p/DeskSetup2026/",
        "is_featured": False,
    },
    {
        "title": "24 Hours Traveling Solo in Kyoto",
        "platform": "youtube",
        "media_type": "video",
        "views": "1.1M",
        "engagement_rate": 9.3,
        "brand": "Away Luggage",
        "post_link": "https://www.youtube.com/watch?v=KyotoTravelGuide",
        "is_featured": False,
    },
    {
        "title": "Streetwear Lookbook & Styling 5 Outfits",
        "platform": "tiktok",
        "media_type": "video",
        "views": "950K",
        "engagement_rate": 11.5,
        "brand": "ASOS Design",
        "post_link": "https://www.tiktok.com/@creator/video/1122334455",
        "is_featured": False,
    },
    {
        "title": "Minimalist Morning Habits for Peak Focus",
        "platform": "instagram",
        "media_type": "photo",
        "views": "310K",
        "engagement_rate": 4.9,
        "brand": "",
        "post_link": "https://www.instagram.com/p/MorningMindset/",
        "is_featured": False,
    },
]


def run():
    creators = CreatorProfile.objects.select_related("user").all()
    if not creators.exists():
        print("No CreatorProfile records found. Attempting to check all User records...")
        users = User.objects.all()
    else:
        users = [cp.user for cp in creators]

    if not users:
        print("No users found in database.")
        return

    total_created = 0
    for user in users:
        existing_count = PortfolioItem.objects.filter(creator=user).count()
        if existing_count >= 3:
            print(f"User '{user.username}' already has {existing_count} portfolio items. Skipping duplicate seed.")
            continue

        for item_dict in SAMPLE_PORTFOLIO_DATA:
            PortfolioItem.objects.create(
                creator=user,
                title=item_dict["title"],
                platform=item_dict["platform"],
                media_type=item_dict["media_type"],
                views=item_dict["views"],
                engagement_rate=item_dict["engagement_rate"],
                brand=item_dict["brand"],
                post_link=item_dict["post_link"],
                is_featured=item_dict["is_featured"],
            )
            total_created += 1

        print(f"Created {len(SAMPLE_PORTFOLIO_DATA)} portfolio items for user: {user.username}")

    print(f"Done! Successfully created {total_created} sample portfolio items across creators.")


if __name__ == "__main__":
    run()
