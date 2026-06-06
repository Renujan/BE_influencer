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
    is_approved = models.BooleanField(default=False)

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

@register_snippet
class Campaign(models.Model):
    STATUS_CHOICES = (
        ("Pending", "Pending"),
        ("Live", "Live"),
        ("Completed", "Completed"),
    )
    name = models.CharField(max_length=255)
    brand = models.ForeignKey(User, on_delete=models.CASCADE, related_name="brand_campaigns")
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name="creator_campaigns", null=True, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="Pending")
    budget = models.DecimalField(max_digits=12, decimal_places=2)
    start_date = models.CharField(max_length=100, blank=True, null=True) # e.g. "May 12"
    progress = models.IntegerField(default=0)
    brief = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.status})"

@register_snippet
class CampaignTask(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=255)
    is_done = models.BooleanField(default=False)
    due_date = models.CharField(max_length=100, blank=True, null=True) # e.g. "May 14"

    def __str__(self):
        return f"{self.campaign.name} - {self.title} ({'Done' if self.is_done else 'Pending'})"

@register_snippet
class CampaignMilestone(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="milestones")
    title = models.CharField(max_length=255)
    is_done = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.campaign.name} - {self.title} ({'Done' if self.is_done else 'Pending'})"

@register_snippet
class Deliverable(models.Model):
    STATUS_CHOICES = (
        ("Revision Requested", "Revision Requested"),
        ("Approved", "Approved"),
        ("Published", "Published"),
    )
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="deliverables")
    name = models.CharField(max_length=255) # e.g. "Reel #1"
    type = models.CharField(max_length=50) # e.g. "reel", "post"
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default="Revision Requested")
    deadline = models.CharField(max_length=100, blank=True, null=True) # e.g. "May 14"
    brief = models.TextField(blank=True, null=True)
    link = models.URLField(blank=True, default="")
    screenshot_name = models.CharField(max_length=255, blank=True, default="")

    def __str__(self):
        return f"{self.campaign.name} - {self.name} ({self.status})"

@register_snippet
class PaymentInstallment(models.Model):
    STATUS_CHOICES = (
        ("Released", "Released"),
        ("In Escrow", "In Escrow"),
        ("Funded", "Funded"),
    )
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="payments")
    milestone_name = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES)
    payment_date = models.CharField(max_length=100, blank=True, default="")

    def __str__(self):
        return f"{self.campaign.name} - {self.milestone_name} (${self.amount})"

@register_snippet
class WorkspaceFile(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="files")
    name = models.CharField(max_length=255)
    size = models.CharField(max_length=50) # e.g. "2.4 MB"
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.CharField(max_length=100) # e.g. "May 12, 2026"
    time = models.CharField(max_length=50) # e.g. "10:32 AM"

    def __str__(self):
        return f"{self.campaign.name} - {self.name} (Uploaded by {self.sender.username})"

@register_snippet
class WorkspaceMessage(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    file_attachment = models.CharField(max_length=255, blank=True, default="")
    time = models.CharField(max_length=50) # e.g. "10:24"

    def __str__(self):
        return f"{self.campaign.name} - Msg by {self.sender.username} ({self.time})"

@register_snippet
class AdminComplianceTicket(models.Model):
    CATEGORY_CHOICES = (
        ("Escrow Protection", "Escrow Protection"),
        ("Contract Scope Dispute", "Contract Scope Dispute"),
        ("Safety / Guidelines", "Safety / Guidelines"),
        ("Deliverable Audit", "Deliverable Audit"),
    )
    STATUS_CHOICES = (
        ("Pending Review", "Pending Review"),
        ("Resolved", "Resolved"),
        ("Approved", "Approved"),
    )
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="tickets")
    category = models.CharField(max_length=100, choices=CATEGORY_CHOICES)
    message = models.TextField()
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default="Pending Review")
    reply = models.TextField(blank=True, default="")
    date = models.CharField(max_length=100, blank=True, default="Just now")

    def __str__(self):
        return f"{self.campaign.name} - {self.category} ({self.status})"
