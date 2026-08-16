from django.db import models
from django.contrib.auth.models import User
from campegin.models import Campaign
from wagtail.snippets.models import register_snippet
from wagtail.admin.panels import FieldPanel

@register_snippet
class CreatorRating(models.Model):
    campaign = models.OneToOneField(Campaign, on_delete=models.CASCADE, related_name="rating")
    brand = models.ForeignKey(User, on_delete=models.CASCADE, related_name="given_creator_ratings")
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_creator_ratings")
    rating = models.IntegerField(default=5, help_text="Rating score from 1 to 5")
    review = models.TextField(blank=True, null=True, help_text="Optional feedback or review notes from business")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    panels = [
        FieldPanel('campaign'),
        FieldPanel('brand'),
        FieldPanel('creator'),
        FieldPanel('rating'),
        FieldPanel('review'),
    ]

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Creator Rating"
        verbose_name_plural = "Creator Ratings"

    def __str__(self):
        return f"{self.rating}★ Rating for {self.creator.username} on {self.campaign.name}"

    def get_creator_display(self):
        return self.creator.username if self.creator else "-"
    get_creator_display.short_description = "Creator Name"

    def get_business_display(self):
        return self.brand.username if self.brand else "-"
    get_business_display.short_description = "Business Person Name"

    def get_campaign_display(self):
        return self.campaign.name if self.campaign else "-"
    get_campaign_display.short_description = "Campaign"

    def get_rating_display(self):
        from django.utils.html import format_html
        return format_html('<span style="color: #f59e0b; font-weight: 700; font-size: 14px;">★ {} / 5</span>', self.rating)
    get_rating_display.short_description = "Rating"


@register_snippet
class BusinessRating(models.Model):
    campaign = models.OneToOneField(Campaign, on_delete=models.CASCADE, related_name="business_rating")
    brand = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_business_ratings")
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name="given_business_ratings")
    rating = models.IntegerField(default=5, help_text="Rating score from 1 to 5")
    review = models.TextField(blank=True, null=True, help_text="Optional feedback or review notes from creator")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    panels = [
        FieldPanel('campaign'),
        FieldPanel('brand'),
        FieldPanel('creator'),
        FieldPanel('rating'),
        FieldPanel('review'),
    ]

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Business Rating"
        verbose_name_plural = "Business Ratings"

    def __str__(self):
        return f"{self.rating}★ Rating for {self.brand.username} on {self.campaign.name}"

    def get_creator_display(self):
        return self.creator.username if self.creator else "-"
    get_creator_display.short_description = "Creator Name"

    def get_business_display(self):
        return self.brand.username if self.brand else "-"
    get_business_display.short_description = "Business Person Name"

    def get_campaign_display(self):
        return self.campaign.name if self.campaign else "-"
    get_campaign_display.short_description = "Campaign"

    def get_rating_display(self):
        from django.utils.html import format_html
        return format_html('<span style="color: #f59e0b; font-weight: 700; font-size: 14px;">★ {} / 5</span>', self.rating)
    get_rating_display.short_description = "Rating"

