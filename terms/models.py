from django.db import models
from wagtail.snippets.models import register_snippet

@register_snippet
class TermsAndCondition(models.Model):
    TARGET_CHOICES = (
        ("business", "Business"),
        ("creator", "Creator"),
        ("both", "Both"),
    )

    terms_id = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        help_text="Unique terms identifier (automatically generated).",
    )
    title = models.CharField(max_length=255)
    content = models.TextField()
    target_audience = models.CharField(
        max_length=20,
        choices=TARGET_CHOICES,
        default="both",
        help_text="Determine whether these terms show for businesses, creators, or both.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Only active terms will be shown in the dashboards.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Terms and Condition"
        verbose_name_plural = "Terms and Conditions"

    def generate_next_id(self):
        import re
        max_num = 0
        # Exclude current model if it exists
        queryset = TermsAndCondition.objects.all()
        if self.id:
            queryset = queryset.exclude(id=self.id)
            
        for t in queryset:
            if t.terms_id:
                match = re.match(r"^TERM(\d+)", t.terms_id)
                if match:
                    num = int(match.group(1))
                    if num > max_num:
                        max_num = num
        next_num = max_num + 1
        
        suffix_map = {
            "business": "-BU",
            "creator": "-CR",
            "both": "-BO"
        }
        suffix = suffix_map.get(self.target_audience, "-BO")
        return f"TERM{next_num:03d}{suffix}"

    def save(self, *args, **kwargs):
        import re
        if not self.terms_id:
            self.terms_id = self.generate_next_id()
        else:
            # If target_audience changed, update the suffix
            match = re.match(r"^(TERM\d+)", self.terms_id)
            if match:
                base_part = match.group(1)
                suffix_map = {
                    "business": "-BU",
                    "creator": "-CR",
                    "both": "-BO"
                }
                suffix = suffix_map.get(self.target_audience, "-BO")
                self.terms_id = f"{base_part}{suffix}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.terms_id or 'TEMP'} - {self.title} ({self.get_target_audience_display()})"

