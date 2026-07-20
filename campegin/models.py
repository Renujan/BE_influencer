from django.db import models
from django.contrib.auth.models import User
from wagtail.snippets.models import register_snippet
from wagtail.admin.panels import FieldPanel

class Campaign(models.Model):
    STATUS_CHOICES = (
        ("Pending", "Pending"),
        ("Live", "Live"),
        ("Completed", "Completed"),
        ("Rejected", "Rejected"),
        ("Countered", "Countered"),
        ("Under_Review", "Under Review"),
    )
    name = models.CharField(max_length=255)
    brand = models.ForeignKey(User, on_delete=models.CASCADE, related_name="brand_campaigns")
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name="creator_campaigns", null=True, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="Under_Review")
    budget = models.DecimalField(max_digits=12, decimal_places=2)
    start_date = models.CharField(max_length=100, blank=True, null=True) # e.g. "May 12"
    progress = models.IntegerField(default=0)
    brief = models.TextField(blank=True, null=True)
    category = models.CharField(max_length=100, blank=True, null=True)
    delivery_language = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=255, blank=True, null=True)
    province = models.CharField(max_length=255, blank=True, null=True)
    district = models.CharField(max_length=255, blank=True, null=True)
    medium = models.CharField(max_length=255, blank=True, null=True)
    voice_brief = models.FileField(upload_to="brief_media/", blank=True, null=True)
    screenshare_brief = models.FileField(upload_to="brief_media/", blank=True, null=True)
    video_brief = models.FileField(upload_to="brief_media/", blank=True, null=True)
    admin_review = models.TextField(blank=True, null=True, help_text="Provide review/rejection comments to the business if rejected.")
    counter_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    counter_note = models.TextField(blank=True, null=True)

    panels = [
        FieldPanel('name'),
        FieldPanel('brand'),
        FieldPanel('creator'),
        FieldPanel('status'),
        FieldPanel('budget'),
        FieldPanel('start_date'),
        FieldPanel('progress'),
        FieldPanel('brief'),
        FieldPanel('category'),
        FieldPanel('delivery_language'),
        FieldPanel('country'),
        FieldPanel('province'),
        FieldPanel('district'),
        FieldPanel('medium'),
        FieldPanel('voice_brief'),
        FieldPanel('screenshare_brief'),
        FieldPanel('video_brief'),
        FieldPanel('admin_review'),
    ]

    def __str__(self):
        return f"{self.name} ({self.status})"

    def get_business_name(self):
        return self.brand.username if self.brand else "-"
    get_business_name.short_description = "Business Name"

    def get_creator_name(self):
        return self.creator.username if self.creator else "-"
    get_creator_name.short_description = "Creator Name"

    def get_last_chat_time(self):
        last_msg = self.messages.all().order_by("-id").first()
        if last_msg:
            return last_msg.time
        return "-"
    get_last_chat_time.short_description = "Last Chat Date & Time"

    def get_view_chat_btn(self):
        from django.urls import reverse
        from django.utils.html import format_html
        url = reverse("chat_monitor_view_chat", args=[self.id])
        return format_html('<a class="button button-small button-secondary" href="{}">View Chat</a>', url)
    get_view_chat_btn.short_description = "View Chat"

    def get_review_btn(self):
        from django.urls import reverse
        from django.utils.html import format_html
        url = reverse("chat_monitor_review", args=[self.id])
        return format_html('<a class="button button-small button-secondary" href="{}">Review</a>', url)
    get_review_btn.short_description = "Review"



@register_snippet
class CampaignTask(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=255)
    is_done = models.BooleanField(default=False)
    due_date = models.CharField(max_length=100, blank=True, null=True) # e.g. "May 14"

    def __str__(self):
        return f"{self.campaign.name} - {self.title} ({'Done' if self.is_done else 'Pending'})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Calculate progress
        total_tasks = self.campaign.tasks.count()
        if total_tasks > 0:
            completed_tasks = self.campaign.tasks.filter(is_done=True).count()
            progress_percentage = int((completed_tasks / total_tasks) * 100)
            self.campaign.progress = progress_percentage
            self.campaign.save(update_fields=['progress'])

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
        ("Pending Review", "Pending Review"),
        ("Approved", "Approved"),
        ("Published", "Published"),
    )
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="deliverables")
    name = models.CharField(max_length=255) # e.g. "Reel #1"
    type = models.CharField(max_length=50) # e.g. "reel", "post"
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default="Revision Requested")
    deadline = models.CharField(max_length=100, blank=True, null=True) # e.g. "May 14"
    brief = models.TextField(blank=True, null=True)
    views = models.CharField(max_length=100, blank=True, null=True)
    reach = models.CharField(max_length=100, blank=True, null=True)
    er = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    assetDriveLink = models.URLField(blank=True, default="")
    assetFileName = models.FileField(upload_to="deliverables/", blank=True, null=True)
    link = models.URLField(blank=True, default="")
    screenshot_name = models.FileField(upload_to="deliverables/", blank=True, null=True)

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
    MESSAGE_TYPE_CHOICES = (
        ('main', 'Main Chat'),
        ('admin_note', 'Admin Private Note'),
        ('admin_business', 'Admin-Business Chat'),
        ('admin_creator', 'Admin-Creator Chat'),
    )
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPE_CHOICES, default='main')
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

class CampaignCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)

    panels = [
        FieldPanel("name"),
    ]

    class Meta:
        verbose_name = "Campaign Category"
        verbose_name_plural = "Campaign Categories"

    def __str__(self):
        return self.name

class CampaignLanguage(models.Model):
    name = models.CharField(max_length=100, unique=True)

    panels = [
        FieldPanel("name"),
    ]

    class Meta:
        verbose_name = "Campaign Language"
        verbose_name_plural = "Campaign Languages"

    def __str__(self):
        return self.name

class CampaignDeliverable(models.Model):
    name = models.CharField(max_length=255, unique=True)

    panels = [
        FieldPanel("name"),
    ]

    class Meta:
        verbose_name = "Campaign Deliverable"
        verbose_name_plural = "Campaign Deliverables"

    def __str__(self):
        return self.name

class CampaignPlatform(models.Model):
    platform_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    color = models.CharField(max_length=50, blank=True, null=True)
    logo = models.CharField(max_length=50, blank=True, null=True)

    panels = [
        FieldPanel("platform_id"),
        FieldPanel("name"),
        FieldPanel("color"),
        FieldPanel("logo"),
    ]

    class Meta:
        verbose_name = "Campaign Platform"
        verbose_name_plural = "Campaign Platforms"

    def __str__(self):
        return self.name

class Pitch(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("declined", "Declined"),
        ("counter_offer", "Counter Offer"),
    )
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_pitches")
    brand = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_pitches")
    campaign_name = models.CharField(max_length=255)
    budget = models.DecimalField(max_digits=12, decimal_places=2)
    sent_date = models.CharField(max_length=100)
    tags = models.JSONField(default=list, blank=True, null=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="pending")
    description = models.TextField(blank=True, null=True)
    deliverables = models.JSONField(default=list, blank=True, null=True)
    counter_offer = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"{self.campaign_name} - {self.status}"
