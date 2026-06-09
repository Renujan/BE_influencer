from django.db import models
from django.contrib.auth.models import User
from wagtail.snippets.models import register_snippet

@register_snippet
class Niche(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

@register_snippet
class BusinessProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="business_profile")
    company_name = models.CharField(max_length=255, blank=True, null=True)
    business_type = models.CharField(max_length=255, blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    phone = models.CharField(max_length=30, blank=True, null=True)
    secondary_phone = models.CharField(max_length=30, blank=True, null=True)
    time_zone = models.CharField(max_length=100, blank=True, null=True)
    avatar_url = models.CharField(max_length=255, blank=True, null=True)

    # Social links
    facebook_url = models.URLField(blank=True, null=True)
    instagram_handle = models.CharField(max_length=100, blank=True, null=True)
    tiktok_handle = models.CharField(max_length=100, blank=True, null=True)
    youtube_url = models.URLField(blank=True, null=True)
    linkedin_url = models.URLField(blank=True, null=True)
    twitter_handle = models.CharField(max_length=100, blank=True, null=True)

    # OTP storage
    otp_code = models.CharField(max_length=6, blank=True, null=True)
    otp_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.company_name or self.user.username} (Business)"

@register_snippet
class CreatorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="creator_profile")
    phone = models.CharField(max_length=30, blank=True, null=True)
    location = models.CharField(max_length=100, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    avatar_url = models.CharField(max_length=255, blank=True, null=True)
    niches = models.ManyToManyField(Niche, blank=True, related_name="creators")
    wallet_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    next_payout_date = models.CharField(max_length=100, blank=True, null=True)

    # OTP storage
    otp_code = models.CharField(max_length=6, blank=True, null=True)
    otp_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} (Creator)"

@register_snippet
class CreatorRate(models.Model):
    creator = models.ForeignKey(CreatorProfile, on_delete=models.CASCADE, related_name="rates")
    content_type = models.CharField(max_length=255)
    platforms = models.CharField(max_length=255, help_text="Comma-separated or JSON list of platforms, e.g. 'Instagram,TikTok'")
    price = models.DecimalField(max_digits=12, decimal_places=2)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.creator.user.username} - {self.content_type} (${self.price})"

@register_snippet
class CreatorSocialAccount(models.Model):
    PLATFORM_CHOICES = (
        ("instagram", "Instagram"),
        ("youtube", "YouTube"),
        ("tiktok", "TikTok"),
        ("facebook", "Facebook"),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="social_accounts")
    platform = models.CharField(max_length=30, choices=PLATFORM_CHOICES)
    username = models.CharField(max_length=100)
    followers_count = models.CharField(max_length=50) # e.g. "1.2M", "320K"
    engagement_rate = models.DecimalField(max_digits=5, decimal_places=2) # e.g. 8.20
    is_connected = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.platform} ({self.username})"
