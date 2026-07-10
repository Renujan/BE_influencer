from django.db import models
from django.contrib.auth.models import User
from wagtail.snippets.models import register_snippet

@register_snippet
class Country(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

@register_snippet
class Niche(models.Model):
    name = models.CharField(max_length=100, unique=True)

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
    website = models.URLField(blank=True, null=True)
    country = models.ForeignKey("Country", on_delete=models.SET_NULL, null=True, blank=True, related_name="businesses")
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

    def __str__(self):
        return f"{self.company_name or self.user.username} (Business)"

@register_snippet
class CreatorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="creator_profile")
    phone = models.CharField(max_length=30, blank=True, null=True)
    location = models.CharField(max_length=100, blank=True, null=True)
    country = models.ForeignKey("Country", on_delete=models.SET_NULL, null=True, blank=True, related_name="creators")
    bio = models.TextField(blank=True, null=True)
    avatar_url = models.CharField(max_length=255, blank=True, null=True)
    niches = models.ManyToManyField(Niche, blank=True, related_name="creators")
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

    @property
    def role(self):
        return "creator"

    def save(self, *args, **kwargs):
        from django.utils import timezone
        if self.is_featured and not self.featured_at:
            self.featured_at = timezone.now()
        elif not self.is_featured:
            self.featured_at = None
        super().save(*args, **kwargs)

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

User.profile = property(lambda self: getattr(self, "business_profile", None) or getattr(self, "creator_profile", None))

