from django.db import models
from wagtail.snippets.models import register_snippet

@register_snippet
class PrivacyPolicy(models.Model):
    TARGET_CHOICES = (
        ("public", "Public (Landing Page)"),
        ("creator", "Creator"),
        ("business", "Business"),
        ("both", "Both"),
    )

    policy_id = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        help_text="Unique privacy policy identifier (automatically generated).",
    )
    title = models.CharField(max_length=255)
    content = models.TextField()
    target_audience = models.CharField(
        max_length=50,
        choices=TARGET_CHOICES,
        default="public",
        help_text="Determine whether this privacy policy shows for public, creator, business, or both.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Only active privacy policies will be shown in the dashboards and public site.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Privacy Policy"
        verbose_name_plural = "Privacy Policies"

    def generate_next_id(self):
        import re
        max_num = 0
        queryset = PrivacyPolicy.objects.all()
        if self.id:
            queryset = queryset.exclude(id=self.id)
            
        for p in queryset:
            if p.policy_id:
                match = re.match(r"^PRIV(\d+)", p.policy_id)
                if match:
                    num = int(match.group(1))
                    if num > max_num:
                        max_num = num
        next_num = max_num + 1
        
        suffix_map = {
            "public": "-PU",
            "creator": "-CR",
            "business": "-BU",
            "both": "-BO",
        }
        suffix = suffix_map.get(self.target_audience, "-PU")
        return f"PRIV{next_num:03d}{suffix}"

    def save(self, *args, **kwargs):
        import re
        if not self.policy_id:
            self.policy_id = self.generate_next_id()
        else:
            match = re.match(r"^(PRIV\d+)", self.policy_id)
            if match:
                base_part = match.group(1)
                suffix_map = {
                    "public": "-PU",
                    "creator": "-CR",
                    "business": "-BU",
                    "both": "-BO",
                }
                suffix = suffix_map.get(self.target_audience, "-PU")
                self.policy_id = f"{base_part}{suffix}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.policy_id or 'TEMP'} - {self.title} ({self.get_target_audience_display()})"
