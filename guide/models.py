from django.db import models
from wagtail.snippets.models import register_snippet

@register_snippet
class Guide(models.Model):
    TARGET_CHOICES = (
        ("business", "Business"),
        ("creator", "Creator"),
        ("both", "Both"),
    )

    CATEGORY_CHOICES = (
        ("handbook", "Handbook"),
        ("protection", "Protection"),
        ("payment", "Payment Guide"),
        ("brand_request", "Brand Request Guide"),
        ("deliverable", "Deliverables"),
        ("general", "General Platform"),
    )

    guide_id = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        help_text="Unique guide identifier (automatically generated).",
    )
    title = models.CharField(max_length=255)
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        default="general",
        help_text="Category topic for this guide.",
    )
    content = models.TextField()
    document = models.FileField(
        upload_to="guide_documents/",
        blank=True,
        null=True,
        help_text="Upload an optional document, PDF, handbook, or attachment for this guide.",
    )
    target_audience = models.CharField(
        max_length=50,
        choices=TARGET_CHOICES,
        default="creator",
        help_text="Target audience who can access and view this guide (Business, Creator, or Both).",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Only active guides will be shown in platform dashboards.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Guide"
        verbose_name_plural = "Guides"

    def generate_next_id(self):
        import re
        max_num = 0
        queryset = Guide.objects.all()
        if self.id:
            queryset = queryset.exclude(id=self.id)
            
        for g in queryset:
            if g.guide_id:
                match = re.match(r"^GUID(\d+)", g.guide_id)
                if match:
                    num = int(match.group(1))
                    if num > max_num:
                        max_num = num
        next_num = max_num + 1
        
        suffix_map = {
            "business": "-BU",
            "creator": "-CR",
            "both": "-BO",
        }
        suffix = suffix_map.get(self.target_audience, "-CR")
        return f"GUID{next_num:03d}{suffix}"

    def save(self, *args, **kwargs):
        import re
        if not self.guide_id:
            self.guide_id = self.generate_next_id()
        else:
            match = re.match(r"^(GUID\d+)", self.guide_id)
            if match:
                base_part = match.group(1)
                suffix_map = {
                    "business": "-BU",
                    "creator": "-CR",
                    "both": "-BO",
                }
                suffix = suffix_map.get(self.target_audience, "-CR")
                self.guide_id = f"{base_part}{suffix}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.guide_id or 'TEMP'} - {self.title} ({self.get_category_display()})"
