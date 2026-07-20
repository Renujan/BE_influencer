from campegin.models import CampaignCategory

categories_to_add = [
    "Story (24hr): Temporary vertical video or photo updates.",
    "Feed Post (Photo): Standard permanent image post on a profile.",
    "Reel / Short Video: Vertical, highly engaging short video.",
    "Long-form Video: In-depth content, landscape format.",
    "Carousel: Multiple images or videos combined into one post.",
    "Live Stream (1hr): Real-time broadcast interaction.",
    "YouTube Dedicated: Entire video focused on brand/product.",
    "YouTube Integration: Sponsored segment within a video.",
    "Blog / Article: Written review, feature, or interview.",
    "Podcast Mention: Audio sponsorship read by the host.",
    "TikTok Video: Short-form video for TikTok trends.",
    "YouTube Shorts: Vertical content for YouTube ecosystem.",
    "X (Twitter) Post / Thread: Text-based promotion or thread.",
    "LinkedIn Post: Content ideal for B2B campaigns.",
    "Twitch Stream Segment: Sponsored gameplay or demo.",
    "Pinterest Pin: Visual bookmarking for lifestyle or product.",
    "UGC (Raw Footage): Creator films content for brand's paid ads.",
    "Newsletter Sponsorship: Ad placement in creator's emails.",
    "Link-in-Bio Placement: Brand's link pinned to top of profile.",
    "Whitelisting: Permission to run ads via creator's handle.",
    "Giveaway / Contest: Promotional event hosted by creator."
]

print("Deleting old categories...")
CampaignCategory.objects.all().delete()

print("Adding new categories...")
for cat_name in categories_to_add:
    # Truncate to 100 chars just in case, since max_length is 100
    cat_name = cat_name[:100]
    CampaignCategory.objects.create(name=cat_name)
    print(f"Added: {cat_name}")

print("Done!")
