from django.db import models
from user.models import CreatorProfile, BusinessProfile
from wagtail.snippets.models import register_snippet

@register_snippet
class CreatorSettings(models.Model):
    creator = models.OneToOneField(CreatorProfile, on_delete=models.CASCADE, related_name="settings")
    
    # Email notifications
    email_new_brand_requests = models.BooleanField(default=True)
    email_campaign_updates = models.BooleanField(default=True)
    email_payment_received = models.BooleanField(default=True)
    email_profile_views = models.BooleanField(default=False)
    email_platform_news = models.BooleanField(default=False)
    
    # Push notifications
    push_brand_requests = models.BooleanField(default=True)
    push_message_replies = models.BooleanField(default=True)
    push_payout_completed = models.BooleanField(default=True)
    
    # Security
    two_factor_enabled = models.BooleanField(default=False)
    
    # Billing & Tax
    tax_id = models.CharField(max_length=50, blank=True, null=True, default="")
    tax_form_submitted = models.BooleanField(default=False)
    plan = models.CharField(max_length=50, default="Creator Pro")
    
    # Rate Card options
    currency = models.CharField(max_length=20, default="USD ($)")
    rate_card_note = models.TextField(blank=True, null=True, default="")

    # Appearance
    theme = models.CharField(max_length=20, default="Light")
    accent_color = models.CharField(max_length=50, default="oklch(0.7 0.2 25)")
    sidebar_layout = models.CharField(max_length=20, default="Full")

    def __str__(self):
        return f"{self.creator.user.username}'s Settings (Creator)"


@register_snippet
class CreatorPayoutMethod(models.Model):
    creator = models.ForeignKey(CreatorProfile, on_delete=models.CASCADE, related_name="payout_methods")
    full_name = models.CharField(max_length=255, blank=True, null=True)
    bank_name = models.CharField(max_length=255, blank=True, null=True)
    account_number = models.CharField(max_length=100, blank=True, null=True)
    bank_book_photo_url = models.CharField(max_length=500, blank=True, null=True)
    is_primary = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.creator.user.username} - {self.bank_name} ({'Primary' if self.is_primary else 'Backup'})"

@register_snippet
class BusinessSettings(models.Model):
    business = models.OneToOneField(BusinessProfile, on_delete=models.CASCADE, related_name="settings")
    
    # Campaign notifications
    campaign_new_approved = models.BooleanField(default=True)
    campaign_influencer_accepts = models.BooleanField(default=True)
    campaign_deliverable_submitted = models.BooleanField(default=True)
    
    # Payment notifications
    payment_released = models.BooleanField(default=True)
    
    # Platform notifications
    platform_product_updates = models.BooleanField(default=True)
    platform_weekly_report = models.BooleanField(default=True)
    
    # Security
    two_factor_enabled = models.BooleanField(default=False)
    
    # Billing
    plan = models.CharField(max_length=50, default="Pro")
    card_last_four = models.CharField(max_length=4, blank=True, null=True, default="")
    card_expiry = models.CharField(max_length=5, blank=True, null=True, default="") # "MM/YY"
    
    # Integrations
    slack_connected = models.BooleanField(default=False)
    google_analytics_connected = models.BooleanField(default=False)
    hubspot_connected = models.BooleanField(default=False)
    notion_connected = models.BooleanField(default=False)
    zapier_connected = models.BooleanField(default=False)
    
    # Appearance
    theme = models.CharField(max_length=20, default="Light")
    accent_color = models.CharField(max_length=50, default="oklch(0.55 0.27 285)")
    sidebar_layout = models.CharField(max_length=20, default="Full")

    def __str__(self):
        return f"{self.business.company_name or self.business.user.username}'s Settings (Business)"

@register_snippet
class BusinessPayoutMethod(models.Model):
    business = models.ForeignKey(BusinessProfile, on_delete=models.CASCADE, related_name="payout_methods")
    full_name = models.CharField(max_length=255, blank=True, null=True)
    bank_name = models.CharField(max_length=255, blank=True, null=True)
    account_number = models.CharField(max_length=100, blank=True, null=True)
    bank_book_photo_url = models.CharField(max_length=500, blank=True, null=True)
    is_primary = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.business.company_name or self.business.user.username} - {self.bank_name} ({'Primary' if self.is_primary else 'Backup'})"
