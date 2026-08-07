from django.db import models
from django.contrib.auth.models import User
from django.utils.safestring import mark_safe
from wagtail.snippets.models import register_snippet

from modelcluster.models import ClusterableModel
from modelcluster.fields import ParentalKey
from wagtail.admin.panels import FieldPanel, InlinePanel
from wagtail.models import Orderable

@register_snippet
class Country(ClusterableModel):
    name = models.CharField(max_length=100, unique=True)
    currency = models.CharField(max_length=50, blank=True, null=True)
    country_code = models.CharField(max_length=10, blank=True, null=True)
    
    class Meta:
        verbose_name_plural = "Countries"

    panels = [
        FieldPanel("name"),
        FieldPanel("currency"),
        FieldPanel("country_code"),
        InlinePanel("mediums", label="Mediums", heading="Mediums"),
        InlinePanel("provinces", label="Provinces", heading="Provinces"),
        InlinePanel("districts", label="Districts", heading="Districts (Select Province)"),
    ]

    def __str__(self):
        return self.name

class Province(Orderable):
    country = ParentalKey(Country, on_delete=models.CASCADE, related_name="provinces")
    name = models.CharField(max_length=100)
    
    panels = [
        FieldPanel("name"),
    ]

    def __str__(self):
        return self.name

class Medium(Orderable):
    country = ParentalKey(Country, on_delete=models.CASCADE, related_name="mediums")
    name = models.CharField(max_length=100)

    panels = [
        FieldPanel("name"),
    ]

    def __str__(self):
        return self.name

class District(Orderable):
    country = ParentalKey(Country, on_delete=models.CASCADE, related_name="districts")
    province = models.ForeignKey("Province", on_delete=models.CASCADE, related_name="districts_list")
    name = models.CharField(max_length=100)
    
    panels = [
        FieldPanel("province"),
        FieldPanel("name"),
    ]

    def __str__(self):
        return self.name

class Niche(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True, verbose_name="Active", help_text="Checked = active/visible; Unchecked = inactive/hidden")

    panels = [
        FieldPanel("name"),
        FieldPanel("is_active"),
    ]

    class Meta:
        verbose_name = "Niche"
        verbose_name_plural = "Niches"
        ordering = ["name"]

    def __str__(self):
        return self.name

@register_snippet
class BusinessType(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

@register_snippet
class BusinessProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="business_profile")
    company_name = models.CharField(max_length=255, blank=True, null=True)
    business_type = models.CharField(max_length=255, blank=True, null=True)
    business_types = models.ManyToManyField(BusinessType, blank=True, related_name="businesses")
    mediums = models.ManyToManyField("Medium", blank=True, related_name="businesses")
    website = models.URLField(blank=True, null=True)
    country = models.ForeignKey("Country", on_delete=models.SET_NULL, null=True, blank=True, related_name="businesses")
    province = models.ForeignKey("Province", on_delete=models.SET_NULL, null=True, blank=True, related_name="businesses")
    district = models.ForeignKey("District", on_delete=models.SET_NULL, null=True, blank=True, related_name="businesses")
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
    otp_method = models.CharField(max_length=10, choices=[("email", "Email"), ("mobile", "Mobile")], default="email")
    otp_verified = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20,
        choices=[("pending", "Pending"), ("approved", "Approved"), ("restricted", "Restricted")],
        default="pending"
    )

    # Verification Fields
    verification_documents_submitted = models.BooleanField(default=False)
    business_reg_number = models.CharField(max_length=100, blank=True, null=True)
    business_document = models.FileField(upload_to="business_documents/", blank=True, null=True)

    # Featured (Top) business flag and timestamp
    is_featured = models.BooleanField(default=False, help_text="Mark as Featured / Top profile")
    featured_at = models.DateTimeField(null=True, blank=True)

    @property
    def role(self):
        return "business"

    def save(self, *args, **kwargs):
        from django.utils import timezone
        if self.is_featured and not self.featured_at:
            self.featured_at = timezone.now()
        elif not self.is_featured:
            self.featured_at = None
        super().save(*args, **kwargs)

    @property
    def currency_symbol(self):
        if self.country:
            if self.country.currency:
                from campegin.models import extract_currency_symbol
                sym = extract_currency_symbol(self.country.currency)
                if sym:
                    return sym
            from campegin.models import COUNTRY_CURRENCY_SYMBOL_MAP
            if self.country.name and self.country.name in COUNTRY_CURRENCY_SYMBOL_MAP:
                return COUNTRY_CURRENCY_SYMBOL_MAP[self.country.name]
        return "$"

    def __str__(self):
        return f"{self.company_name or self.user.username} (Business)"

@register_snippet
class CreatorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="creator_profile")
    phone = models.CharField(max_length=30, blank=True, null=True)
    location = models.CharField(max_length=100, blank=True, null=True)
    country = models.ForeignKey("Country", on_delete=models.SET_NULL, null=True, blank=True, related_name="creators")
    bio = models.TextField(blank=True, null=True)
    province = models.ForeignKey(Province, on_delete=models.SET_NULL, null=True, blank=True, related_name="creators")
    district = models.ForeignKey("District", on_delete=models.SET_NULL, null=True, blank=True, related_name="creators")
    avatar_url = models.CharField(max_length=255, blank=True, null=True)
    niches = models.ManyToManyField(Niche, blank=True, related_name="creators")
    mediums = models.ManyToManyField(Medium, blank=True, related_name="creators")
    wallet_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    next_payout_date = models.CharField(max_length=100, blank=True, null=True)

    # OTP storage
    otp_code = models.CharField(max_length=6, blank=True, null=True)
    otp_method = models.CharField(max_length=10, choices=[("email", "Email"), ("mobile", "Mobile")], default="email")
    otp_verified = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20,
        choices=[("pending", "Pending"), ("approved", "Approved"), ("restricted", "Restricted")],
        default="pending"
    )

    # Verification Fields
    verification_documents_submitted = models.BooleanField(default=False)
    document_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        choices=[("nic", "NIC"), ("passport", "Passport"), ("driving_license", "Driving License")]
    )
    document_front = models.FileField(upload_to="creator_documents/", blank=True, null=True)
    document_back = models.FileField(upload_to="creator_documents/", blank=True, null=True)
    other_details = models.TextField(blank=True, null=True)

    # Featured (Top) creator flag and timestamp
    is_featured = models.BooleanField(default=False, help_text="Mark as Featured / Top profile")
    featured_at = models.DateTimeField(null=True, blank=True)

    saved_brands = models.ManyToManyField('BusinessProfile', blank=True, related_name="saved_by_creators")

    @property
    def average_rating(self):
        from CreatorRating.models import CreatorRating
        from django.db.models import Avg
        if not self.user:
            return 0.0
        avg = CreatorRating.objects.filter(creator=self.user).aggregate(Avg('rating'))['rating__avg']
        return round(float(avg), 1) if avg is not None else 0.0

    @property
    def total_ratings_count(self):
        from CreatorRating.models import CreatorRating
        if not self.user:
            return 0
        return CreatorRating.objects.filter(creator=self.user).count()

    @property
    def role(self):
        return "creator"

    @property
    def currency_symbol(self):
        if self.country:
            if self.country.currency:
                from campegin.models import extract_currency_symbol
                sym = extract_currency_symbol(self.country.currency)
                if sym:
                    return sym
            from campegin.models import COUNTRY_CURRENCY_SYMBOL_MAP
            if self.country.name and self.country.name in COUNTRY_CURRENCY_SYMBOL_MAP:
                return COUNTRY_CURRENCY_SYMBOL_MAP[self.country.name]
        return "$"

    def save(self, *args, **kwargs):
        from django.utils import timezone
        if self.is_featured and not self.featured_at:
            self.featured_at = timezone.now()
        elif not self.is_featured:
            self.featured_at = None
        super().save(*args, **kwargs)

    def get_formatted_wallet(self):
        return f"{self.currency_symbol}{self.wallet_balance:,.2f}"
    get_formatted_wallet.short_description = "Wallet Balance"

    def get_status_badge(self):
        from django.utils.html import format_html
        colors = {
            "approved": ("#dcfce7", "#166534", "Approved"),
            "pending": ("#fef9c3", "#854d0e", "Pending"),
            "restricted": ("#ffe4e6", "#991b1b", "Restricted"),
        }
        bg, fg, label = colors.get(self.status, ("#f8fafc", "#475569", str(self.status).title()))
        return format_html(
            '<span style="background-color: {}; color: {}; font-weight: 600; font-size: 11px; padding: 3px 10px; border-radius: 4px; display: inline-block;">{}</span>',
            bg, fg, label
        )
    get_status_badge.short_description = "Status"

    def get_rating_display(self):
        from django.utils.html import format_html
        avg = self.average_rating
        if avg > 0:
            return format_html('<span style="color: #f59e0b; font-weight: 700;">★ {}</span>', avg)
        return "-"
    get_rating_display.short_description = "Rating"

    def __str__(self):
        return f"{self.user.username} (Creator)"


@register_snippet
class CreatorRate(models.Model):
    creator = models.ForeignKey(CreatorProfile, on_delete=models.CASCADE, related_name="rates")
    content_type = models.CharField(max_length=255)
    platforms = models.CharField(max_length=255, help_text="Comma-separated or JSON list of platforms, e.g. 'Instagram,TikTok'")
    price = models.DecimalField(max_digits=12, decimal_places=2)
    min_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, default=0)
    max_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, default=0)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.creator.user.username} - {self.content_type} (${self.price})"

@register_snippet
class CreatorSocialAccount(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="social_accounts")
    platform = models.CharField(max_length=100)
    username = models.CharField(max_length=100, blank=True, default="")
    followers_count = models.CharField(max_length=50, blank=True, default="") # e.g. "1.2M", "320K", "50,000"
    proof_link = models.CharField(max_length=255, blank=True, default="")
    engagement_rate = models.DecimalField(max_digits=5, decimal_places=2, default=5.00) # e.g. 8.20
    is_connected = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False, help_text="Verified by Super Admin")

    def __str__(self):
        status_str = "Verified" if self.is_verified else ("In Verify" if self.is_connected else "Disconnected")
        return f"{self.user.username} - {self.platform} ({status_str})"

    def get_proof_link_display(self):
        url = (self.proof_link or "").strip()
        if not url:
            return "-"
        full_url = url if url.startswith("http://") or url.startswith("https://") else f"https://{url}"
        return mark_safe(f'<a href="{full_url}" target="_blank" rel="noopener noreferrer" style="color: #2F54EB; font-weight: bold; text-decoration: underline; white-space: nowrap;">🔗 Open Link ↗</a>')
    get_proof_link_display.short_description = "Proof Link"

User.profile = property(lambda self: getattr(self, "business_profile", None) or getattr(self, "creator_profile", None))

