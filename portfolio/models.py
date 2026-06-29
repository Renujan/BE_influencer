from django.db import models
from django.contrib.auth.models import User


class PortfolioItem(models.Model):
    PLATFORM_CHOICES = [
        ("instagram", "Instagram"),
        ("youtube", "YouTube"),
        ("tiktok", "TikTok"),
    ]
    MEDIA_TYPE_CHOICES = [
        ("photo", "Photo"),
        ("video", "Video"),
        ("reel", "Reel"),
    ]

    creator = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="portfolio_items"
    )
    title = models.CharField(max_length=255)
    platform = models.CharField(max_length=30, choices=PLATFORM_CHOICES, default="instagram")
    media_type = models.CharField(max_length=20, choices=MEDIA_TYPE_CHOICES, default="photo")
    views = models.CharField(max_length=50, blank=True, default="0", help_text="e.g. '1.2M', '840K'")
    engagement_rate = models.FloatField(default=0.0, help_text="e.g. 8.4 for 8.4%")
    brand = models.CharField(max_length=255, blank=True, default="", help_text="Sponsor/brand name, blank if organic")
    post_link = models.URLField(blank=True, null=True, help_text="Live URL of the post")
    thumbnail = models.ImageField(
        upload_to="portfolio/thumbnails/",
        blank=True,
        null=True,
        help_text="Upload a thumbnail image or screenshot for this post."
    )
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Portfolio Item"
        verbose_name_plural = "Portfolio Items"

    def __str__(self):
        return f"{self.creator.username} — {self.title} ({self.platform})"
