from django.db import models
from django.contrib.auth.models import User
from wagtail.snippets.models import register_snippet

@register_snippet
class Niche(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

@register_snippet
class UserProfile(models.Model):
    ROLE_CHOICES = (
        ("business", "Business"),
        ("influencer", "Creator"),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    phone = models.CharField(max_length=30, blank=True, null=True)
    avatar_url = models.CharField(max_length=255, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=100, blank=True, null=True)
    wallet_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    next_payout_date = models.CharField(max_length=100, blank=True, null=True)
    
    # Creator details
    niches = models.ManyToManyField(Niche, blank=True, related_name="creators")
    
    # Business details
    company_name = models.CharField(max_length=255, blank=True, null=True)
    business_type = models.CharField(max_length=100, blank=True, null=True)
    website = models.URLField(blank=True, null=True)

    # Email OTP storage (simulated OTP flow)
    otp_code = models.CharField(max_length=6, blank=True, null=True)
    otp_verified = models.BooleanField(default=False)

    def get_details(self):
        if self.role == "business":
            parts = []
            if self.company_name:
                parts.append(self.company_name)
            if self.business_type:
                parts.append(self.business_type)
            return " | ".join(parts) or "Business Client"
        else:
            niches_list = [n.name for n in self.niches.all()]
            return f"Niches: {', '.join(niches_list)}" if niches_list else "Creator Talent"
    
    get_details.short_description = "Profile Details"

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

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


