def run():
    from portfolio.models import PortfolioItem
    from django.contrib.auth.models import User

    users = User.objects.all()
    if not users.exists():
        print("No users found.")
        return

    for creator in users:
        if PortfolioItem.objects.filter(creator=creator).count() >= 4:
            continue
        
        items = [
            {
                "title": "Summer Skincare Routine",
                "platform": "instagram",
                "media_type": "reel",
                "views": "1.2M",
                "engagement_rate": 8.4,
                "brand": "Lumen Beauty",
                "post_link": "https://instagram.com/p/summer-skincare",
                "is_featured": True
            },
            {
                "title": "Unboxing Nike Air Max",
                "platform": "youtube",
                "media_type": "video",
                "views": "840K",
                "engagement_rate": 6.2,
                "brand": "Nike",
                "post_link": "https://youtube.com/watch?v=nike-air",
                "is_featured": True
            },
            {
                "title": "Morning Routine Setup",
                "platform": "tiktok",
                "media_type": "reel",
                "views": "2.5M",
                "engagement_rate": 12.1,
                "brand": "Organic Co.",
                "post_link": "https://tiktok.com/@user/video/12345",
                "is_featured": False
            },
            {
                "title": "Festival OOTD",
                "platform": "instagram",
                "media_type": "photo",
                "views": "300K",
                "engagement_rate": 4.5,
                "brand": "",
                "post_link": "https://instagram.com/p/festival",
                "is_featured": False
            }
        ]

        for item_data in items:
            PortfolioItem.objects.create(creator=creator, **item_data)
        
        print(f"Added {len(items)} portfolio items for user {creator.username}.")

if __name__ == '__main__':
    run()
