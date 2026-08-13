from django.db import models
from django.contrib.auth.models import User
from django import forms
from wagtail.snippets.models import register_snippet
from wagtail.admin.panels import FieldPanel
from wagtail.admin.forms import WagtailAdminModelForm
import re

COUNTRY_CURRENCY_SYMBOL_MAP = {
    "United States": "$",
    "United Kingdom": "£",
    "Canada": "$",
    "Australia": "A$",
    "India": "₹",
    "Sri Lanka": "Rs",
    "Germany": "€",
    "France": "€",
    "Italy": "€",
    "Spain": "€",
    "Japan": "¥",
    "China": "¥",
    "South Korea": "₩",
    "Brazil": "R$",
    "Mexico": "$",
    "South Africa": "R",
    "Nigeria": "₦",
    "New Zealand": "$",
    "Singapore": "S$",
    "United Arab Emirates": "د.إ",
    "Saudi Arabia": "﷼",
    "Netherlands": "€",
    "Sweden": "kr",
    "Switzerland": "Fr"
}

def extract_currency_symbol(currency_str):
    if not currency_str:
        return None
    currency_str = str(currency_str).strip()
    match = re.search(r'\(([^)]+)\)', currency_str)
    if match:
        return match.group(1).strip()
    return currency_str

class CampaignCategoryForm(WagtailAdminModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import CampaignPlatform
        platform_choices = [(p.name, p.name) for p in CampaignPlatform.objects.all()]
        self.fields["platform"].widget = forms.Select(
            choices=[("", "Select Platform")] + platform_choices,
            attrs={"class": "w-full"}
        )

class CampaignDeliverableForm(WagtailAdminModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import CampaignPlatform
        platform_choices = [(p.name, p.name) for p in CampaignPlatform.objects.all()]
        if not platform_choices:
            platform_choices = [
                ("Facebook", "Facebook"),
                ("Instagram", "Instagram"),
                ("TikTok", "TikTok"),
                ("YouTube", "YouTube"),
                ("LinkedIn", "LinkedIn"),
                ("X", "X"),
            ]
        self.fields["platform"].widget = forms.Select(
            choices=[("", "Select Platform")] + platform_choices,
            attrs={"class": "w-full"}
        )

class CampaignNiche(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True, verbose_name="Active", help_text="Checked = active/visible while creating campaign; Unchecked = inactive/hidden")

    panels = [
        FieldPanel("name"),
        FieldPanel("is_active"),
    ]

    class Meta:
        verbose_name = "Campaign Niche"
        verbose_name_plural = "Campaign Niches"
        ordering = ["name"]

    def __str__(self):
        return self.name

class Campaign(models.Model):
    STATUS_CHOICES = (
        ("Pending", "Pending"),
        ("Live", "Live"),
        ("Completed", "Completed"),
        ("Rejected", "Rejected"),
        ("Countered_Pending", "Creator Counter Pending Approval"),
        ("Countered", "Countered"),
        ("Business_Counter_Pending", "Business Counter Pending Approval"),
        ("Business_Countered", "Business Countered"),
        ("Under_Review", "Under Review"),
    )
    name = models.CharField(max_length=255)
    brand = models.ForeignKey(User, on_delete=models.CASCADE, related_name="brand_campaigns")
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name="creator_campaigns", null=True, blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default="Under_Review")
    budget = models.DecimalField(max_digits=12, decimal_places=2)
    min_budget = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    max_budget = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    per_creator_budget = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    min_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    max_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    rate_card_id = models.CharField(max_length=100, blank=True, null=True)
    start_date = models.CharField(max_length=100, blank=True, null=True) # e.g. "May 12"
    end_date = models.CharField(max_length=100, blank=True, null=True)
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
    counter_round = models.IntegerField(default=0)
    counter_history = models.JSONField(default=list, blank=True, null=True)
    decline_reason = models.TextField(blank=True, null=True)
    created_via = models.CharField(max_length=50, default="direct_request", choices=(("direct_request", "Direct Request"), ("request", "Request"), ("pitch", "Creator Pitch")))
    created_time = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    panels = [
        FieldPanel('name'),
        FieldPanel('brand'),
        FieldPanel('creator'),
        FieldPanel('status'),
        FieldPanel('budget'),
        FieldPanel('min_budget'),
        FieldPanel('max_budget'),
        FieldPanel('per_creator_budget'),
        FieldPanel('min_price'),
        FieldPanel('max_price'),
        FieldPanel('rate_card_id'),
        FieldPanel('start_date'),
        FieldPanel('end_date'),
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
        FieldPanel('counter_round'),
        FieldPanel('decline_reason'),
        FieldPanel('created_via'),
        FieldPanel('created_time'),
    ]

    def calculate_flow_progress(self):
        """
        Calculate progress percentage according to the campaign flow progress:
        - Rejected: 0%
        - Under_Review: 20%
        - Pending (Admin Approved, Creator Review): 40%
        - Countered / Countered_Pending / Business_Counter_Pending / Business_Countered (Negotiation): 55%
        - Live / Active: 70% base (+ up to 25% for completed deliverables/tasks, max 95%)
        - Completed: 100%
        """
        status = (self.status or "").strip()
        if status == "Rejected":
            return 0
        elif status == "Under_Review":
            return 20
        elif status == "Pending":
            return 40
        elif status in ["Countered", "Countered_Pending", "Business_Counter_Pending", "Business_Countered"]:
            return 55
        elif status in ["Live", "live", "Active", "active", "In_Progress", "in_progress"]:
            if self.pk:
                try:
                    total_dels = self.deliverables.count()
                    if total_dels > 0:
                        approved_dels = self.deliverables.filter(status__in=["Approved", "Published"]).count()
                        deliverable_bonus = int((approved_dels / total_dels) * 25)
                        return min(95, 70 + deliverable_bonus)
                except Exception:
                    pass

                try:
                    total_tasks = self.tasks.count()
                    if total_tasks > 0:
                        done_tasks = self.tasks.filter(is_done=True).count()
                        task_bonus = int((done_tasks / total_tasks) * 25)
                        return min(95, 70 + task_bonus)
                except Exception:
                    pass

            return 70
        elif status in ["Completed", "completed"]:
            return 100

        return self.progress or 0

    def save(self, *args, **kwargs):
        self.progress = self.calculate_flow_progress()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.status})"

    def get_campaign_name(self):
        return self.name or "-"
    get_campaign_name.short_description = "Campaign Name"

    def get_business_name(self):
        return self.brand.username if self.brand else "-"
    get_business_name.short_description = "Business Name"

    def get_creator_name(self):
        return self.creator.username if self.creator else "-"
    get_creator_name.short_description = "Creator Name"

    @property
    def creator_name(self):
        return self.creator.username if self.creator else (self.influencer or "")

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

    @property
    def currency_symbol(self):
        if self.country:
            c_str = str(self.country).strip()
            if c_str in COUNTRY_CURRENCY_SYMBOL_MAP:
                return COUNTRY_CURRENCY_SYMBOL_MAP[c_str]
            try:
                from user.models import Country
                c = Country.objects.filter(name__iexact=c_str).first()
                if c and c.currency:
                    sym = extract_currency_symbol(c.currency)
                    if sym:
                        return sym
            except Exception:
                pass

        if self.creator:
            try:
                if hasattr(self.creator, 'creator_profile') and self.creator.creator_profile and self.creator.creator_profile.country:
                    c = self.creator.creator_profile.country
                    if c and c.currency:
                        sym = extract_currency_symbol(c.currency)
                        if sym:
                            return sym
                    if c and c.name and c.name in COUNTRY_CURRENCY_SYMBOL_MAP:
                        return COUNTRY_CURRENCY_SYMBOL_MAP[c.name]
            except Exception:
                pass

        if self.brand:
            try:
                if hasattr(self.brand, 'business_profile') and self.brand.business_profile and self.brand.business_profile.country:
                    c = self.brand.business_profile.country
                    if c and c.currency:
                        sym = extract_currency_symbol(c.currency)
                        if sym:
                            return sym
                    if c and c.name and c.name in COUNTRY_CURRENCY_SYMBOL_MAP:
                        return COUNTRY_CURRENCY_SYMBOL_MAP[c.name]
            except Exception:
                pass

        return "$"




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
    revision_notes = models.TextField(blank=True, default="")
    revision_reference_link = models.URLField(max_length=500, blank=True, default="")
    revision_reference_file = models.FileField(upload_to="deliverables/revisions/", blank=True, null=True)

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
    is_pinned = models.BooleanField(default=False)
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
    sender = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    sender_role = models.CharField(max_length=50, blank=True, default="")
    target_audience = models.CharField(max_length=50, blank=True, default="both")
    category = models.CharField(max_length=100, choices=CATEGORY_CHOICES)
    message = models.TextField()
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default="Pending Review")
    reply = models.TextField(blank=True, default="")
    date = models.CharField(max_length=100, blank=True, default="Just now")

    def __str__(self):
        return f"{self.campaign.name} - {self.category} ({self.status})"

class CampaignCategory(models.Model):
    name = models.CharField(max_length=255, blank=True, default="")
    platform = models.CharField(max_length=100, blank=True, default="")
    type = models.CharField(max_length=100, blank=True, default="")
    duration = models.CharField(max_length=100, blank=True, default="")
    min_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, null=True, blank=True)
    max_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, null=True, blank=True)

    base_form_class = CampaignCategoryForm

    panels = [
        FieldPanel("platform"),
        FieldPanel("type"),
        FieldPanel("duration"),
        FieldPanel("name"),
        FieldPanel("min_price"),
        FieldPanel("max_price"),
    ]

    class Meta:
        verbose_name = "Campaign Category"
        verbose_name_plural = "Campaign Categories"

    def __str__(self):
        return self.name or f"{self.platform} - {self.type} ({self.duration})"

    def save(self, *args, **kwargs):
        parts = [p for p in [self.platform, self.type] if p]
        base = " - ".join(parts) if parts else (self.name or "")
        if self.duration:
            self.name = f"{base} ({self.duration})" if base else self.duration
        elif base:
            self.name = base
        super().save(*args, **kwargs)

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
    name = models.CharField(max_length=255)
    platform = models.CharField(max_length=100, blank=True, null=True, default="")

    base_form_class = CampaignDeliverableForm

    panels = [
        FieldPanel("platform"),
        FieldPanel("name"),
    ]

    class Meta:
        verbose_name = "Campaign Deliverable"
        verbose_name_plural = "Campaign Deliverables"

    def __str__(self):
        if self.platform:
            return f"{self.platform} - {self.name}"
        return self.name

from wagtail.admin.panels import FieldPanel
from wagtail.admin.forms import WagtailAdminModelForm
from django.forms.widgets import ClearableFileInput
from django.utils.html import mark_safe

class CustomPlatformLogoInput(ClearableFileInput):
    def render(self, name, value, attrs=None, renderer=None):
        output = super().render(name, value, attrs=attrs, renderer=renderer)
        if value:
            url = ""
            try:
                if hasattr(value, "url") and value.url:
                    url = value.url
                elif isinstance(value, str) and value.strip():
                    url = value if (value.startswith("/") or value.startswith("http")) else f"/media/{value}"
            except Exception:
                if hasattr(value, "name") and value.name:
                    url = f"/media/{value.name}"

            if url:
                preview = f'''
                <div style="margin-top: 12px; padding: 12px; background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; display: inline-flex; align-items: center; gap: 14px;">
                    <span style="font-size: 12px; font-weight: 600; color: #475569;">Saved Logo Preview:</span>
                    <img src="{url}" style="height: 48px; width: 48px; object-fit: contain; border-radius: 6px; border: 1px solid #cbd5e1; background: #ffffff; padding: 4px;" alt="Logo Preview" />
                    <a href="{url}" target="_blank" style="font-size: 12px; font-weight: 600; color: #2563eb; text-decoration: underline;">Open Image</a>
                </div>
                '''
                return mark_safe(output + preview)
        return output

class CampaignPlatformForm(WagtailAdminModelForm):
    class Meta:
        widgets = {
            "logo": CustomPlatformLogoInput(),
        }

class CampaignPlatform(models.Model):
    platform_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    color = models.CharField(max_length=50, blank=True, null=True)
    logo = models.ImageField(upload_to="platform_logos/", blank=True, null=True)

    base_form_class = CampaignPlatformForm

    def logo_preview(self):
        if self.logo:
            try:
                url = ""
                if hasattr(self.logo, "url") and self.logo.url:
                    url = self.logo.url
                elif isinstance(self.logo, str) and self.logo.strip():
                    val = self.logo.strip()
                    if val.startswith("/") or val.startswith("http") or val.endswith((".png", ".jpg", ".jpeg", ".svg", ".webp")):
                        url = val if (val.startswith("/") or val.startswith("http")) else f"/media/{val}"
                    else:
                        return mark_safe(f'<span style="font-size: 18px; line-height: 1; padding: 4px 8px; background: #f1f5f9; border-radius: 6px;">{val}</span>')
                elif hasattr(self.logo, "name") and self.logo.name:
                    url = f"/media/{self.logo.name}"
                
                if url:
                    return mark_safe(f'<img src="{url}" style="height: 36px; width: 36px; object-fit: contain; border-radius: 6px; border: 1px solid #cbd5e1; background: #ffffff; padding: 2px;" />')
            except Exception:
                pass
        return "-"
    logo_preview.short_description = "Logo Preview"

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
        ("pending_admin", "Pending Admin Approval"),
        ("pending", "Pending Business Review"),
        ("accepted_by_business", "Accepted by Business – Awaiting Admin Conversion"),
        ("accepted", "Accepted – Converted to Campaign"),
        ("biz_counter_pending", "Business Counter – Pending Admin"),
        ("biz_countered", "Business Counter – Approved"),
        ("pitch_counter_pending", "Creator Counter – Pending Admin"),
        ("pitch_countered", "Creator Counter – Approved"),
        ("declined", "Declined"),
    )
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_pitches")
    brand = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_pitches")
    campaign_name = models.CharField(max_length=255)
    budget = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sent_date = models.CharField(max_length=100)
    tags = models.JSONField(default=list, blank=True, null=True)
    status = models.CharField(max_length=35, choices=STATUS_CHOICES, default="pending_admin")
    description = models.TextField(blank=True, null=True)
    deliverables = models.JSONField(default=list, blank=True, null=True)
    counter_offer = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    counter_note = models.TextField(null=True, blank=True)
    counter_count = models.IntegerField(default=0)
    counter_history = models.JSONField(default=list, blank=True, null=True)
    attachment = models.FileField(upload_to="pitch_attachments/", null=True, blank=True)
    decline_reason = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.campaign_name} - {self.status}"

    @property
    def currency_symbol(self):
        if self.creator:
            try:
                if hasattr(self.creator, 'creator_profile') and self.creator.creator_profile and self.creator.creator_profile.country:
                    c = self.creator.creator_profile.country
                    if c and c.currency:
                        sym = extract_currency_symbol(c.currency)
                        if sym:
                            return sym
                    if c and c.name and c.name in COUNTRY_CURRENCY_SYMBOL_MAP:
                        return COUNTRY_CURRENCY_SYMBOL_MAP[c.name]
            except Exception:
                pass

        if self.brand:
            try:
                if hasattr(self.brand, 'business_profile') and self.brand.business_profile and self.brand.business_profile.country:
                    c = self.brand.business_profile.country
                    if c and c.currency:
                        sym = extract_currency_symbol(c.currency)
                        if sym:
                            return sym
                    if c and c.name and c.name in COUNTRY_CURRENCY_SYMBOL_MAP:
                        return COUNTRY_CURRENCY_SYMBOL_MAP[c.name]
            except Exception:
                pass

        return "$"

