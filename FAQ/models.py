from django.db import models
from wagtail.snippets.models import register_snippet

@register_snippet
class FAQ(models.Model):
    TARGET_CHOICES = (
        ("business", "Business"),
        ("creator", "Creator"),
        ("both", "Both"),
    )

    faq_id = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        help_text="Unique FAQ identifier (automatically generated).",
    )
    question = models.CharField(max_length=255)
    answer = models.TextField()
    target_audience = models.CharField(
        max_length=20,
        choices=TARGET_CHOICES,
        default="both",
        help_text="Determine whether this FAQ shows for businesses, creators, or both.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Only active FAQs will be shown in the dashboards.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"

    def generate_next_id(self):
        import re
        max_num = 0
        queryset = FAQ.objects.all()
        if self.id:
            queryset = queryset.exclude(id=self.id)
            
        for f in queryset:
            if f.faq_id:
                match = re.match(r"^FAQ(\d+)", f.faq_id)
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
        return f"FAQ{next_num:03d}{suffix}"

    def save(self, *args, **kwargs):
        import re
        if not self.faq_id:
            self.faq_id = self.generate_next_id()
        else:
            # If target_audience changed, update the suffix
            match = re.match(r"^(FAQ\d+)", self.faq_id)
            if match:
                base_part = match.group(1)
                suffix_map = {
                    "business": "-BU",
                    "creator": "-CR",
                    "both": "-BO"
                }
                suffix = suffix_map.get(self.target_audience, "-BO")
                self.faq_id = f"{base_part}{suffix}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.faq_id or 'TEMP'} - {self.question} ({self.get_target_audience_display()})"
